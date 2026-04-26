from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Query
import json
from indexer.indexer import Indexer
from parsers.pdf_parser import PDFParser    
from prompts.indexer_prompt import INDEXER_PROMPT
from retrievers.retriever import Retriever
from storage.storage import Storage
import uuid
import os
from llms.openai_llm import OpenAILLM
from llms.gemini_llm import GeminiLLM
from llms.claude_llm import ClaudeLLM
from llms.ollama_llm import OllamaLLM
from chat.chat import Chat
from wiki.wiki_builder import WikiBuilder
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

app = FastAPI(
    title="Vectorless RAG API",
    description=""",
    This API allows you to perform Retrieval-Augmented Generation without using vector databases.

    You can:
    - **Upload documents** for indexing.
    - **Check the status** of an indexing job.
    - **Query your documents** using natural language.
    """,
    version="1.0.0",
)

JOBS_FILE = "jobs.json"

def _load_jobs():
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE) as f:
            return json.load(f)
    return {}

def _save_jobs(jobs):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f)

def get_llm():
    provider = os.getenv("LLM_PROVIDER", "openai")
    if provider == "openai":
        return OpenAILLM(api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "gemini":
        return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"), model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    elif provider == "claude":
        return ClaudeLLM(api_key=os.getenv("CLAUDE_API_KEY"))
    elif provider == "ollama":
        return OllamaLLM(model=os.getenv("OLLAMA_MODEL", "llama3"))
    else:        
        raise ValueError(f"Unsupported LLM provider: {provider}")


def run_indexing(file_path, topic_name, mode, job_id):
    try:
        llm = get_llm()
        parser = PDFParser(file_path=file_path, mode=mode, llm=llm)
        document = parser.parse()
        jobs = _load_jobs()
        jobs[job_id] = {"status": "parsed"}
        _save_jobs(jobs)

        indexer = Indexer(llm=llm)
        tree_docs = indexer.create_index(document, indexer_prompt=INDEXER_PROMPT, batch_size=5, max_page=10)

        storage = Storage()
        doc_id = storage.add_to_storage(tree_docs=tree_docs, topic_name=topic_name, file_path=file_path, doc_pages=document.pages)
        jobs = _load_jobs()
        jobs[job_id] = {"status": "indexed", "doc_id": doc_id}
        _save_jobs(jobs)
    except Exception as e:
        jobs = _load_jobs()
        jobs[job_id] = {"status": "error", "error": str(e)}
        _save_jobs(jobs)

@app.post("/add_document/", summary="Upload a document for indexing")
def add_document(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(..., description="The PDF document you want to index."), 
    topic_name: str = Query("default", description="A name to group related documents, like a folder."), 
    mode: str = Query("text", description="Parsing mode ('text' or 'vision'). Currently only 'text' is fully supported.")
):
    """
    Accepts a PDF file and starts a background task to index it.
    
    - **file**: The PDF document to be indexed.
    - **topic_name**: A string to categorize or group your documents. Think of it like a collection or a folder.
    - **mode**: The parsing mode. Use 'text' for standard text extraction.
    
    Returns a `job_id` which you can use to check the status of the indexing process.
    """
    # Step 1: Save the uploaded file to disk
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())
    
    job_id = str(uuid.uuid4())
    jobs = _load_jobs()
    jobs[job_id] = {"status": "processing"}
    _save_jobs(jobs)
    background_tasks.add_task(run_indexing, file_location, topic_name, mode, job_id)

    return {"job_id": job_id, "status": "processing"}

@app.get("/status/{job_id}", summary="Check the status of an indexing job")
def get_status(job_id: str):
    """
    Retrieves the current status of a background indexing job.
    
    - **job_id**: The ID returned from the `/add_document/` endpoint.
    
    Possible statuses: `processing`, `parsed`, `indexed`, `error`.
    If the status is `indexed`, the response will also include the `doc_id`.
    """
    jobs = _load_jobs()
    if job_id in jobs:
        return {"job_id": job_id, **jobs[job_id]}
    else:
        return {"error": "Job ID not found"}

@app.post("/query/", summary="Query your indexed documents")
def query(
    topic_name: str = Query(..., description="The topic you want to search within."), 
    query: str = Query(..., description="Your question or the information you want to retrieve.")
):
    """
    Searches for an answer to your query within a specific topic.
    
    - **topic_name**: The collection of documents you want to query.
    - **query**: The natural language question you want to ask.
    
    The system will use an LLM to reason over the document's structure and retrieve the most relevant information.
    """
    try:
        messages =[]
        messages.append({"role":"user","content":f"Question: {query}"}) 

        llm = get_llm()
        retriever = Retriever()
        final_response, _ = retriever.retrieve(query=query, topic_name=topic_name, llm=llm)
        messages.append({"role":"assistant","content":f"Answer: {final_response}"}) 
        
        return {"response": final_response}
    except Exception as e:
        import traceback
        return {"error": str(e), "detail": traceback.format_exc()}

@app.get("/topics/", summary="List all available topics")
def get_topics():
    """Returns a list of all unique topic names that contain indexed documents."""
    storage = Storage()
    return {"topics": storage.get_topics()}

@app.get("/llms/", summary="Get LLM provider information")
def get_supported_llms():
    """Shows all supported LLM providers and which one is currently configured via environment variables."""
    return {
        "supported_providers": ["openai", "gemini", "claude", "ollama"],
        "current_provider": os.getenv("LLM_PROVIDER", "openai")
    }

@app.get("/topic_name/", summary="DEPRECATED: List all available topics")
def get_topic_name():
    """DEPRECATED in favor of /topics/. Returns a list of all unique topic names."""
    storage = Storage()
    return {"topics": storage.get_topics()}


@app.get("/topics/{topic_name}/documents", summary="List all documents in a topic")
def get_topic_documents(topic_name: str):
    """Retrieves the IDs of all documents indexed under a specific topic name."""
    storage = Storage()
    topic_index = storage.get_topic_index(topic_name)
    return {"topic": topic_name, "documents": list(topic_index.keys())}

@app.post("/chat/", summary="Chat with your documents (for persistent conversations)")
def chat(
    topic_name: str = Query(..., description="The topic you want to search within."),
    query: str = Query(..., description="Your question or the information you want to retrieve."),
    rating: int = Query(None, ge=0, le=1, description="Optional. Provide 0 or 1 immediately to auto-trigger feedback and wiki update."),
    comment: str = Query(None, description="Optional comment alongside the rating.")
):
    """
    Chat with your indexed documents. Optionally pass a `rating` (0 or 1) in the same call to
    automatically record feedback and — if rating=1 — rebuild the topic wiki immediately.
    
    - **topic_name**: The collection of documents you want to query.
    - **query**: Your message or question.
    - **rating**: (optional) 0 = bad, 1 = good. If provided, feedback and wiki update happen automatically.
    """
    try:
        llm = get_llm()
        result = Chat().send(query=query, topic_name=topic_name, llm=llm)
        if rating is not None:
            feedback_result = Chat().feedback(
                message_id=result["message_id"], rating=rating, llm=llm, comment=comment
            )
            result["feedback"] = feedback_result
        history = Chat().get_history(topic_name)
        return {**result, "conversation_history": history}
    except Exception as e:
        import traceback
        return {"error": str(e), "detail": traceback.format_exc()}
    
@app.get("/chats/{topic_name}", summary="Get chat history for a topic")
def get_chat_history(topic_name: str):
    """Retrieves the conversation history for a specific topic."""
    return {"topic": topic_name, "conversation_history": Chat().get_history(topic_name)}



@app.post("/feedback/", summary="Provide feedback on a response")
def feedback(
    message_id: str = Query(..., description="The ID of the message to rate (returned from /chat/)."),
    rating: int = Query(..., ge=0, le=1, description="0 = bad, 1 = good."),
    comment: str = Query(None, description="Optional comment.")
):
    """
    Rate a chat response. If rating=1, the Q&A pair is summarized by the LLM and saved
    as a synthesized knowledge node in the topic index for future retrieval.
    """
    try:
        llm = get_llm()
        return Chat().feedback(message_id=message_id, rating=rating, llm=llm, comment=comment)
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        import traceback
        return {"error": str(e), "detail": traceback.format_exc()}


@app.post("/wiki_builder/", summary="Build a simple wiki from a topic")
def build_wiki(topic_name: str = Query(..., description="The topic you want to build a wiki for.")):
    """
    Generates a simple wiki-style summary of all the documents in a topic using the LLM.
    
    - **topic_name**: The collection of documents you want to summarize into a wiki.
    
    The system will create a structured summary that captures the key information across all documents in the topic.
    """
    try:
        llm = get_llm()
        return WikiBuilder().build(topic_name=topic_name, llm=llm)
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        import traceback
        return {"error": str(e), "detail": traceback.format_exc()}


@app.get("/topics/{topic_name}/wiki", summary="Read the wiki for a topic")
def get_wiki(topic_name: str):
    """
    Returns the current wiki markdown for a topic, if it exists.
    The wiki is built from approved (thumbs-up) Q&A pairs via /wiki_builder/ or automatically on feedback.
    """
    wiki_path = os.path.join("wiki", f"{topic_name}.md")
    if not os.path.exists(wiki_path):
        return {"error": f"No wiki found for topic '{topic_name}'. Use /wiki_builder/ to generate one."}
    with open(wiki_path, "r") as f:
        content = f.read()
    return {"topic_name": topic_name, "wiki_path": wiki_path, "content": content}