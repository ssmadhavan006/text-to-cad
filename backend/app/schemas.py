from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Natural language mechanical design prompt")
    session_id: Optional[str] = Field(None, description="Active session ID for iterative editing")
    stream: Optional[bool] = Field(False, description="Whether to stream response events")


class ExtractionResult(BaseModel):
    is_modification: bool = Field(default=False, description="Whether this is a modification of an existing part")
    shape_description: str = Field(..., description="Normalized natural language description of the shape and operations (e.g. 'hexagonal mounting plate with 6 bolt holes')")
    primary_operations: List[str] = Field(default_factory=list, description="Primary operations inferred (e.g. ['extrude', 'pattern', 'fillet'])")
    shape_type: Optional[str] = Field(None, description="Identified standard category name: box, cylinder, sphere, cone, spur_gear, bracket")
    parameters: Dict[str, Any] = Field(..., description="Extracted shape parameters with units if provided")
    reasoning: Optional[str] = Field(None, description="Explanation/CoT for extraction")

class FeasibilityResult(BaseModel):
    is_feasible: bool = Field(..., description="Whether the request is geometrically and mechanically feasible")
    errors: List[str] = Field(default_factory=list, description="Reasons for rejection if not feasible")
    warnings: List[str] = Field(default_factory=list, description="Warnings about geometry limits")
    normalized_parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters normalized to standard units (mm, degrees, etc.)")

class ExecutionAttempt(BaseModel):
    attempt: int
    code: str
    success: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    output_id: Optional[str] = None
    latency_generation: Optional[float] = None
    latency_execution: Optional[float] = None


class GenerateResponse(BaseModel):
    success: bool
    shape_type: str
    extracted_parameters: Dict[str, Any]
    feasibility: FeasibilityResult
    final_code: Optional[str] = None
    step_file_url: Optional[str] = None
    stl_file_url: Optional[str] = None
    glb_file_url: Optional[str] = None
    attempts: int = 0
    history: List[ExecutionAttempt] = Field(default_factory=list)
    error_message: Optional[str] = None
    latency_intent: Optional[float] = None
    latency_retrieval: Optional[float] = None
    latency_total: Optional[float] = None
