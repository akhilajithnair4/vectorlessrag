# 🧠 VectorlessRAG

> **No vectors. No embeddings. No chunking. Just intelligence.**

```
 ██╗   ██╗███████╗ ██████╗████████╗ ██████╗ ██████╗ ██╗     ███████╗███████╗███████╗
 ██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██║     ██╔════╝██╔════╝██╔════╝
 ██║   ██║█████╗  ██║        ██║   ██║   ██║██████╔╝██║     █████╗  ███████╗███████╗
 ╚██╗ ██╔╝██╔══╝  ██║        ██║   ██║   ██║██╔══██╗██║     ██╔══╝  ╚════██║╚════██║
  ╚████╔╝ ███████╗╚██████╗   ██║   ╚██████╔╝██║  ██║███████╗███████╗███████║███████║
   ╚═══╝  ╚══════╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚══════╝
                                    RAG
```

---

## 😤 The problem with RAG today

You split your 200-page annual report into chunks.
You embed them.
You search by similarity.
You get back 5 random paragraphs that *kinda* match the question.
Your LLM hallucinates the rest.

Sound familiar?

**Chunking destroys context. Embeddings find similar words, not answers. Vector search doesn't understand documents — it just pattern matches.**

---

## 🧠 How VectorlessRAG works

Instead of chunking, VectorlessRAG reads your document like a human would:

1. 📄 **Parse** — extract every page as raw text (or use vision for scanned PDFs)
2. 🌲 **Index** — LLM reads the document and builds a hierarchical tree (like a smart table of contents with summaries at every level)
3. 🔍 **Retrieve** — at query time, LLM reads the tree summaries and picks exactly which sections contain the answer
4. 💬 **Answer** — only those pages are sent to the LLM. No noise. No hallucination from irrelevant chunks.

```
Your PDF
   └── 📁 Chapter 1: Financials          (pages 1-45)
         └── 📄 1.1 Revenue              (pages 10-12)  ← 🎯 LLM picks this
         └── 📄 1.2 Operating Costs      (pages 13-20)
   └── 📁 Chapter 2: Strategy            (pages 46-90)
         └── 📄 2.1 Market Expansion     (pages 50-60)  ← 🎯 and this
```

The LLM reasons about *structure*, not similarity. That's the difference.

---

## ⚡ Quickstart

```bash
pip install -r requirements.txt
```

```python
from vectorlessrag import VectorLessRag
from llms.openai_llm import OpenAILLM

llm = OpenAILLM(api_key="your-key")
rag = VectorLessRag(llm=llm)

# 📥 Index a document
doc_id = rag.add_document("apple_annual_report.pdf", topic_name="annual_reports", mode="text")

# 💬 Ask a question
answer = rag.query("What was Apple's revenue in 2024?", topic_name="annual_reports")
print(answer)
```

That's it.

---

## 🚀 Run as an API

```bash
uvicorn api.api:app --reload
```

Or with Docker 🐳:

```bash
docker build -t vectorlessrag .
docker run -p 8000:8000 --env-file .env vectorlessrag
```

### 📡 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/add_document/` | 📤 Upload a PDF and index it |
| `GET` | `/status/{job_id}` | ⏳ Check indexing progress |
| `POST` | `/query/` | 💬 Ask a question |
| `GET` | `/topics/` | 📂 List all topics |
| `GET` | `/topics/{topic_name}/documents` | 📄 List docs in a topic |
| `GET` | `/llms/` | 🤖 See supported LLM providers |

### 🧪 Example

```bash
# 📤 Upload a document
curl -X POST http://localhost:8000/add_document/ \
  -F "file=@apple_report.pdf" \
  -F "topic_name=annual_reports"

# Returns: {"job_id": "abc123", "status": "processing"}

# ⏳ Check status
curl http://localhost:8000/status/abc123

# 💬 Ask a question
curl -X POST "http://localhost:8000/query/?topic_name=annual_reports&query=What+was+revenue+in+2024"
```

---

## 🤖 Supported LLMs

Set your provider in `.env` — swap anytime, no code changes needed.

| Provider | `.env` setting |
|----------|---------------|
| 🟢 OpenAI (GPT-4) | `LLM_PROVIDER=openai` |
| 🔵 Google Gemini | `LLM_PROVIDER=gemini` |
| 🟠 Anthropic Claude | `LLM_PROVIDER=claude` |
| 🐑 Ollama (local) | `LLM_PROVIDER=ollama` |

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

---

## ⚔️ Why no vectors?

| | 😰 Vector RAG | 🧠 VectorlessRAG |
|--|------------|---------------|
| Setup | Embed everything first | Just index |
| Cost | 💸 Pay per embedding | Pay per query only |
| Long docs | Chunks lose context | Full page context preserved |
| Accuracy | Similarity matching | Reasoning-based retrieval |
| Hallucination | 😬 Common (wrong chunks) | ✅ Rare (exact pages) |

---

## 🗂️ Project structure

```
vectorlessindex/
    vectorlessrag.py      ← 🎯 main entry point
    parsers/              ← 📄 PDF text + vision extraction
    indexer/              ← 🌲 builds the document tree
    retrievers/           ← 🔍 finds relevant nodes at query time
    storage/              ← 💾 saves and loads trees + pages
    llms/                 ← 🤖 pluggable LLM providers
    prompts/              ← 📝 all LLM prompts
    api/                  ← 🚀 FastAPI REST interface
```

---

## 🤝 Contributing

This is open source and built to be used by anyone — solo developers, startups, and enterprises alike.

If you find a bug, open an issue. If you want to add a new LLM provider, add a file to `llms/` that extends `BaseLLM`. That's all it takes.

---

> 💡 *Built with the belief that documents deserve better than chunking.*


---

## The problem with RAG today

You split your 200-page annual report into chunks.
You embed them.
You search by similarity.
You get back 5 random paragraphs that *kinda* match the question.
Your LLM hallucinates the rest.

Sound familiar?

**Chunking destroys context. Embeddings find similar words, not answers. Vector search doesn't understand documents — it just pattern matches.**

---

## How VectorlessRAG works

Instead of chunking, VectorlessRAG reads your document like a human would:

1. **Parse** — extract every page as raw text (or use vision for scanned PDFs)
2. **Index** — LLM reads the document and builds a hierarchical tree (like a smart table of contents with summaries at every level)
3. **Retrieve** — at query time, LLM reads the tree summaries and picks exactly which sections contain the answer
4. **Answer** — only those pages are sent to the LLM. No noise. No hallucination from irrelevant chunks.

```
Your PDF
   └── Chapter 1: Financials          (pages 1-45)
         └── 1.1 Revenue              (pages 10-12)  ← LLM picks this
         └── 1.2 Operating Costs      (pages 13-20)
   └── Chapter 2: Strategy            (pages 46-90)
         └── 2.1 Market Expansion     (pages 50-60)  ← and this
```

The LLM reasons about *structure*, not similarity. That's the difference.

---

## Quickstart

```bash
pip install -r requirements.txt
```

```python
from vectorlessrag import VectorLessRag
from llms.openai_llm import OpenAILLM

llm = OpenAILLM(api_key="your-key")
rag = VectorLessRag(llm=llm)

# Index a document
doc_id = rag.add_document("apple_annual_report.pdf", topic_name="annual_reports", mode="text")

# Ask a question
answer = rag.query("What was Apple's revenue in 2024?", topic_name="annual_reports")
print(answer)
```

That's it.

---

## Run as an API

```bash
uvicorn api.api:app --reload
```

Or with Docker:

```bash
docker build -t vectorlessrag .
docker run -p 8000:8000 --env-file .env vectorlessrag
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/add_document/` | Upload a PDF and index it |
| `GET` | `/status/{job_id}` | Check indexing progress |
| `POST` | `/query/` | Ask a question |
| `GET` | `/topics/` | List all topics |
| `GET` | `/topics/{topic_name}/documents` | List docs in a topic |
| `GET` | `/llms/` | See supported LLM providers |

### Example

```bash
# Upload a document
curl -X POST http://localhost:8000/add_document/ \
  -F "file=@apple_report.pdf" \
  -F "topic_name=annual_reports"

# Returns: {"job_id": "abc123", "status": "processing"}

# Check status
curl http://localhost:8000/status/abc123

# Ask a question
curl -X POST "http://localhost:8000/query/?topic_name=annual_reports&query=What+was+revenue+in+2024"
```

---

## Supported LLMs

Set your provider in `.env` — swap anytime, no code changes needed.

| Provider | `.env` setting |
|----------|---------------|
| OpenAI (GPT-4) | `LLM_PROVIDER=openai` |
| Google Gemini | `LLM_PROVIDER=gemini` |
| Anthropic Claude | `LLM_PROVIDER=claude` |
| Ollama (local) | `LLM_PROVIDER=ollama` |

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

---

## Why no vectors?

| | Vector RAG | VectorlessRAG |
|--|------------|---------------|
| Setup | Embed everything first | Just index |
| Cost | Pay per embedding | Pay per query only |
| Long docs | Chunks lose context | Full page context preserved |
| Accuracy | Similarity matching | Reasoning-based retrieval |
| Hallucination | Common (wrong chunks) | Rare (exact pages) |

---

## Project structure

```
vectorlessindex/
    vectorlessrag.py      ← main entry point
    parsers/              ← PDF text + vision extraction
    indexer/              ← builds the document tree
    retrievers/           ← finds relevant nodes at query time
    storage/              ← saves and loads trees + pages
    llms/                 ← pluggable LLM providers
    prompts/              ← all LLM prompts
    api/                  ← FastAPI REST interface
```

---

## Contributing

This is open source and built to be used by anyone — solo developers, startups, and enterprises alike.

If you find a bug, open an issue. If you want to add a new LLM provider, add a file to `llms/` that extends `BaseLLM`. That's all it takes.

---

Built with the belief that documents deserve better than chunking.

