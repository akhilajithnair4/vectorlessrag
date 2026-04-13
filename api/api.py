from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Query, Body
import json
from indexer.indexer import Indexer
from parsers.pdf_parser import PDFParser    
from prompts.indexer_prompt import INDEXER_PROMPT
from retrievers.retriever import Retriever
from storage.storage import Storage
from llms.base import BaseLLM
import uuid
import os
from llms.openai_llm import OpenAILLM
from llms.gemini_llm import GeminiLLM
from llms.claude_llm import ClaudeLLM
from llms.ollama_llm import OllamaLLM
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)


def start():
    import uvicorn
    uvicorn.run("api.api:app", host="0.0.0.0", port=8000, reload=False)


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
        llm = get_llm()
        retriever = Retriever()
        final_response, _ = retriever.retrieve(query=query, topic_name=topic_name, llm=llm)
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