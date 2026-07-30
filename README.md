# Project Meridian

Project Meridian is an enterprise-grade AI agent system built for the AI Agent track. It parses complex, high-stakes documents (administrative, legal, medical), extracts structured meaning graphs, persists them in Neo4j, simplifies/adapts them to different audience profiles, and audits the results for semantic drift using a Neo4j graph-based verifier.

---

## Key Features

1. **Structured Meaning Graphs**: Extracts claims, obligations, rights, conditions, actions, deadlines, and gaps as typed nodes and relationships in Neo4j.
2. **Dynamic Adaptation Strategy**: Selects vocabulary complexity, information density, tone, structure format, and safety filters as a function of `(Domain x Audience)`.
3. **Local Hybrid Grounding**: Combines local dense search (`BAAI/bge-small-en-v1.5`) and sparse search (`BM25`) over a curated local glossary to define technical jargon.
4. **Outbound Privacy Redactor**: Automatically redacts PII before making external search lookups.
5. **Speech Interface**: Features Whisper CPU Speech-to-Text and Edge-TTS voice generation.
6. **Execution Audit Checkpoints**: Emits structured JSON lines and formatted Markdown files for debugging.
7. **Interactive Visual Sandbox**: Displays a dynamic, drag-and-drop node graph matching the Neo4j database structure.

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **LLM Routing**: Primary Google Gemini (`gemini-2.5-flash`), Fallback Groq (`llama-3.3-70b-versatile`)
- **Database**: Neo4j Community (Docker)
- **Local Retriever**: BGE embeddings (SentenceTransformers) + BM25 (`rank_bm25`)
- **Speech**: Whisper (`faster-whisper`), TTS (`edge-tts`)
- **Frontend**: React (Vite), HTML5 Semantic elements, Vanilla CSS (Modern glassmorphic dark mode, custom interactive SVG physics network graph)

---

## Quick Start (Docker Compose)

### 1. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill in the required keys:
- **`GEMINI_API_KEY`**: Obtain a generous free-tier API key at [Google AI Studio](https://aistudio.google.com/).
- **`GROQ_API_KEY`**: (Optional fallback) Obtain an API key at [Groq Console](https://console.groq.com/).
- **`TAVILY_API_KEY`**: (Optional web lookup) Obtain a free key at [Tavily AI](https://tavily.com/).
- **`NEO4J_PASSWORD`**: Set a password (e.g. `meridian_secure_pass_123`).

### 2. Run Container Build
Start the entire stack with one command:
```bash
docker compose up --build
```
This builds and boots:
- **Neo4j** at `bolt://localhost:7687` (HTTP console: `http://localhost:7474`)
- **FastAPI Backend** at `http://localhost:8000`
- **React Frontend** at `http://localhost:3000`

---

## Local Development (Native Python & Node)

If you do not want to use Docker locally, you can run the services natively:

### 1. Backend Server Setup
From the `backend` folder:
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
python -m uvicorn app.main:app --port 8000 --reload
```

### 2. Frontend App Setup
From the `frontend` folder:
```bash
# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
Open [http://localhost:3000/](http://localhost:3000/) in your browser.

---

## Production Deployment

Project Meridian is configured to easily deploy to low-resource hosted environments:

### 1. Frontend (Vercel / Netlify)
The frontend is a static React Single Page Application (SPA).
*   **Vercel**: Deploy the `frontend/` subdirectory directly. Configured via [vercel.json](file:///d:/copilot/frontend/vercel.json) to handle SPA routing redirects.
*   **Netlify**: Deploy `frontend/` directly. Configured via [netlify.toml](file:///d:/copilot/frontend/netlify.toml) and [_redirects](file:///d:/copilot/frontend/public/_redirects).
*   **Environment Variables**: Set `VITE_API_URL` to your deployed backend URL.

### 2. Backend (Render / Docker Web Service)
The backend FastAPI application can be deployed as a Docker Web Service on Render:
*   **Render Web Service**: Link your GitHub repository. Point it to the `backend/` directory and use the [Dockerfile](file:///d:/copilot/backend/Dockerfile).
*   **Resource Constraints**: Render's free tier has a strict ~512MB RAM cap. We handle this dynamically by setting `DISABLE_LOCAL_MODELS=true` in Render's environment variables. This disables local Whisper and BGE model loading to conserve RAM, switching to mock fallbacks.
*   **Logs**: Checkpoints pipe directly to `stdout` for Render's log aggregator.

### 3. Graph Database (Neo4j AuraDB Free)
*   Provision a managed Neo4j instance on **Neo4j AuraDB**.
*   Update `NEO4J_URI` to `neo4j+s://<subdomain>.databases.neo4j.io` and configure your credentials. If AuraDB is offline, the backend gracefully degrades and continues processing adaptations.

---

## API Documentation

### `POST /api/v1/adapt`
Executes the full pipeline for adaptation.

#### Example Request:
```bash
curl -X POST "http://localhost:8000/api/v1/adapt" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "Pursuant to City Municipal Ordinance § 402.19, residents must grant safety access on August 15, 2026. Failure results in a fine of $150.00.",
       "audience_profile": {
         "role": "patient",
         "domain_familiarity": "novice",
         "cognitive_access_needs": "anxiety_aware",
         "preferred_language": "en",
         "modality": "text"
       },
       "options": {
         "generate_multiple_profiles": false,
         "include_fidelity_note": true,
         "enable_external_lookup": false,
         "tts_output": false
       }
     }'
```

#### Example Response:
```json
{
  "run_id": "run_a2b3c4d5",
  "domain": "legal",
  "document_type": "policy",
  "risk_level": "critical",
  "versions": [
    {
      "profile": "patient",
      "adapted_content": "We need to check safety features on August 15, 2026. This is standard safety check. Please let us in...",
      "strategy_summary": "Vocab=simple, Structure=qa, Tone=reassuring",
      "gaps": ["No contact person listed for scheduling changes"],
      "fidelity_note": "Fidelity check: 100% coverage. compliance verified.",
      "audio_url": ""
    }
  ],
  "content_understanding": {
    "domain": "legal",
    "risk_level": "critical"
  },
  "meaning_summary": {
    "node_count": 3,
    "relationship_count": 2
  },
  "graph_run_node_id": "run_a2b3c4d5"
}
```

---

## Log Locations & Checkpoint Format

Logs are stored in the mounted `./logs` directory:
1. **JSONL Format (`logs/agent_run_{run_id}.jsonl`)**: Raw JSON lines documenting pipeline metrics, token/time parameters, and error descriptions.
2. **Markdown Format (`logs/agent_run_{run_id}.md`)**: Beautiful, human-readable tables mapping pipeline status and input/output descriptions.

### Example Markdown Table Log:
| Timestamp | Stage | Status | Duration (ms) | Model/Provider | Details |
| --- | --- | --- | --- | --- | --- |
| 2026-07-30T10:45:00Z | `RUN_STARTED` | INFO | - | - | Pipeline initiated. |
| 2026-07-30T10:45:01Z | `CONTENT_UNDERSTANDING_STARTED` | **STARTED** | - | - | Input truncated... |
| 2026-07-30T10:45:03Z | `CONTENT_UNDERSTANDING_COMPLETED` | **COMPLETED** | 2120 | gemini | Domain: legal, Risk: critical |
| 2026-07-30T10:45:04Z | `MEANING_EXTRACTION_COMPLETED` | **COMPLETED** | 3120 | gemini | Extracted 4 nodes, 3 links |

---

## Directory Structure

```
project-meridian/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/
│       │   ├── routes.py
│       │   └── schemas.py
│       ├── agents/
│       │   ├── orchestrator.py
│       │   ├── content_understanding.py
│       │   ├── meaning_extractor.py
│       │   ├── strategy_engine.py
│       │   ├── rewriter.py
│       │   └── verifier.py
│       ├── llm/
│       │   ├── router.py
│       │   ├── gemini_client.py
│       │   └── groq_client.py
│       ├── graph/
│       │   ├── neo4j_client.py
│       │   └── schema.py
│       ├── retrieval/
│       │   ├── embeddings.py
│       │   ├── bm25_index.py
│       │   ├── hybrid_search.py
│       │   └── tavily_client.py
│       └── utils/
│           ├── redaction.py
│           └── checkpoints.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── App.jsx
        ├── index.css
        └── main.jsx
```
