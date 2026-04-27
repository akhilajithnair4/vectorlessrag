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

## 😤 The problem with RAG today

You split your 200-page document into chunks. You embed them. You search by similarity. You get back 5 random paragraphs that *kind of* match the question. Your LLM hallucinates the rest.

This is particularly brutal with structured documents — clinical protocols, legal contracts, technical specs, financial statements — where every row in a table depends on the rows around it. Split them into chunks and you lose the table entirely. The chunk boundary lands right in the middle of a dosage table and suddenly your model is making up numbers.

**Chunking destroys context. Embeddings find similar words, not answers. Vector search doesn't understand documents — it just pattern-matches.**

---

## 💡 How VectorlessRAG works

Instead of chunking, VectorlessRAG reads your document like a human analyst would:

**Step 1 — Parse** 📄  
Every page is extracted as raw text using `pdfplumber` (digital PDFs) or vision mode using `PyMuPDF` + LLM (scanned/image PDFs). Pages are stored in order. No chunking. No overlap tricks.

**Step 2 — Index** 🌲  
An LLM reads the document in batches and builds a hierarchical JSON tree — like a smart table of contents where every node has a factual summary and an exact page range.

```
Clinical Trial Protocol — Study XYZ-001 (pages 1-180)
├── Study Overview (pages 1-8)
│   ├── Primary Endpoints (pages 3-4)
│   └── Eligibility Criteria (pages 5-7)
├── Treatment Arms (pages 9-45)
│   ├── Arm A — Dose Escalation Schedule (pages 12-18)
│   └── Arm B — Control Group Parameters (pages 19-24)
├── Safety Monitoring (pages 46-90)
│   ├── Adverse Event Definitions (pages 48-52)
│   └── Stopping Rules (pages 61-65)
└── Statistical Analysis Plan (pages 91-120)
```

Large documents are indexed in parallel batches. Each batch gets its absolute page range so the LLM never confuses footer page numbers (e.g. "Page 70" printed at the bottom) with actual PDF position.

**Step 3 — Retrieve** 🔍  
At query time the tree is flattened to a compact list of `{node_id, title, pages, summary}`. An LLM reads this list and picks the node IDs most likely to contain the answer. The actual pages for those nodes are fetched with a ±3 page buffer.

**Step 4 — Answer** 🧠  
The retrieved page text goes to the LLM with your full query. It reasons over real document content — not summaries, not embeddings, not synthetic rephrasing. Full rows in tables. Full sentences. Full context.

---

## ⚔️ VectorlessRAG vs PageIndex

Both systems use the same core approach — hierarchical tree index, no vectors, no chunking, LLM reasoning for retrieval. Here's where they diverge:

| | PageIndex | VectorlessRAG |
|---|---|---|
| **Core idea** | Hierarchical tree index, LLM reasoning retrieval | Same |
| **Vectorless** | ✅ | ✅ |
| **No chunking** | ✅ | ✅ |
| **Persistent chat** | ❌ | ✅ Sliding window history per topic |
| **Feedback loop** | ❌ | ✅ 0/1 rating on any response |
| **Knowledge injection** | ❌ | ✅ Thumbs-up → LLM summarizes Q&A → node injected into index |
| **Wiki builder** | ❌ | ✅ Approved Q&As compiled into a living markdown wiki |
| **Multi-doc topics** | ❌ | ✅ Multiple docs per topic, queried together |
| **REST API** | External cloud API | ✅ Self-hosted FastAPI, runs locally |

What VectorlessRAG adds is the **knowledge compounding loop**. Every conversation you have with your documents gets better over time — good answers get injected back as knowledge nodes, your approved Q&As build into a wiki, and future retrievals benefit from that accumulated context. It's built for teams that are going to live inside a document set for months, not just run one-off queries.

---


## 🚀 What it can actually do

Here are real examples across different document types — not just financial reports.

---

### 🧪 Clinical & Pharma Documents

Index a clinical trial protocol (180 pages, complex eligibility criteria, dose tables, stopping rules):

```python
rag.add_document("study_xyz001_protocol.pdf", topic_name="clinical_xyz", mode="text")
```

```
Query: "what are the dose-limiting toxicity criteria for arm A?"

Response: DLT criteria for Arm A (pages 14-16): Grade 3 non-hematologic toxicity
lasting >7 days, Grade 4 hematologic toxicity, any Grade 3 cardiac event, dose
delay >14 days due to drug-related adverse events. Primary DLT window is Cycle 1
(Days 1-21). Exceptions listed for Grade 3 alopecia and Grade 3 nausea controlled
within 48hrs with antiemetics.
```

```
Query: "compare primary endpoints between the two arms"

Response: Arm A primary endpoint — maximum tolerated dose (MTD) determination
with secondary ORR at 12 weeks. Arm B primary endpoint — PFS at 6 months vs
placebo. Statistical power calculations: Arm A uses 3+3 dose escalation with
N=6-18, Arm B uses superiority design with 80% power, α=0.05, N=120 per arm.
```

```
Query: "what happens if two patients in the same cohort experience a DLT?"

Response: Per the stopping rules (page 63): if 2/6 patients in any cohort experience
a DLT, dose escalation halts. The cohort is expanded to 6 patients if initial 3
show 1 DLT. If 2/6 DLTs are confirmed, that dose level is declared the maximum
administered dose (MAD) and the previous dose becomes the MTD recommendation.
```

---

### ⚖️ Legal Contracts

Index a 120-page master service agreement:

```
Query: "what are our termination rights if the vendor has a data breach?"

Response: Section 14.3 (pages 67-68): Client may terminate for cause with 30 days
written notice if Vendor (a) fails to notify Client of a Security Incident within
72 hours of discovery, (b) experiences two or more material breaches of Section 8
(Data Security) within any 12-month period, or (c) fails to obtain SOC 2 Type II
certification by the date specified in Exhibit C. Termination for cause triggers
the Transition Assistance obligations in Section 19.
```

```
Query: "summarize all the SLA commitments and penalties"

Response: [Full table extracted — uptime commitments, response time SLAs,
penalty credits as % of monthly fees, escalation paths, exclusions, and
the carve-out for force majeure events]
```

---

### 🏗️ Technical Specifications

Index a product requirements doc or architecture spec:

```
Query: "what are the latency requirements for the payment processing service?"

Response: Section 4.2.1 (pages 23-24): p50 latency ≤120ms, p95 ≤400ms, p99 ≤800ms
measured at the API gateway. Timeout threshold is 2000ms after which the transaction
is voided and the client receives error code PAY-408. Load testing target is 5000
concurrent sessions with no degradation beyond the p99 threshold.
```

```
Query: "list every integration point and its authentication method"

Response: [Full table — 11 services, their endpoints, auth methods (OAuth2, API key,
mTLS), timeout configs, retry policies, and circuit breaker thresholds]
```

---

### 📚 Research Papers & Literature Reviews

Index a batch of research papers into one topic, query across all of them:

```python
for paper in ["study_2022.pdf", "study_2023.pdf", "meta_analysis_2024.pdf"]:
    rag.add_document(paper, topic_name="nsclc_immunotherapy", mode="text")
```

```
Query: "what sample sizes were used across these studies and what were the response rates?"

Response: [Cross-paper comparison table — study name, N, intervention, ORR, median PFS,
follow-up duration, key confounders noted by each author]
```

```
Query: "do any of these papers contradict each other on PD-L1 cutoff thresholds?"

Response: Yes — Smith et al. (2022) uses PD-L1 ≥1% as the inclusion threshold and
reports ORR of 32%, while the 2024 meta-analysis reanalyses this cohort and argues
the effect is driven entirely by the PD-L1 ≥50% subgroup (ORR 61%). Chen et al.
(2023) used ≥50% cutoff from enrollment and reports consistent ORR of 58%, supporting
the meta-analysis conclusion.
```

---

### 📋 HR & Policy Documents

Index your entire employee handbook or compliance policy library:

```
Query: "what is the policy on secondary employment?"

Response: Section 3.7 (pages 44-45): Employees may engage in outside employment
provided it does not (a) conflict with company interests, (b) use company resources
or confidential information, or (c) exceed 8 hours per week during core business hours.
Written disclosure required annually to direct manager and HR. Violation is grounds
for disciplinary action up to and including termination.
```

---

## 💬 Persistent Chat

Unlike a one-shot query, the chat mode keeps a conversation going per topic. Ask follow-up questions. Reference things you said earlier. The last 20 messages are passed as sliding window context.

```python
rag = VectorLessRag(llm=llm)

# Start a conversation
r1 = rag.chat("what does section 4 cover?", topic_name="clinical_xyz")
print(r1["response"])
# → "Section 4 covers the Treatment Arms — Arm A dose escalation and Arm B control..."

r2 = rag.chat("and what are the exclusion criteria for arm A specifically?", topic_name="clinical_xyz")
print(r2["response"])
# → "For Arm A, exclusion criteria include prior platinum therapy within 6 months,
#    ECOG >2, active CNS metastases, and creatinine clearance <30 mL/min..."

r3 = rag.chat("if a patient has CrCl of 35, can they enroll?", topic_name="clinical_xyz")
print(r3["response"])
# → "Yes — the cutoff is <30 mL/min. A CrCl of 35 mL/min meets the eligibility
#    threshold for Arm A and would not be excluded on this criterion alone."
```

Each response includes a `message_id`. Use it to rate the answer.

---

## 👍 Feedback + Knowledge Injection

Rate any response after reading it. A thumbs-up does three things automatically:
1. Saves the rating to the conversation history
2. Has the LLM summarize the Q&A into a compact knowledge node
3. Injects that node into the document's index tree for future retrievals
4. Rebuilds the topic wiki

```python
# Step 1 — ask
result = rag.chat("what are the stopping rules?", topic_name="clinical_xyz")
print(result["response"])

# Step 2 — read the answer, then rate
rag.feedback(result["message_id"], rating=1)

print(result["feedback"]["node_injected"])
# → "DLT Stopping Rules — Arm A Cohort Escalation"

print(result["feedback"]["wiki_updated"])
# → "wiki/clinical_xyz.md"
```

---

## 📖 Wiki Builder

Every thumbs-up builds your knowledge base. The wiki builder takes all your approved Q&A pairs for a topic and asks the LLM to compile them into a structured markdown wiki — overview, key findings, entities, metrics, open questions, contradictions.

It runs automatically on every `rating=1`. But you can also trigger it manually:

```python
result = rag.build_wiki(topic_name="clinical_xyz")
# Writes to wiki/clinical_xyz.md
```

Or hit the API directly:

```bash
curl -X POST "http://localhost:8000/wiki_builder/?topic_name=clinical_xyz"
```

The wiki is **cumulative** — each run reads the existing wiki and updates it with new approved pairs. So it gets better the more you use it.

---

## ⚡ Quickstart

**1. Install**
```bash
pip install vectorlessrag
```

Or from source:
```bash
git clone https://github.com/yourusername/vectorlessrag.git
cd vectorlessrag
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

# Index a document
doc_id = rag.add_document("protocol.pdf", topic_name="study_xyz", mode="text")

# One-shot query
answer = rag.query("what are the primary endpoints?", topic_name="study_xyz")
print(answer)

# Persistent chat — ask first, read the answer, then rate
result = rag.chat("what are the dose-limiting toxicity criteria?", topic_name="study_xyz")
print(result["response"])

# After reading the answer, decide if it was good
rag.feedback(result["message_id"], rating=1)  # thumbs up → injects knowledge node + rebuilds wiki
rag.feedback(result["message_id"], rating=0)  # thumbs down → just records it, no injection
```

**4. Or run as a REST API**
```bash
uvicorn api.api:app --host 0.0.0.0 --port 8000
```

Interactive docs at `http://localhost:8000/docs`

---

## 🔌 REST API Reference

### POST `/add_document/`
Upload a PDF and start indexing in the background.

| Field | Type | Description |
|---|---|---|
| `file` | File | PDF file to index |
| `topic_name` | string | Collection to add the document to |
| `mode` | string | `text` (default) or `vision` for scanned PDFs |

```json
{ "job_id": "0248547e-a69e-46d6-987f-8612051957f6", "status": "processing" }
```

---

### GET `/status/{job_id}`
Check indexing progress. Statuses: `processing` → `parsed` → `indexed` | `error`

---

### POST `/query/`
One-shot question against a topic.

| Param | Description |
|---|---|
| `topic_name` | Topic to search within |
| `query` | Natural language question |

---

### POST `/chat/`
Persistent conversation with sliding window history.

| Param | Description |
|---|---|
| `topic_name` | Topic to chat with |
| `query` | Your message |
| `rating` | `0` or `1` — optional, triggers feedback + wiki update in the same call |
| `comment` | Optional text comment alongside the rating |

---

### POST `/feedback/`
Rate a past response by `message_id`.

| Param | Description |
|---|---|
| `message_id` | ID returned from `/chat/` |
| `rating` | `0` (bad) or `1` (good) |
| `comment` | Optional comment |

---

### POST `/wiki_builder/`
Build or update a topic wiki from all thumbs-up Q&A pairs.

| Param | Description |
|---|---|
| `topic_name` | The topic to build a wiki for |

---

### GET `/chats/{topic_name}`
Get the full conversation history for a topic.

### GET `/topics/`
List all topics with indexed documents.

### GET `/topics/{topic_name}/documents`
List all document IDs under a topic.

### GET `/llms/`
Show current LLM provider configuration.

---

## 📦 Multi-document topics

Add multiple documents to the same topic. The retriever queries every document in parallel and merges before synthesis.

```bash
# Index multiple documents under one topic
curl -X POST "http://localhost:8000/add_document/" \
  -F "file=@protocol_v1.pdf" -F "topic_name=study_xyz"

curl -X POST "http://localhost:8000/add_document/" \
  -F "file=@protocol_amendment_1.pdf" -F "topic_name=study_xyz"

curl -X POST "http://localhost:8000/add_document/" \
  -F "file=@investigators_brochure.pdf" -F "topic_name=study_xyz"

# Query across all three at once
curl -X POST "http://localhost:8000/query/?topic_name=study_xyz&query=have+the+stopping+rules+changed+between+protocol+versions"
```

---

## 🤖 Supported LLMs

| Provider | `LLM_PROVIDER` | Key variable |
|---|---|---|
| OpenAI (GPT-4o) | `openai` | `OPENAI_API_KEY` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |
| Anthropic Claude | `claude` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama` | — (no key needed) |

Vision mode requires a multimodal model. Gemini 1.5 Pro and GPT-4o both work well for scanned PDFs.

---

## 🔬 Parsing modes

| Mode | How it works | When to use |
|---|---|---|
| `text` | `pdfplumber` extracts text layer | Digital/native PDFs |
| `vision` | `PyMuPDF` renders each page to image, LLM reads it | Scanned PDFs, image-heavy docs |

```python
rag.add_document("native_report.pdf", topic_name="docs", mode="text")
rag.add_document("scanned_contract.pdf", topic_name="legal", mode="vision")
```

---

## 🗂️ Project structure

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
├── chat/
│   └── chat.py               # Persistent chat, feedback, knowledge injection
├── wiki/
│   └── wiki_builder.py       # Compiles approved Q&As into a topic wiki
├── llms/
│   ├── base.py               # BaseLLM abstract class
│   ├── gemini_llm.py
│   ├── openai_llm.py
│   ├── claude_llm.py
│   └── ollama_llm.py
├── prompts/
│   ├── indexer_prompt.py     # Instructs LLM to build the tree
│   ├── retriever_prompt.py   # Instructs LLM to select relevant nodes
│   └── wiki_builder_prompt.py # Instructs LLM to compile a wiki
└── core/
    └── config.py             # Shared constants (CHAT_HISTORY path, etc.)
```

---

## 🌲 How the tree index works

Each document is stored as a nested JSON tree. Every node has:

```json
{
  "node_id": "0048",
  "title": "Dose-Limiting Toxicity Criteria — Arm A",
  "start_index": 13,
  "end_index": 16,
  "summary": "DLT defined as Grade 3 non-hematologic >7 days, Grade 4 hematologic, Grade 3 cardiac, or dose delay >14 days. Evaluation window is Cycle 1 Days 1-21. Exceptions for alopecia and brief nausea.",
  "sub_nodes": []
}
```

Parent nodes use `prefix_summary` (broad overview of a section). Leaf nodes use `summary` (specific facts, numbers, thresholds). The retriever only sends leaf summaries to the selection LLM — keeps the prompt small and focused.

---

## 🐳 Docker

```bash
docker build -t vectorlessrag .
docker run -p 8000:8000 --env-file .env vectorlessrag
```

---

## ➕ Adding a new LLM

Create a file in `llms/` that extends `BaseLLM`:

```python
from llms.base import BaseLLM

class MyLLM(BaseLLM):
    def call(self, prompt: str) -> str:
        # your LLM call here
        return response_text

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        # only needed for vision mode
        return response_text
```

No other changes needed — `core/config.py` picks it up from `LLM_PROVIDER`.

---

## 🤝 Contributing

Open source. PRs welcome.

- Found a bug? Open an issue.
- New LLM provider? Add a file to `llms/`.
- New parser? Add a file to `parsers/`.

---

> *Built because documents deserve better than chunking.*

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

**1. Install**
```bash
pip install vectorlessrag
```

Or from source:
```bash
git clone https://github.com/akhilajithnair4/vectorlessrag.git
cd vectorlessrag
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
vectorlessrag
```

Or manually:
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

