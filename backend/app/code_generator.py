import logging
import httpx
import re
import json
import time
from typing import Dict, Any, List, Optional
from app.config import settings
from app.vector_store import retrieve_examples

logger = logging.getLogger(__name__)

# Global latency state for benchmarking instrumentation
last_retrieval_latency = 0.0
last_generation_latency = 0.0

# System prompt template where worked examples are dynamically inserted
SYSTEM_PROMPT_TEMPLATE = """You are an expert mechanical engineer and CAD programmer.
Your task is to generate a parametric CadQuery Python script based on a shape description and normalized parameters.

Follow these strict requirements:
1. The script must import `cadquery` as `cq`.
2. The final CAD shape/object must be assigned to a variable named exactly `result`.
3. Do NOT include any code to save or export the file (the execution system will append this automatically).
4. Use standard, reliable CadQuery methods. Avoid using deprecated or complex topological features.
5. All dimensions are in millimeters (mm) and angles in degrees.
6. Provide a step-by-step Chain of Thought explanation of your geometric modeling strategy before the code block.
7. Wrap the Python code inside a single markdown code block: ```python ... ```.
8. Crucial API rule: The `cq.Workplane.workplane()` method (e.g. `result.faces().workplane()`) does NOT accept arguments like `centered`, `centerX`, `centerY`, `center`, `width`, or `height`. Always call `.workplane()` without these arguments. Any centering or sizing parameters must be passed directly to shape methods (e.g. `.box(..., centered=True)` or `.rect(..., centered=True)`), NOT to `.workplane()`.

Here are some worked examples showing correct CadQuery usage:

{few_shot_examples}

Now, generate the code for the requested shape.
"""

SYSTEM_PROMPT_MODIFICATION_TEMPLATE = """You are an expert mechanical engineer and CAD programmer.
Your task is to modify an existing parametric CadQuery Python script based on a modification request and new parameters.

Follow these strict requirements:
1. The script must import `cadquery` as `cq`.
2. The final CAD shape/object must be assigned to a variable named exactly `result`.
3. Do NOT include any code to save or export the file (the execution system will append this automatically).
4. Use standard, reliable CadQuery methods. Avoid using deprecated or complex topological features.
5. All dimensions are in millimeters (mm) and angles in degrees.
6. Provide a step-by-step Chain of Thought explanation of your geometric modeling strategy before the code block.
7. Wrap the Python code inside a single markdown code block: ```python ... ```.
8. Maintain the structure and parameters of the existing script where possible, adding or modifying operations as requested. Do not discard previous features.
9. Crucial API rule: The `cq.Workplane.workplane()` method (e.g. `result.faces().workplane()`) does NOT accept arguments like `centered`, `centerX`, `centerY`, `center`, `width`, or `height`. Always call `.workplane()` without these arguments. Any centering or sizing parameters must be passed directly to shape methods (e.g. `.box(..., centered=True)` or `.rect(..., centered=True)`), NOT to `.workplane()`.

Here is a worked example showing how to add an operation to a script:
### Existing Script:
```python
import cadquery as cq
length = 40.0
width = 30.0
height = 20.0
result = cq.Workplane("XY").box(length, width, height)
```
### Modification Request: "add a fillet of 2mm to the top edges"
### Response CoT:
1. We want to select the top edges of the box and apply a 2.0 mm fillet.
2. Select the face at the positive Z boundary (`>Z`), select its edges, and call `.fillet(2.0)`.
3. Modify the code to include `fillet_radius = 2.0` and apply it to `result`.

```python
import cadquery as cq
length = 40.0
width = 30.0
height = 20.0
fillet_radius = 2.0

result = cq.Workplane("XY").box(length, width, height)
if fillet_radius > 0:
    result = result.edges(">Z").fillet(fillet_radius)
```

Now, here is a reference example showing correct CadQuery usage for the requested modification operation:
{few_shot_examples}
"""

def format_few_shot_examples(examples: List[Dict[str, Any]]) -> str:
    """
    Formats the list of retrieved examples into a string block for the system prompt.
    """
    if not examples:
        return "# (No reference examples available; write standard CadQuery code)"
        
    formatted = []
    for ex in examples:
        block = (
            f"### Shape: {ex['description']}\n"
            f"Parameters: {json.dumps(ex['parameters'])}\n"
            f"Response:\n"
            f"{ex['cot_explanation']}\n\n"
            f"```python\n"
            f"{ex['code']}\n"
            f"```"
        )
        formatted.append(block)
    return "\n\n".join(formatted)

def generate_code(
    shape_description: str,
    normalized_params: Dict[str, Any],
    system_context: Optional[str] = None,
    previous_code: Optional[str] = None,
    previous_parameters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Prompts the primary model (qwen2.5-coder:7b) to generate or modify a CadQuery python script.
    Retrieves the top-3 nearest worked examples from the ChromaDB vector database.
    """
    global last_retrieval_latency, last_generation_latency
    
    logger.info(f"Retrieving few-shot examples for description: '{shape_description}'...")
    retrieval_start = time.time()
    # Retrieve top 3 semantically similar examples
    examples = retrieve_examples(shape_description, k=3)
    last_retrieval_latency = time.time() - retrieval_start
    
    formatted_examples = format_few_shot_examples(examples)
    
    if previous_code:
        # Use modification template
        system_prompt = SYSTEM_PROMPT_MODIFICATION_TEMPLATE.format(few_shot_examples=formatted_examples)
        user_prompt = (
            f"Existing CAD Script:\n"
            f"```python\n"
            f"{previous_code}\n"
            f"```\n\n"
            f"Existing Parameters: {previous_parameters or {}}\n\n"
            f"Modification Requested: {shape_description}\n"
            f"New/Updated Parameters: {normalized_params}\n"
        )
    else:
        # Assemble system prompt dynamically for scratch generation
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(few_shot_examples=formatted_examples)
        user_prompt = f"Shape Description: {shape_description}\nNormalized Parameters: {normalized_params}\n"
        
    if system_context:
        user_prompt += f"\nContext/Previous Error: {system_context}\nPlease correct the code to avoid this error."
        
    payload = {
        "model": settings.PRIMARY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    
    logger.info("Calling code generator LLM...")
    gen_start = time.time()
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    response = httpx.post(url, json=payload, timeout=120.0)
    response.raise_for_status()
    last_generation_latency = time.time() - gen_start
    
    result_json = response.json()
    message_content = result_json["message"]["content"]
    logger.debug(f"Raw generator response: {message_content}")
    
    # Extract python code block
    code_match = re.search(r"```python\s*(.*?)\s*```", message_content, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
        return code
        
    if "import cadquery" in message_content:
        return message_content.strip()
        
    raise RuntimeError("Failed to extract python code block from generator response")


def generate_code_stream(
    shape_description: str,
    normalized_params: Dict[str, Any],
    system_context: Optional[str] = None,
    previous_code: Optional[str] = None,
    previous_parameters: Optional[Dict[str, Any]] = None
):
    """
    Calls the primary model (qwen2.5-coder:7b) to generate or modify a CadQuery script,
    returning a generator that yields token content in real-time.
    """
    logger.info(f"Retrieving few-shot examples for description: '{shape_description}'...")
    examples = retrieve_examples(shape_description, k=3)
    formatted_examples = format_few_shot_examples(examples)
    
    if previous_code:
        system_prompt = SYSTEM_PROMPT_MODIFICATION_TEMPLATE.format(few_shot_examples=formatted_examples)
        user_prompt = (
            f"Existing CAD Script:\n"
            f"```python\n"
            f"{previous_code}\n"
            f"```\n\n"
            f"Existing Parameters: {previous_parameters or {}}\n\n"
            f"Modification Requested: {shape_description}\n"
            f"New/Updated Parameters: {normalized_params}\n"
        )
    else:
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(few_shot_examples=formatted_examples)
        user_prompt = f"Shape Description: {shape_description}\nNormalized Parameters: {normalized_params}\n"
        
    if system_context:
        user_prompt += f"\nContext/Previous Error: {system_context}\nPlease correct the code to avoid this error."
        
    payload = {
        "model": settings.PRIMARY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": True,
        "options": {
            "temperature": 0.2
        }
    }
    
    logger.info("Calling code generator LLM in streaming mode...")
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    
    with httpx.stream("POST", url, json=payload, timeout=120.0) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content

