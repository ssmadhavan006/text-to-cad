# Rules and Constraints

These rules are seed constraints from the project specification, plus local additions.

### 4.1 Terminal execution policy (strict)
- **Short, fast, safe commands** (install a package, run a unit test file, run a linter, run a script that completes in well under ~60 seconds, check a file, run a quick syntax/import check): run these yourself and read the output.
- **Long-running, expensive, or environment-risky commands** — anything involving model fine-tuning, downloading large model weights/datasets, any GPU training loop, batch dataset preprocessing over the full corpus, anything you estimate could take more than ~1-2 minutes, or anything that could materially change global system/environment state in a way that's hard to undo — you must **NOT** run these yourself. Instead:
  1. Stop.
  2. Print the **exact command** to run, in a fenced code block, with no placeholders.
  3. Briefly state what it does, what success looks like, what files/output it should produce, and roughly how long you expect it to take.
  4. Explicitly ask the user to run it manually and paste back the output/logs.
  5. Do not proceed past that point in the plan until the user provides the output.
- When unsure whether something qualifies as "long-running," default to asking rather than running. Asking costs a few seconds; an unsupervised multi-minute job that silently fails or eats resources costs much more.
- Never run anything that fine-tunes a model, modifies system-wide config, or installs system packages (`apt`, global `pip`, etc.) without explicit user confirmation first, regardless of expected runtime.

### 4.2 Package management
- Use **uv** exclusively. Never invoke `pip install`, `python -m venv`, or `conda` directly.
- Initialize the project with `uv init`. Add dependencies with `uv add <package>` (and `uv add --dev <package>` for dev/test tooling). Run anything with `uv run <command>`.
- Keep `pyproject.toml` and the committed `uv.lock` as the single source of truth for dependencies — never hand-edit version pins inconsistently with what `uv add` produces.
- If a dependency needs to be removed, use `uv remove`, don't just delete the line from `pyproject.toml`.

### 4.3 Anti-hallucination / anti-fabrication rules
- Never claim a feature works, a test passes, or a benchmark number is real unless you actually ran it in this session and observed the output. If you're estimating or haven't verified, say so explicitly ("untested," "expected behavior, not yet confirmed").
- Never invent CadQuery/build123d/OpenCASCADE API methods you're not certain exist. If unsure, check the installed package's actual source/docstrings (`uv run python -c "import cadquery; help(cadquery.Workplane.fillet)"` or equivalent) rather than guessing from memory or pattern-matching to similar libraries.
- Never silently catch and swallow an exception to make a demo "look like it works." If execution fails, that failure must surface through the self-correction loop or, after exhausting retries, to the user — never hidden.
- Do not fabricate or hardcode a "successful" geometry result behind the scenes to make a hard case pass. If the system can't actually generate a valid part for a given prompt, it must say so.
- When writing progress.md entries, the "Verification" field must describe something you actually observed, with enough specificity that someone could repeat it.

### 4.4 Code quality / engineering practices
- Type hints on all function signatures; `pydantic` models for any data crossing module boundaries (LLM output, feasibility gate input/output, execution results).
- Every module that can fail (LLM call, code execution, kernel ops) must have explicit, typed error handling — no bare `except:`.
- Write tests as you go, not at the end. At minimum: unit tests for the feasibility gate's rules (including known-bad inputs that must be rejected), and integration tests for at least one end-to-end happy path per supported feature type (Section 1).
- Sandbox all LLM-generated code execution: run it in a subprocess with a hard timeout and restricted resources. Treat generated code as untrusted input, always — never `exec()` it in-process.
- Small, frequent commits with descriptive messages. Don't batch unrelated changes into one commit.
- No secrets, API keys, or credentials committed to the repo, ever — use `.env` + `.gitignore`.
- Prefer explicit, readable code over clever abstractions, especially in the feasibility gate where correctness and auditability matter more than elegance.
- Keep the LLM-calling code behind a thin interface (e.g. `generate_code(prompt, context) -> str`) so the underlying model/serving approach can be swapped later without touching the pipeline logic.

### 4.5 Communication discipline
- Before starting a new phase or any structurally significant change, briefly state your plan and proceed — don't ask permission for routine implementation decisions within the agreed scope.
- Do ask before: changing the tech stack choices in Section 2, expanding the feature catalog in Section 1, adding new heavyweight infrastructure (databases, containers, services) not already listed, or running anything covered by the long-running-command policy in 4.1.

### 4.6 Local CadQuery Rules & Footguns
- **Dynamic Allowlist Generation**: Any API validation allowlist (like `cad_api_allowlist.json`) must be dynamically generated via introspection scripts (like `generate_allowlist.py`) using python's `inspect` module, rather than manually authored. This ensures consistency and makes it easy to update validation rules when the underlying library is upgraded.
- **AST Validator Coverage**: When calling `.workplane()` on CadQuery objects, do not pass arguments like `centered`, `centerX`, or `centerY`, as they are not accepted by `cq.Workplane.workplane()`. The static AST validator will reject them before execution.

### 4.7 Feature Verification Policy
- A feature may only be marked "Verified" in `architecture.md` after it has a passing test using a prompt structurally distinct from any worked example in the corpus — not merely a parameter variation of one. Marking something supported based on a single hand-matched demo case is exactly the kind of unverified claim this project must avoid.

