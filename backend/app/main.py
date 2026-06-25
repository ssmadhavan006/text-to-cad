from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.schemas import GenerateRequest, GenerateResponse, FeasibilityResult, ExecutionAttempt
from app.intent_extractor import extract_intent
from app.feasibility_gate import check_feasibility
from app.code_generator import generate_code
from app.executor import execute_code
from app.vector_store import initialize_vector_store
import os
import logging
import time
import app.code_generator as code_generator

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup static directories
os.makedirs(settings.OUTPUTS_DIR, exist_ok=True)

app = FastAPI(title="Text-to-CAD Engine API", version="1.0.0")

# CORS middleware to allow connection from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP, allow all origins. Can be restricted to frontend dev port later.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static outputs directory containing generated STEP/STL files
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

@app.on_event("startup")
async def on_startup():
    initialize_vector_store()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "engine": "CadQuery + OpenCASCADE",
        "primary_model": settings.PRIMARY_MODEL,
        "fallback_model": settings.FALLBACK_MODEL
    }

sessions = {}

async def generate_cad_stream_events(req: GenerateRequest):
    import json
    import asyncio
    import re
    from app.vector_store import retrieve_examples
    from app.code_generator import generate_code_stream
    
    start_total = time.time()
    
    # 1. Intent Extraction
    yield f"data: {json.dumps({'event': 'stage', 'data': 'Extracting parameters...'})}\n\n"
    await asyncio.sleep(0.001)
    
    try:
        intent_start = time.time()
        extraction = extract_intent(req.prompt)
        latency_intent = time.time() - intent_start
        logger.info(f"Extracted shape: {extraction.shape_type} with parameters: {extraction.parameters}")
    except Exception as e:
        logger.exception("Failed to extract intent")
        yield f"data: {json.dumps({'event': 'error', 'data': f'LLM extraction error: {str(e)}'})}\n\n"
        return
        
    is_mod = extraction.is_modification and req.session_id and (req.session_id in sessions)
    previous_code = None
    previous_params = {}
    shape_type = extraction.shape_type
    raw_params_to_check = extraction.parameters
    
    if is_mod:
        session_data = sessions[req.session_id]
        previous_code = session_data["final_code"]
        previous_params = session_data["normalized_parameters"]
        shape_type = session_data["shape_type"]
        
        merged_raw_params = dict(session_data.get("raw_parameters", {}))
        merged_raw_params.update(extraction.parameters)
        raw_params_to_check = merged_raw_params
        
    # 2. Feasibility Gate
    yield f"data: {json.dumps({'event': 'stage', 'data': 'Checking feasibility...'})}\n\n"
    await asyncio.sleep(0.001)
    
    feasibility = check_feasibility(shape_type, raw_params_to_check)
    if not feasibility.is_feasible:
        err_msg = "Rejected by Feasibility Gate: " + "; ".join(feasibility.errors)
        logger.warning(err_msg)
        yield f"data: {json.dumps({'event': 'error', 'data': err_msg})}\n\n"
        return
        
    # 3. Code Generation and Self-Correction Loop
    attempts_history = []
    max_attempts = 3
    current_code = ""
    error_context = None
    
    last_retrieval = 0.0
    for attempt_num in range(1, max_attempts + 1):
        attempt_start = time.time()
        
        yield f"data: {json.dumps({'event': 'stage', 'data': f'Generating CadQuery script (Attempt {attempt_num})...'})}\n\n"
        await asyncio.sleep(0.001)
        
        try:
            logger.info("Retrieving few-shots...")
            retrieval_start = time.time()
            examples = retrieve_examples(extraction.shape_description, k=3)
            last_retrieval = time.time() - retrieval_start
            
            # Start streaming code generation
            generator_stream = generate_code_stream(
                shape_description=extraction.shape_description,
                normalized_params=feasibility.normalized_parameters,
                system_context=error_context,
                previous_code=previous_code,
                previous_parameters=previous_params if is_mod else None
            )
            
            accumulated = ""
            yielded_cot_len = 0
            yielded_code_len = 0
            in_code = False
            code_start_idx = -1
            
            for token in generator_stream:
                accumulated += token
                
                # If not in code block yet, check if ```python is in accumulated
                if not in_code:
                    idx = accumulated.find("```python")
                    if idx != -1:
                        unyielded_cot = accumulated[yielded_cot_len:idx]
                        yielded_cot_len = idx
                        in_code = True
                        code_start_idx = idx + len("```python")
                        
                        if unyielded_cot:
                            yield f"data: {json.dumps({'event': 'cot', 'data': unyielded_cot})}\n\n"
                        yield f"data: {json.dumps({'event': 'code_start', 'data': ''})}\n\n"
                        
                        remaining = accumulated[code_start_idx:]
                        if remaining:
                            closing_idx = remaining.find("```")
                            if closing_idx != -1:
                                code_part = remaining[:closing_idx]
                                in_code = False
                                yielded_code_len = len(code_part)
                                yield f"data: {json.dumps({'event': 'code', 'data': code_part})}\n\n"
                                yield f"data: {json.dumps({'event': 'code_end', 'data': ''})}\n\n"
                            else:
                                yielded_code_len = len(remaining)
                                yield f"data: {json.dumps({'event': 'code', 'data': remaining})}\n\n"
                    else:
                        unyielded_cot = accumulated[yielded_cot_len:]
                        yielded_cot_len = len(accumulated)
                        if unyielded_cot:
                            yield f"data: {json.dumps({'event': 'cot', 'data': unyielded_cot})}\n\n"
                else:
                    code_content = accumulated[code_start_idx:]
                    closing_idx = code_content.find("```")
                    if closing_idx != -1:
                        new_code = code_content[:closing_idx]
                        unyielded_code = new_code[yielded_code_len:]
                        yielded_code_len = len(new_code)
                        in_code = False
                        
                        if unyielded_code:
                            yield f"data: {json.dumps({'event': 'code', 'data': unyielded_code})}\n\n"
                        yield f"data: {json.dumps({'event': 'code_end', 'data': ''})}\n\n"
                    else:
                        new_code = code_content
                        unyielded_code = new_code[yielded_code_len:]
                        yielded_code_len = len(new_code)
                        if unyielded_code:
                            yield f"data: {json.dumps({'event': 'code', 'data': unyielded_code})}\n\n"
                
                await asyncio.sleep(0.001)
                
            # Extract the final code from the accumulated stream
            code_match = re.search(r"```python\s*(.*?)\s*```", accumulated, re.DOTALL)
            if code_match:
                current_code = code_match.group(1).strip()
            elif "import cadquery" in accumulated:
                current_code = accumulated.strip()
            else:
                raise RuntimeError("Failed to extract python code block from generator response")
                
            generation_latency = time.time() - attempt_start
            
            # Execute
            yield f"data: {json.dumps({'event': 'stage', 'data': f'Executing CadQuery script (Attempt {attempt_num})...'})}\n\n"
            await asyncio.sleep(0.001)
            
            attempt = execute_code(current_code, attempt_num)
            attempt.latency_generation = generation_latency
            attempts_history.append(attempt)
            
            if attempt.success:
                logger.info(f"CAD generation succeeded on attempt {attempt_num}!")
                step_url = f"/static/outputs/{attempt.output_id}.step"
                stl_url = f"/static/outputs/{attempt.output_id}.stl"
                glb_url = f"/static/outputs/{attempt.output_id}.glb"
                
                if req.session_id:
                    sessions[req.session_id] = {
                        "final_code": current_code,
                        "normalized_parameters": feasibility.normalized_parameters,
                        "raw_parameters": raw_params_to_check,
                        "shape_type": shape_type
                    }
                    
                resp_json = GenerateResponse(
                    success=True,
                    shape_type=shape_type,
                    extracted_parameters=raw_params_to_check,
                    feasibility=feasibility,
                    final_code=current_code,
                    step_file_url=step_url,
                    stl_file_url=stl_url,
                    glb_file_url=glb_url,
                    attempts=attempt_num,
                    history=attempts_history,
                    latency_intent=latency_intent,
                    latency_retrieval=last_retrieval,
                    latency_total=time.time() - start_total
                ).dict()
                
                yield f"data: {json.dumps({'event': 'success', 'data': resp_json})}\n\n"
                return
            else:
                logger.warning(f"Attempt {attempt_num} failed: {attempt.error_message}")
                yield f"data: {json.dumps({'event': 'attempt_failed', 'data': f'Attempt {attempt_num} failed: {attempt.error_message}'})}\n\n"
                await asyncio.sleep(0.001)
                
                error_context = (
                    f"Code failed to execute correctly.\n"
                    f"Return Code / Traceback Error:\n{attempt.error_message}\n"
                    f"Stdout:\n{attempt.stdout or ''}"
                )
                
        except Exception as gen_err:
            logger.exception(f"Unexpected exception during attempt {attempt_num}")
            error_context = f"Internal generator error: {str(gen_err)}"
            attempts_history.append(ExecutionAttempt(
                attempt=attempt_num,
                code=current_code,
                success=False,
                error_message=error_context,
                latency_generation=time.time() - attempt_start,
                latency_execution=0.0
            ))
            yield f"data: {json.dumps({'event': 'attempt_failed', 'data': f'Attempt {attempt_num} failed: {error_context}'})}\n\n"
            await asyncio.sleep(0.001)

    # Exhausted attempts
    logger.error("Self-correction loop exhausted all attempts without success")
    resp_json = GenerateResponse(
        success=False,
        shape_type=shape_type,
        extracted_parameters=raw_params_to_check,
        feasibility=feasibility,
        attempts=max_attempts,
        history=attempts_history,
        error_message="Self-correction loop exhausted all attempts without success.",
        latency_intent=latency_intent,
        latency_retrieval=last_retrieval,
        latency_total=time.time() - start_total
    ).dict()
    yield f"data: {json.dumps({'event': 'error', 'data': resp_json})}\n\n"


@app.post("/api/generate")
async def generate_cad(req: GenerateRequest):
    if req.stream:
        return StreamingResponse(generate_cad_stream_events(req), media_type="text/event-stream")

    start_total = time.time()
    logger.info(f"Received generation request: {req.prompt} (Session ID: {req.session_id})")
    
    # 1. Intent Extraction
    try:
        intent_start = time.time()
        extraction = extract_intent(req.prompt)
        latency_intent = time.time() - intent_start
        logger.info(f"Extracted shape: {extraction.shape_type} with parameters: {extraction.parameters}. is_modification: {extraction.is_modification}")
    except Exception as e:
        logger.exception("Failed to extract intent")
        raise HTTPException(status_code=500, detail=f"LLM extraction error: {str(e)}")
        
    # Check if this is a valid modification request
    is_mod = extraction.is_modification and req.session_id and (req.session_id in sessions)
    
    previous_code = None
    previous_params = {}
    shape_type = extraction.shape_type
    raw_params_to_check = extraction.parameters
    
    if is_mod:
        session_data = sessions[req.session_id]
        previous_code = session_data["final_code"]
        previous_params = session_data["normalized_parameters"]
        shape_type = session_data["shape_type"]
        
        # Merge raw parameters: start with session's raw parameters and update with new ones
        merged_raw_params = dict(session_data.get("raw_parameters", {}))
        merged_raw_params.update(extraction.parameters)
        raw_params_to_check = merged_raw_params
        logger.info(f"Session active. Merging raw parameters: {merged_raw_params}")
    else:
        logger.info("Starting a new CAD generation session / context.")

    # 2. Feasibility Gate (deterministic checks)
    feasibility = check_feasibility(shape_type, raw_params_to_check)
    if not feasibility.is_feasible:
        logger.warning(f"Request rejected by feasibility gate: {feasibility.errors}")
        return GenerateResponse(
            success=False,
            shape_type=shape_type,
            extracted_parameters=raw_params_to_check,
            feasibility=feasibility,
            error_message="Rejected by Feasibility Gate: " + "; ".join(feasibility.errors),
            latency_intent=latency_intent,
            latency_total=time.time() - start_total
        )
        
    # 3. Code Generation and Self-Correction Loop
    attempts_history = []
    max_attempts = 3
    current_code = ""
    error_context = None
    
    last_retrieval = 0.0
    for attempt_num in range(1, max_attempts + 1):
        attempt_start = time.time()
        try:
            # Generate or modify code
            current_code = generate_code(
                shape_description=extraction.shape_description,
                normalized_params=feasibility.normalized_parameters,
                system_context=error_context,
                previous_code=previous_code,
                previous_parameters=previous_params if is_mod else None
            )
            last_retrieval = code_generator.last_retrieval_latency
            
            # Execute generated code in the subprocess sandbox
            attempt = execute_code(current_code, attempt_num)
            attempt.latency_generation = code_generator.last_generation_latency
            attempts_history.append(attempt)
            
            if attempt.success:
                logger.info(f"CAD generation succeeded on attempt {attempt_num}!")
                
                # File URLs for static serving
                step_url = f"/static/outputs/{attempt.output_id}.step"
                stl_url = f"/static/outputs/{attempt.output_id}.stl"
                glb_url = f"/static/outputs/{attempt.output_id}.glb"
                
                # Update session state on success
                if req.session_id:
                    sessions[req.session_id] = {
                        "final_code": current_code,
                        "normalized_parameters": feasibility.normalized_parameters,
                        "raw_parameters": raw_params_to_check,
                        "shape_type": shape_type
                    }
                
                return GenerateResponse(
                    success=True,
                    shape_type=shape_type,
                    extracted_parameters=raw_params_to_check,
                    feasibility=feasibility,
                    final_code=current_code,
                    step_file_url=step_url,
                    stl_file_url=stl_url,
                    glb_file_url=glb_url,
                    attempts=attempt_num,
                    history=attempts_history,
                    latency_intent=latency_intent,
                    latency_retrieval=last_retrieval,
                    latency_total=time.time() - start_total
                )
            else:
                logger.warning(f"Attempt {attempt_num} failed: {attempt.error_message}")
                # Use standard error traceback to prompt self-correction on next retry
                error_context = (
                    f"Code failed to execute correctly.\n"
                    f"Return Code / Traceback Error:\n{attempt.error_message}\n"
                    f"Stdout:\n{attempt.stdout or ''}"
                )
                
        except Exception as gen_err:
            logger.exception(f"Unexpected exception during attempt {attempt_num}")
            error_context = f"Internal generator error: {str(gen_err)}"
            attempts_history.append(ExecutionAttempt(
                attempt=attempt_num,
                code=current_code,
                success=False,
                error_message=error_context,
                latency_generation=time.time() - attempt_start,
                latency_execution=0.0
            ))

    # If execution failed after all retries
    logger.error("Self-correction loop exhausted all attempts without success")
    return GenerateResponse(
        success=False,
        shape_type=shape_type,
        extracted_parameters=raw_params_to_check,
        feasibility=feasibility,
        attempts=max_attempts,
        history=attempts_history,
        error_message="Self-correction loop exhausted all attempts without success.",
        latency_intent=latency_intent,
        latency_retrieval=last_retrieval,
        latency_total=time.time() - start_total
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
