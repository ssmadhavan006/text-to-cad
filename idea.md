Recommended architecture
┌─────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  User Input  │────▶│ Feasibility/Intent │────▶│  Code Generation    │
│ text (+image)│     │   Gate (Step 2)    │     │  LLM (CadQuery/     │
└─────────────┘     └──────────────────┘     │  build123d script)  │
                                               └─────────┬──────────┘
                                                          │
                                               ┌─────────▼──────────┐
                                               │ Execution Kernel    │
                                               │ (OpenCASCADE via    │
                                               │ CadQuery/FreeCAD)   │
                                               └─────────┬──────────┘
                                          error ┌────────┴────────┐ valid
                                     ┌──────────▼───┐      ┌──────▼──────┐
                                     │ Self-Correction│      │  STEP/STL   │
                                     │ Loop (LLM rewrite)│  │  export     │
                                     └──────────┬───────┘      └──────┬──────┘
                                                │ retry (max N)        │
                                                └──────────────────────▼
                                                                ┌──────────────┐
                                                                │ 3D Viewer (web)│
                                                                └──────────────┘
Mapped to the workflow your seniors gave you:

User prompt → captured in a chat-style frontend.
Feasibility filter (your step 2) — this is the part most tutorials skip, and it's your differentiator. Two sub-layers:

Syntactic/semantic gate: a small, fast LLM (or even rule-based parser + a lightweight intent classifier) extracts structured parameters (shape type, dimensions, units, feature list — e.g., "gear, 12 teeth, module 2mm, bore 10mm") into a JSON schema. Reject/clarify if required fields are missing or contradictory (e.g., bore diameter > outer diameter).
Physical/geometric plausibility check: simple engineering rules before any expensive generation — wall thickness vs. material, hole diameter vs. part size, gear tooth count vs. module/pitch diameter relationship, draft angles, etc. This can literally be a Python rules engine + unit-aware parsing (use pint for units). This is cheap, deterministic, fast, and is a great live-demo moment ("watch it catch an impossible gear before wasting a generation cycle").


Main engine — LLM generates CadQuery/build123d code conditioned on the structured parameters (not raw free text — much more reliable). Chain-of-thought: have the model first write out the construction plan (sketch → extrude/revolve → fillet → pattern) as intermediate reasoning, then emit code. This is what the "12-teeth gear" CoT example you found refers to.
Execution kernel: run the generated script in a sandboxed subprocess against CadQuery (which wraps OpenCASCADE / OCP). CadQuery and FreeCAD are both wrappers around OpenCascade, a powerful, B-rep-based geometric modeling kernel, and both can run as stand-alone, GUI-less Python scripts for parametric CAD generation — this is what gives you real curved surfaces (fillets, revolves, lofts) instead of GNN-approximated meshes. Mit
Self-correction loop: if execution throws (syntax error, invalid Boolean op, self-intersecting geometry, non-manifold result), capture the exact traceback/error and feed it back to the LLM with the original prompt + previous code, ask for a corrected version. Cap at ~3 retries, then fail gracefully to the user with a clear message rather than silently looping. This is the single most important reliability feature to demo — it's the difference between "73% success rate naive" and "97%+ success rate with self-correction" and it's a very visual, convincing demo moment (show a failure, show the error, show the auto-fix).
Viewer: export STEP (parametric, for engineering use downstream) and a lightweight mesh (GLTF/STL→glTF) for fast in-browser rendering with three.js. Show the generated code alongside the model so it's editable/auditable (this matters a lot to an engineering-software company — opacity is their fear about generative AI in CAD).

4. Stack recommendation (tuned to your hardware)
Your RTX 5070 desktop has 12GB VRAM — that's the binding constraint, and it rules out running large 70B-class models locally at decent quantization, but it's plenty for a fine-tuned 7B–14B coder model in 4-bit/8-bit, which is genuinely all you need here (CAD-Coder's own ablations show fine-tuned 7–13B models beating 72B general VLMs on this narrow task — specialization beats scale for this problem).
Language/code-gen model:

Primary: Fine-tune Qwen2.5-Coder-7B-Instruct (or 14B if you can tolerate slower inference, but 7B at 4-bit fits comfortably in 12GB with room for KV cache) on CadQuery generation. This matches what the CAD-Coder text-to-CAD line of work itself uses — Guan et al. reformulated text-to-CAD as generating CadQuery code from natural language, using supervised fine-tuning followed by reinforcement learning with CAD-specific reward functions, on a Qwen2.5-7B-Instruct base. You're not inventing a new method, you're replicating a validated recipe — good for a proposal, since you can cite precedent. ACM Digital Library
Inference: vLLM if you want throughput/concurrent demo users, or Ollama for simplicity during dev. For a single-user MVP demo, Ollama is genuinely fine and much less ops overhead.
Multimodal extension (Phase 2): CAD-Coder's LLaVA-based approach for "photo + text" input is a good Phase 2 differentiator, but don't put it in the MVP — it roughly doubles your engineering surface (vision encoder, alignment training, more data prep) for a feature that isn't your core ask.

Geometry kernel / scripting layer:

build123d over raw CadQuery for new code — it's the actively-developed successor with a cleaner, more Pythonic builder API and better support for complex sweeps/lofts, but both sit on OpenCASCADE, so either is fine for the kernel; CadQuery has more existing fine-tuning data/papers to draw on (GenCAD-Code, ExeCAD), so practically: train/fine-tune the LLM on CadQuery (data availability wins), keep build123d as a documented future migration path.
Sandbox script execution in a subprocess with a timeout and resource limits (don't exec() LLM-generated code in-process — treat it like any other LLM-generated code: untrusted).

RAG / retrieval layer:

Vector DB (Qdrant or ChromaDB — both run trivially on your machine) indexing: Text2CAD's ~170K models and ~660K text annotations, Fusion 360 Gallery design histories, and the ABC dataset's B-rep primitives, embedded as (description → code-snippet) pairs. This gives the model retrieved few-shot exemplars for the specific feature family in the prompt (gear, bracket, flange, enclosure) before it generates — meaningfully improves reliability without needing more fine-tuning compute, and it's cheap to extend per-customer later (this is your answer to Leo's "trains on customer's own design rules" pitch — you can say the same thing, openly). ADS

Feasibility filter:

A lightweight structured-extraction call (same small LLM, low temperature, JSON-mode output) + a deterministic Python rules engine (pint for units, basic geometric/mechanical constraint checks). No ML needed here — keep it fast and explainable.

Backend: FastAPI (Python-native, pairs naturally with CadQuery/build123d/OCP, easy WebSocket support for streaming generation progress and viewer updates).
Frontend: React + three.js (or @react-three/fiber) for the 3D viewer, loading glTF/STL exports; show the generated code in a side panel (Monaco editor component) so users can see/tweak it — this "editable, transparent" angle is something to lean on hard in the pitch.
Storage: Postgres for prompt/job/version history (this also lets you demo "design history" / iteration tracking, which echoes Fusion 360 Gallery's sequential design history framing — another thing to namecheck since it shows you understand how real CAD tools think about parametric history, not just final shape).
5. Datasets — how to actually use them (not just list them)

Text2CAD dataset: ~150k training CAD sequences with four design prompts ranging from abstract to expert levels (L0–L3) per sample, ~600k training samples total. Use this for the bulk of your SFT — but you need to convert its sketch-and-extrude sequence format into executable CadQuery, since it's natively in DeepCAD's command format, not CadQuery. CAD-Coder's GenCAD-Code dataset already did this conversion for you, so practically: use GenCAD-Code (163k pairs, already in CadQuery) as your primary SFT set, and treat raw Text2CAD as a secondary source/prompt-diversity augmenter (its multi-level prompt structure — beginner to expert phrasing — is great for making your model robust to how a real mechanical engineer vs. a novice would phrase the same gear request). arxiv
ABC Dataset: best used for RAG corpus / geometric primitive retrieval and B-rep validity checks, not full fine-tuning — it's huge and lacks paired natural language, so you'd need to auto-caption it (expensive) to be SFT-useful directly.
Fusion 360 Gallery: best for Phase 2 "design history" / multi-step editing features (sketch→extrude→fillet sequences) and as inspiration for your feasibility-gate's mechanical sanity rules.

6. Phased plan (MVP-first, as you asked)
Phase 0 (2–3 weeks) — Pipeline skeleton, no fine-tuning yet

Wire the full loop end-to-end using a strong general coder model via API (Claude or GPT-4-class, or Qwen2.5-Coder-7B zero-shot) prompted with good few-shot CadQuery examples. Goal: prove the architecture (gate → generate → execute → self-correct → render) works mechanically, before spending GPU time on fine-tuning. This is also your fallback demo if fine-tuning runs late.
Phase 1 (MVP, demo-ready, 4–6 weeks) — Fine-tuned model + self-correction + feasibility gate

Fine-tune Qwen2.5-Coder-7B (QLoRA, 4-bit, fits your 12GB card) on GenCAD-Code + a curated slice of Text2CAD prompts.
Implement the feasibility gate with a focused, demoable rule set (gears, brackets, flanges, simple enclosures — pick a narrow "supported feature catalog" rather than claiming generality you can't back).
Self-correction loop with visible retry trace in the UI.
Web viewer with code-panel + STEP/STL export.
Demo script: show 3 tiers live — (a) simple primitive (cuboid with a hole) succeeds first try, (b) a parametric mechanical part (12-tooth gear) shows the CoT reasoning step, (c) an intentionally bad prompt (impossible dimensions) gets caught by the feasibility gate, and (d) a prompt that initially fails execution gets auto-corrected on screen. That four-beat demo tells the whole story in under 5 minutes.

Phase 2 (post-MVP, what you propose as "next phase" in the doc, not building now)

Multimodal input (CAD-Coder-style image+text) for bracket-photo-style prompts.
Per-customer RAG fine-tuning on private part libraries (your answer to Leo's "customer-specific design rules").
Design-history/iterative editing ("now add 4 mounting holes to that bracket") instead of one-shot generation.
RL fine-tuning (GRPO + Chamfer-distance reward) once you have enough generated/validated samples to build a reward signal — this is the most compute/complexity-heavy item, correctly deferred.

Phase 3 (the actual pitch to Dassault as an "internal project")

Integration path into 3DEXPERIENCE/SOLIDWORKS as a plug-in or API-callable service rather than a standalone app — this is the part that turns this from "cool student project" into "thing we could actually adopt," and you should write a short section proposing exactly how it'd sit alongside Leo (e.g., as an internal R&D sandbox for evaluating explainable/auditable generation before any customer-facing rollout, or as the engine behind a "power-user API" for batch/parametric generation that a chat companion UI isn't suited for).