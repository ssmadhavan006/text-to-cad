# Progress Log

## Current State
- ✅ High-fidelity GLB mesh preview exports with smooth shading (STEP math remains exact).
- ✅ Proposal-grade benchmark harness compiles and measures latencies/retries across 10 verified cases (100% success rate).
- ✅ Stateful multi-turn iterative editing (chained modifications) fully integrated and verified via integration test suite.
- ✅ Dynamic ChromaDB vector store few-shot retrieval (RAG) generalizes CAD primitives and operations.
- ✅ React web dashboard and FastAPI backend session context operational.

## Log

### [2026-06-25 21:45] Phase 4: Latency Diagnosis Completed
**What changed:**
- **Goal 1 (GPU Inference Diagnosis)**: Confirmed that Ollama `0.30.10` fails GPU bootstrap discovery on NVIDIA GeForce RTX 5070 (Blackwell architecture, Compute Capability 12.0) with exit code 1. Discovered that the installation was missing critical libraries `cublasLt64_12.dll` and `cudart64_12.dll` (had a corrupted `.tmp` file in the installer folder). Found and copied working versions of these DLLs from a PyTorch virtual environment to the Ollama directory, which resolved the DLL loading errors, but Ollama's discovery subprocess still exits with 1, confirming that this Ollama version does not support the Blackwell architecture or CUDA 13.2 driver configuration.
- **Goal 2 (Subprocess/Import Overhead)**: Measured `import cadquery` in isolation using `Measure-Command` and confirmed it takes **1.45 seconds**, which accounts for 100% of the Sandbox Execution stage latency (1.43s p50). Every script execution currently pays this 1.45s startup tax.
- **Goal 3 (Segmented Benchmark Data)**: Analyzed existing `benchmark_results.md` data:
  - Median total latency is 48.19s, p95 is 133.34s.
  - Per-stage median: Intent Extraction: 4.58s, RAG Retrieval: 2.12s, Code Generation: 40.74s, Sandbox Execution: 1.43s.
  - First-attempt success cases (80%): Median is 43.70s, p95 is 58.55s.
  - Chained/Retry cases (20%): Median is 115.08s (requires 2 attempts, doubling the generation cost).
  - Code generation clearly dominates total latency, owing to CPU-bound model execution.
**Why:** To establish a clear performance baseline and identify actionable optimization avenues before implementing fixes and UI stream handling.
**Files touched:**
- [progress.md](file:///d:/Coding/text-to-cad/progress.md)
**Verification:** Verified DLL loading via Win32 ctypes python script, timed CadQuery import, and computed statistical segmentations.
**Status:** ✅ diagnosis completed

### [2026-06-25 20:15] Completed Phase 3: Visual Fidelity, Benchmarking, and Iterative Editing
**What changed:** 
- **Goal 1 (Visual Fidelity)**: Upgraded preview mesh pipeline to export size-aware glTF binary (`.glb`) files utilizing deflection tolerances (`tolerance = max(1e-4, min(0.5, diag * 0.0015))` and `angularTolerance = 0.05`). Modified `StlViewer.jsx` to load GLB meshes via `GLTFLoader` and dynamically assign theme-aware `MeshStandardMaterial` parameters (cool blue for Light Mode, aluminum for Dark Mode) with smooth vertex normals.
- **Goal 2 (Benchmarking)**: Instrument backend with sub-step latency tracking. Built `benchmarking/run_benchmarks.py` harness which executed the 10 verified test cases, aggregating p50/p95 latency and retry profiles into `benchmark_results.md` showing a 100% final success rate.
- **Goal 3 (Iterative Editing)**: Extended `intent_extractor.py` system prompt to classify `is_modification` intent and parameters. Upgraded `code_generator.py` to route to a specialized `SYSTEM_PROMPT_MODIFICATION_TEMPLATE` when a previous script and parameters are provided. Integrated stateful in-memory session context and parameter merging in `main.py`. Added active context UI and a "Reset Session" button in `App.jsx`. Added comprehensive test suite `tests/test_iterative_editing.py` validating 3-turn bracket and 2-turn gear modification chains.
**Why:** To resolve visual faceting bugs, generate official Dassault-proposal statistics, and implement stateful multi-turn editing features.
**Files touched:**
- [backend/app/executor.py](file:///d:/Coding/text-to-cad/backend/app/executor.py)
- [backend/app/schemas.py](file:///d:/Coding/text-to-cad/backend/app/schemas.py)
- [backend/app/main.py](file:///d:/Coding/text-to-cad/backend/app/main.py)
- [backend/app/intent_extractor.py](file:///d:/Coding/text-to-cad/backend/app/intent_extractor.py)
- [backend/app/code_generator.py](file:///d:/Coding/text-to-cad/backend/app/code_generator.py)
- [frontend/src/components/StlViewer.jsx](file:///d:/Coding/text-to-cad/frontend/src/components/StlViewer.jsx)
- [frontend/src/App.jsx](file:///d:/Coding/text-to-cad/frontend/src/App.jsx)
- [benchmarking/run_benchmarks.py](file:///d:/Coding/text-to-cad/benchmarking/run_benchmarks.py)
- [benchmark_results.md](file:///d:/Coding/text-to-cad/benchmark_results.md)
- [tests/test_iterative_editing.py](file:///d:/Coding/text-to-cad/tests/test_iterative_editing.py)
- [architecture.md](file:///d:/Coding/text-to-cad/architecture.md)
- [progress.md](file:///d:/Coding/text-to-cad/progress.md)
**Verification:** Ran `pytest tests/test_iterative_editing.py` (all tests passed) and executed `run_benchmarks.py` (successfully compiled and generated `benchmark_results.md`).
**Status:** ✅ working
**Next step:** Completed Phase 3. Ready for final user hand-off.

### [2026-06-25 15:40] Completed dynamic vector store and verified 6 generalization cases
**What changed:** Re-indexed ChromaDB database after correcting standard CadQuery methods in `few_shot_examples.json` (specifically fixing `Workplane.cone` to `cq.Solid.makeCone` and corrected `polarArray` arguments). Loosened bracket check in `feasibility_gate.py` to allow deducing length/width from radial properties for circular/polygonal shapes and mapped `pattern_radius` to `hole_offset`. Added 6 generalization cases in `tests/test_generalization.py` and confirmed they all passed successfully.
**Why:** To transition the few-shot template library to a fully dynamic, self-correcting RAG architecture that successfully generalizes primitives and operations under verification rules.
**Files touched:**
- [few_shot_examples.json](file:///d:/Coding/text-to-cad/data/few_shot_examples.json)
- [vector_store.py](file:///d:/Coding/text-to-cad/backend/app/vector_store.py)
- [feasibility_gate.py](file:///d:/Coding/text-to-cad/backend/app/feasibility_gate.py)
- [test_generalization.py](file:///d:/Coding/text-to-cad/tests/test_generalization.py)
- [architecture.md](file:///d:/Coding/text-to-cad/architecture.md)
- [progress.md](file:///d:/Coding/text-to-cad/progress.md)
**Verification:** All 6 generalization test cases passed in a single test suite execution with 100% success.
**Status:** ✅ working
**Next step:** Implement frontend visibility dark/light mode toggle.

### [2026-06-25 15:05] Corrected documentation and established Phase 2 verification rules
**What changed:** Re-classified features in `architecture.md` to distinguish between "Scaffolded" (has worked example, compiles, but held-out parameters are untested) and "Planned" (untested/no example). Added Rule 4.7 to `rules.md` requiring structurally distinct tests for verified status.
**Why:** To ensure clear, honest documentation and prevent claiming untested features are fully supported.
**Files touched:**
- [architecture.md](file:///d:/Coding/text-to-cad/architecture.md)
- [rules.md](file:///d:/Coding/text-to-cad/rules.md)
- [progress.md](file:///d:/Coding/text-to-cad/progress.md)
**Verification:** Reviewed files on disk.
**Status:** ⚠️ partially working (documentation corrected, verification pending Phase 2 code)
**Next step:** Install ChromaDB and build the dynamic example vector store.

### [2026-06-25 14:32] Completed React frontend dashboard and integrated full MVP
**What changed:** Built the React frontend dashboard using Vite, `@react-three/fiber` (Three.js), and `@monaco-editor/react`. Integrated the frontend UI with the FastAPI backend. Adjusted API timeouts to allow local Ollama runs to complete without client timeouts.
**Why:** To provide an interactive, premium user experience allowing designers to prompt, validate, compile, view, and download CAD models.
**Files touched:**
- [frontend/src/App.jsx](file:///d:/Coding/text-to-cad/frontend/src/App.jsx)
- [frontend/src/components/StlViewer.jsx](file:///d:/Coding/text-to-cad/frontend/src/components/StlViewer.jsx)
- [frontend/src/index.css](file:///d:/Coding/text-to-cad/frontend/src/index.css)
- [backend/app/code_generator.py](file:///d:/Coding/text-to-cad/backend/app/code_generator.py)
- [tests/demo_runs.py](file:///d:/Coding/text-to-cad/tests/demo_runs.py)
- [progress.md](file:///d:/Coding/text-to-cad/progress.md)
**Verification:** Ran `uv run --env-file .env python tests/demo_runs.py` which compiled a box, spur gear, bracket, and tested feasibility rejection. All demo runs passed successfully. Tested Vite server and confirmed it loads.
**Status:** ✅ working
**Next step:** Present the complete solution to the user.

### [2026-06-25 14:15] Completed CadQuery sanity check and environment configuration
**What changed:** Verified that CadQuery and OpenCASCADE successfully run under `uv` by exporting a 3D box to STL and STEP. Created `.gitignore`, `.env`, and `.env.example`.
**Why:** To ensure the core geometry engine works before building the app logic.
**Files touched:**
- [tests/sanity_check.py](file:///d:/Coding/text-to-cad/tests/sanity_check.py)
- [.gitignore](file:///d:/Coding/text-to-cad/.gitignore)
- [.env](file:///d:/Coding/text-to-cad/.env)
- [.env.example](file:///d:/Coding/text-to-cad/.env.example)
- [progress.md](file:///d:/Coding/text-to-cad/progress.md)
**Verification:** Subprocess executed `uv run python tests/sanity_check.py` successfully and verified that `tests/output/sanity_box.step` and `tests/output/sanity_box.stl` were generated.
**Status:** ✅ working
**Next step:** Design the backend data models and implement Phase C: Feasibility gate.

### [2026-06-25 14:13] Initialized project and created living documents
**What changed:** Ran `uv init` and created the three living documents: `progress.md`, `rules.md`, and `architecture.md`.
**Why:** To establish the repository workspace, set up project scaffolding, and define tracking, rules, and system architecture.
**Files touched:**
- [pyproject.toml](file:///d:/Coding/text-to-cad/pyproject.toml)
- [progress.md](file:///d:/Coding/text-to-cad/progress.md)
- [rules.md](file:///d:/Coding/text-to-cad/rules.md)
- [architecture.md](file:///d:/Coding/text-to-cad/architecture.md)
**Verification:** Confirmed file creation on disk and successful execution of `uv init`.
**Status:** ✅ working
**Next step:** Create the folder structure and add dependencies.
