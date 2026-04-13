# VectorlessRAG

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

## The problem with RAG today

You split your 200-page annual report into chunks.
You embed them.
You search by similarity.
You get back 5 random paragraphs that *kinda* match the question.
Your LLM hallucinates the rest.

**Chunking destroys context. Embeddings find similar words, not answers. Vector search doesn't understand documents — it just pattern matches.**

This problem gets worse with structured documents — financial statements, legal contracts, technical specifications — where every row in a table depends on the rows around it. Split them into chunks and you lose the table entirely.

---

## How VectorlessRAG works

Instead of chunking, VectorlessRAG reads your document like a human analyst would:

**Step 1 — Parse**
Every page is extracted as raw text using `pdfplumber` (digital PDFs) or vision mode using `PyMuPDF` + an LLM (scanned/image PDFs). No chunking. Pages are stored in order.

**Step 2 — Index**
An LLM reads the document and builds a hierarchical JSON tree — like a smart table of contents with factual summaries at every level. Each node knows its exact page range.

```
Microsoft Annual Report (pages 1-220)
├── Financial Statements (pages 34-45)
│   ├── INCOME STATEMENTS (pages 36-37)       ← pages 36-37 stored
│   ├── BALANCE SHEETS (pages 38-39)           ← pages 38-39 stored
│   └── CASH FLOW STATEMENTS (pages 40-41)    ← pages 40-41 stored
├── Notes to Financial Statements (pages 46-130)
│   ├── Note 5 — Income Taxes (pages 58-60)
│   └── Note 16 — Other Income (pages 88-89)
└── ...
```

Large documents (>10 pages) are indexed in parallel batches using `ThreadPoolExecutor`. Each batch is given its absolute page range so the LLM never uses printed footer page numbers.

**Step 3 — Retrieve**
At query time, the tree is flattened to a compact JSON list of `{node_id, title, pages, summary}`. An LLM reads this list and returns the node IDs most likely to contain the answer. The actual pages for those nodes are fetched with a ±3 page buffer to handle slight indexing offsets.

**Step 4 — Answer**
The retrieved page text is sent to the LLM with the full query. The LLM reasons over real document content — not chunks, not embeddings, not summaries. It can compute derived metrics, compare across sections, and produce structured output.

---

## What it can actually do

These are real queries run against the Microsoft FY2025 Annual Report (220 pages):

**Fetch a complete financial statement**
```
Query: "fetch the income statement"

Response: Full table with Product/Service revenue breakdown, COGS, Gross Margin,
R&D, S&M, G&A, Operating Income, Other Income, Tax, Net Income, EPS (basic + diluted),
weighted average shares — all three years.
```

**Compute derived financial metrics**
```
Query: "what is the net profit margin and tell me the trend"

Response: Calculated NPM for FY2023 (34.14%), FY2024 (35.96%), FY2025 (36.14%)
with trend interpretation.
```

**Multi-statement analysis (DuPont)**
```
Query: "is it a good company to invest? do dupont analysis"

Response: Full DuPont decomposition pulling from both income statement and balance sheet:
NPM × Asset Turnover × Equity Multiplier = ROE (29.65%), plus investment thesis
with risks, shareholder return analysis, and ESG commentary.
```

**Build a financial model**
```
Query: "build a 3-year DCF model with 10% discount rate and 3% terminal growth rate"

Response: Full projected FCF model with historical anchors, revenue growth assumptions,
CapEx projections, discounted cash flows, terminal value, and enterprise value estimate.
```

**Compute a metric not printed in any statement**
```
Query: "compute the free cash flow"

Response: OCF ($136,162M) − CapEx ($64,551M) = FCF $71,611M — correctly sourced
from the Cash Flow Statement.
```

---

## Quickstart

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure your LLM**
```env
# .env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
```

**3. Use as a Python library**
```python
from vectorlessrag import VectorLessRag
from llms.gemini_llm import GeminiLLM

llm = GeminiLLM(api_key="your-key")
rag = VectorLessRag(llm=llm)

# Index a document (runs in background)
job_id = rag.add_document("microsoft_10k.pdf", topic_name="annual_reports", mode="text")

# Poll until indexed
status = rag.get_status(job_id)  # "processing" → "indexed"

# Query
answer = rag.query("What was the net profit margin trend?", topic_name="annual_reports")
print(answer)
```

**4. Or run as a REST API**
```bash
uvicorn api.api:app --host 0.0.0.0 --port 8000
```

Interactive docs available at `http://localhost:8000/docs`

---

## REST API Reference

### POST `/add_document/`
Upload a PDF and start indexing in the background.

**Parameters (multipart form):**
| Field | Type | Description |
|---|---|---|
| `file` | File | PDF file to index |
| `topic_name` | string | Collection to add the document to |
| `mode` | string | `text` (default) or `vision` for scanned PDFs |

**Response:**
```json
{
  "job_id": "0248547e-a69e-46d6-987f-8612051957f6",
  "status": "processing"
}
```

---

### GET `/status/{job_id}`
Check indexing progress.

**Response:**
```json
{
  "job_id": "0248547e-...",
  "status": "indexed",
  "doc_id": "temp_2025_AnnualReport_0541c6"
}
```

Possible statuses: `processing` → `parsed` → `indexed` | `error`

---

### POST `/query/`
Query your indexed documents.

**Parameters (query string):**
| Field | Type | Description |
|---|---|---|
| `topic_name` | string | Topic to search within |
| `query` | string | Natural language question |

**Response:**
```json
{
  "response": "The net profit margin for FY2025 was 36.14%..."
}
```

The system retrieves the relevant pages and synthesizes a complete answer. If the query asks for a table or statement, it reproduces all rows exactly.

---

### GET `/topics/`
List all available topics.

### GET `/topics/{topic_name}/documents`
List all documents indexed under a topic.

### GET `/llms/`
Show the currently configured LLM provider.

---

## Multi-document topics

Upload multiple documents to the same topic and query across all of them simultaneously. The retriever loops over every document in the topic and merges results before synthesis.

```bash
# Upload three annual reports to one topic
curl -X POST "http://localhost:8000/add_document/" \
  -F "file=@microsoft_2025.pdf" -F "topic_name=big_tech"

curl -X POST "http://localhost:8000/add_document/" \
  -F "file=@apple_2025.pdf" -F "topic_name=big_tech"

curl -X POST "http://localhost:8000/add_document/" \
  -F "file=@google_2025.pdf" -F "topic_name=big_tech"

# Query across all three
curl -X POST "http://localhost:8000/query/?topic_name=big_tech&query=compare+net+profit+margins+and+recommend+the+best+investment"
```

---

## Supported LLMs

Set `LLM_PROVIDER` in `.env` and provide the corresponding API key. No code changes needed to switch providers.

| Provider | `LLM_PROVIDER` | Key variable |
|---|---|---|
| OpenAI (GPT-4o) | `openai` | `OPENAI_API_KEY` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |
| Anthropic Claude | `claude` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama` | — |

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
```

Vision mode (for scanned PDFs) requires a multimodal LLM. Gemini 1.5 Pro and GPT-4o both work. Ollama support depends on the local model.

---

## Parsing modes

| Mode | How it works | When to use |
|---|---|---|
| `text` | `pdfplumber` extracts text layer | Digital/native PDFs (reports, docs) |
| `vision` | `PyMuPDF` renders each page to PNG, LLM reads the image | Scanned PDFs, image-based documents |

```python
# Text mode (fast, cheap)
rag.add_document("report.pdf", topic_name="docs", mode="text")

# Vision mode (slower, handles scans)
rag.add_document("scanned_contract.pdf", topic_name="legal", mode="vision")
```

---

## Docker

```bash
docker build -t vectorlessrag .
docker run -p 8000:8000 --env-file .env vectorlessrag
```

---

## Project structure

```
vectorlessindex/
├── vectorlessrag.py          # Main Python library entry point
├── api/
│   └── api.py                # FastAPI app — all endpoints
├── parsers/
│   └── pdf_parser.py         # Text + vision PDF parsing
├── indexer/
│   └── indexer.py            # Builds hierarchical JSON tree index
├── retrievers/
│   └── retriever.py          # Flattens tree, selects nodes, fetches pages
├── storage/
│   └── storage.py            # File-based JSON storage per topic
├── llms/
│   ├── base.py               # BaseLLM abstract class
│   ├── gemini_llm.py
│   ├── openai_llm.py
│   ├── claude_llm.py
│   └── ollama_llm.py
├── prompts/
│   ├── indexer_prompt.py     # Instructs LLM to build the tree
│   └── retriever_prompt.py   # Instructs LLM to select relevant nodes
└── core/
    └── config.py             # LLM provider config from .env
```

---

## How the tree index works

Each document is stored as a nested JSON tree. Every node contains:

```json
{
  "node_id": "0036",
  "title": "INCOME STATEMENTS",
  "start_index": 36,
  "end_index": 37,
  "summary": "Consolidated income statement for FY2025/24/23. Revenue $281.7B/$245.1B/$211.9B. Net income $101.8B/$88.1B/$72.4B. Diluted EPS $13.64/$11.80/$9.68.",
  "sub_nodes": []
}
```

Parent nodes use `prefix_summary` (broad overview). Leaf nodes use `summary` (specific facts, numbers, names). The retriever sends only leaf summaries to the selection LLM — keeping the prompt small while preserving enough detail to pick the right section.

For large documents, indexing runs in parallel batches. Each batch is given its **absolute page range** in the prompt so the LLM never mistakes printed footer page numbers (e.g. "Page 70" in a footer) for actual document position. This was a critical fix for annual reports and 10-Ks where internal page numbering differs from PDF page position.

---

## Why not just use Claude/ChatGPT file upload?

| | Claude / ChatGPT Upload | VectorlessRAG |
|---|---|---|
| Document size | ~50 pages reliably | Unlimited (batched indexing) |
| Persistence | Gone when session ends | Stored, queryable forever |
| Multi-document | One at a time | Multiple per topic |
| API access | Manual UI only | REST API — any app can call it |
| Cost per query | Full doc reprocessed every time | Index once, cheap queries |
| Cross-doc analysis | Manual, session-scoped | Native |
| Programmatic | No | Yes |

Claude is a tool. VectorlessRAG is infrastructure — a queryable document intelligence backend that any application can integrate.

---

## Adding a new LLM provider

Create a file in `llms/` that extends `BaseLLM`:

```python
from llms.base import BaseLLM

class MyLLM(BaseLLM):
    def call(self, prompt: str) -> str:
        # your LLM call here
        return response_text

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        # optional — only needed for vision mode
        return response_text
```

Then add it to `core/config.py` under `get_llm()`. No other changes needed.

---

## Contributing

Open source. PRs welcome.

- Found a bug? Open an issue.
- New LLM provider? Add a file to `llms/`.
- New parser? Add a file to `parsers/`.

---

> *Built with the belief that documents deserve better than chunking.*

