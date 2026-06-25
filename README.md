# Text-to-CAD Engine

An AI-powered 3D CAD parameter extraction and generation pipeline. It converts natural language prompts (e.g. *"design a spur gear with 12 teeth, module 2mm"*) into mathematically exact, physical **STEP** models for CNC/machining, alongside smoothed binary **GLB/glTF** meshes for interactive 3D browser previewing.

---

## 🚀 Key Features

* **GPU-Accelerated Inference**: Fully offloaded to local GPU acceleration (NVIDIA GeForce RTX 5070 Blackwell architecture), dropping code generation times from ~40s to **under 6 seconds**.
* **Pre-Warmed Sandbox Execution**: Implements a persistent, isolated IPC worker pool (`worker.py`) that pre-warms the CadQuery/OpenCASCADE import tax, reducing execution latency from 1.45s to **0.02s**.
* **Real-time SSE Streaming**: Exposes a Server-Sent Events (SSE) endpoint to stream generation stages, Chain-of-Thought (CoT) reasoning, and python code tokens directly to the frontend console.
* **Stateful Multi-Turn Editing**: Keeps active in-memory session parameters, merging and validation modifications (e.g. *"now add 4 mounting holes"*) sequentially.
* **Deterministic Feasibility Gate**: Employs mathematical unit validation rules (via `Pint`) to immediately reject physically impossible bounds before calling LLM layers.
* **Dynamic Few-Shot RAG**: Uses ChromaDB and Ollama embedding collections (`nomic-embed-text`) to dynamically search and retrieve the most relevant geometric example cases for prompts.

---

## 🛠️ Technology Stack

* **Backend**: FastAPI, CadQuery (OpenCASCADE kernel), ChromaDB, Ollama, PyTest, Uvicorn, Pint
* **Frontend**: React, Vite, Three.js (React Three Fiber), Monaco Editor, Tailwind CSS / Vanilla CSS

---

## 📂 Project Structure

```
text-to-cad/
├── backend/
│   ├── app/
│   │   ├── code_generator.py      # LLM code drafting (qwen2.5-coder:7b)
│   │   ├── config.py              # Environment settings loading
│   │   ├── executor.py            # Sandbox executor and worker manager
│   │   ├── feasibility_gate.py    # Deterministic geometry bounds checks
│   │   ├── intent_extractor.py    # Request classification (qwen2.5-coder:1.5b)
│   │   ├── main.py                # FastAPI main routes (SSE / static serving)
│   │   ├── schemas.py             # Typed Pydantic data schemas
│   │   ├── vector_store.py        # ChromaDB dynamic few-shot RAG
│   │   └── worker.py              # Long-lived pre-warmed CAD worker
│   └── data/
│       └── few_shot_examples.json # Geometry corpus of worked examples
├── frontend/                      # React frontend workspace (Vite)
├── benchmarking/                  # Latency and retry benchmark harness
├── tests/                         # Integration and unit test suite
├── pyproject.toml                 # UV python package constraints
└── architecture.md                # System data flows and verified features
```

---

## 📦 Getting Started

### 1. Prerequisites
Ensure you have the following installed:
* **Python 3.12** (managed via `uv`)
* **Node.js** (for frontend)
* **Ollama** (locally serving `qwen2.5-coder:7b`, `qwen2.5-coder:1.5b`, and `nomic-embed-text:latest`)
* **NVIDIA GPU Drivers & CUDA Toolkit**

### 2. Backend Setup
1. Clone the repository and configure environment variables in `.env`:
   ```bash
   cp .env.example .env
   ```
2. Start the local Ollama daemon:
   ```bash
   ollama serve
   ```
3. Boot the FastAPI server (it will automatically build and hydrate the vector store):
   ```bash
   $env:PYTHONPATH="backend"
   uv run python backend/app/main.py
   ```
   The backend will be listening on [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```
2. Run the Vite development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧪 Verification & Testing

To run the full suite of unit and integration tests (feasibility gate, RAG vector store, generalization cases, iterative editing chains):
```bash
$env:PYTHONPATH="backend"
uv run pytest
```
To run the automated benchmark metrics compilation:
```bash
uv run python benchmarking/run_benchmarks.py
```
Outputs and aggregates latency metrics inside [benchmark_results.md](file:///d:/Coding/text-to-cad/benchmark_results.md).
