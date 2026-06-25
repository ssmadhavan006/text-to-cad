import json
import logging
import httpx
from app.config import settings
from app.schemas import ExtractionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a CAD parameter extraction assistant.
Analyze the user's natural language mechanical design request and extract the CAD intent.
You must classify if the user wants to start a NEW shape from scratch, or MODIFY the existing active shape (e.g., adding features like holes, chamfers, fillets, or changing parameters like bore diameter).
You MUST output your response as a valid JSON object matching the following structure:
{
  "is_modification": true, // Boolean: set to true if the request modifies, adds to, or edits a previously generated shape (e.g. 'now add 4 holes', 'make the bore 12mm instead', 'fillet the top edge by 2mm', 'add a chamfer of 1mm'). Set to false if designing a completely new part from scratch.
  "shape_description": "Normalized natural language description of the target part / modifications (e.g. 'hexagonal mounting plate with 6 bolt holes' or 'add 4 mounting holes' or 'change bore diameter to 12mm')",
  "primary_operations": [
     // List of primary geometric operations described or added (e.g. "extrude", "revolve", "pattern", "fillet", "chamfer", "cut", "union")
  ],
  "parameters": {
     // Key-value pairs of dimensions extracted from the prompt.
     // Include units if specified in the text (e.g., "10mm", "2 inches", "5cm").
     // If a unit is not specified, output it as a raw number.
  },
  "reasoning": "Explain your extraction reasoning here."
}

Supported features and typical parameters:
- Primitives (box, cylinder, sphere, cone)
- Operations (extrude, revolve, fillet, chamfer, hole, cut, union, linear_pattern, circular_pattern)
- Dimensions (length, width, height, radius, diameter, thickness, module, teeth, pressure_angle, fillet_radius, chamfer_width, hole_diameter, hole_offset, pattern_radius, n_holes)

Example 1 (New shape): "design a spur gear with 12 teeth, module 2mm, 10mm bore, width 8mm"
Example 1 Output:
{
  "is_modification": false,
  "shape_description": "spur gear with 12 teeth and a center bore",
  "primary_operations": ["extrude", "pattern", "cut"],
  "parameters": {
    "module": "2mm",
    "teeth": 12,
    "bore_diameter": "10mm",
    "width": "8mm",
    "pressure_angle": 20.0
  },
  "reasoning": "The user wants a brand new spur gear part with module 2mm, 12 teeth, and a center bore."
}

Example 2 (Modification): "now add 4 mounting holes to that"
Example 2 Output:
{
  "is_modification": true,
  "shape_description": "add 4 mounting holes",
  "primary_operations": ["pattern", "cut"],
  "parameters": {
    "n_holes": 4
  },
  "reasoning": "The user is saying 'now add... to that', which implies modifying the existing active shape by adding a pattern of 4 holes."
}

Example 3 (Modification): "make the bore diameter 12mm instead"
Example 3 Output:
{
  "is_modification": true,
  "shape_description": "change bore diameter to 12mm",
  "primary_operations": ["cut"],
  "parameters": {
    "bore_diameter": "12mm"
  },
  "reasoning": "The word 'instead' indicates the user wants to update the parameter value of the existing center bore to 12mm."
}

Respond with a single valid JSON object. Do not wrap it in markdown code blocks.
"""

def infer_shape_type(description: str, operations: list[str]) -> str:
    """
    Deterministically maps a free-text shape description and operations list
    to one of the 6 standard shape schemas for feasibility gate routing.
    """
    desc_lower = description.lower()
    
    # 1. Spur gear
    if "gear" in desc_lower or "spur" in desc_lower:
        return "spur_gear"
        
    # 2. Cone
    if "cone" in desc_lower or "frustum" in desc_lower:
        return "cone"
        
    # 3. Sphere
    if "sphere" in desc_lower or "ball" in desc_lower:
        return "sphere"
        
    # 4. Bracket/Plate/Flange/Bushing
    if any(k in desc_lower for k in ["bracket", "plate", "flange", "sheet", "mounting", "bushing", "revolve", "polygon"]):
        return "bracket"
        
    # 5. Cylinder
    if any(k in desc_lower for k in ["cylinder", "pin", "rod", "disc"]):
        return "cylinder"
        
    # 6. Box
    if any(k in desc_lower for k in ["box", "cube", "block", "cuboid"]):
        return "box"
        
    # Fallback to general bracket/plate schema or box
    if "revolve" in operations or "pattern" in operations:
        return "bracket"
    return "box"

def extract_intent(prompt: str) -> ExtractionResult:
    """
    Calls the local Ollama instance using the fallback model (qwen2.5-coder:1.5b)
    to extract loose shape descriptions, modifications, and parameters.
    """
    models_to_try = [settings.FALLBACK_MODEL, settings.PRIMARY_MODEL]
    last_error = None

    for model in models_to_try:
        try:
            logger.info(f"Extracting intent using model {model}...")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract parameters from this prompt: '{prompt}'"}
                ],
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            }

            url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
            response = httpx.post(url, json=payload, timeout=20.0)
            response.raise_for_status()

            result_json = response.json()
            message_content = result_json["message"]["content"]
            logger.debug(f"Raw extractor response: {message_content}")

            data = json.loads(message_content.strip())
            
            desc = data.get("shape_description", "unknown")
            ops = data.get("primary_operations", [])
            is_mod = data.get("is_modification", False)
            
            # Infer standard shape_type for schema/feasibility gate compatibility
            inferred_type = infer_shape_type(desc, ops)
            
            return ExtractionResult(
                is_modification=is_mod,
                shape_description=desc,
                primary_operations=ops,
                shape_type=inferred_type,
                parameters=data.get("parameters", {}),
                reasoning=data.get("reasoning", "")
            )

        except Exception as e:
            logger.warning(f"Intent extraction failed with model {model}: {e}")
            last_error = e

    raise RuntimeError(f"All models failed to extract intent. Last error: {last_error}")

