import os
import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"

def test_api_health():
    response = httpx.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["engine"] == "CadQuery + OpenCASCADE"

def test_generate_box_e2e():
    payload = {
        "prompt": "design a box with length 10mm, width 20mm, height 30mm"
    }
    
    # Send request with a 60 second timeout since Ollama code generation can take time
    response = httpx.post(f"{BASE_URL}/api/generate", json=payload, timeout=60.0)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["shape_type"] == "box"
    
    # Check parameters
    params = data["extracted_parameters"]
    assert "length" in params
    assert "width" in params
    assert "height" in params
    
    # Check feasibility results
    assert data["feasibility"]["is_feasible"] is True
    
    # Verify file urls and files on disk
    step_url = data["step_file_url"]
    stl_url = data["stl_file_url"]
    assert step_url.startswith("/static/outputs/")
    assert stl_url.startswith("/static/outputs/")
    
    # Check if files actually exist on disk
    # The static files are served from backend/static/outputs
    step_filename = os.path.basename(step_url)
    stl_filename = os.path.basename(stl_url)
    
    step_path = os.path.join("backend", "static", "outputs", step_filename)
    stl_path = os.path.join("backend", "static", "outputs", stl_filename)
    
    assert os.path.exists(step_path), f"STEP file does not exist at {step_path}"
    assert os.path.exists(stl_path), f"STL file does not exist at {stl_path}"
    
    # Clean up generated files
    if os.path.exists(step_path):
        os.remove(step_path)
    if os.path.exists(stl_path):
        os.remove(stl_path)

def test_generate_rejected_by_feasibility_gate():
    # A gear with teeth < 6 is rejected
    payload = {
        "prompt": "design a spur gear with 4 teeth, module 2mm, bore 6mm, width 10mm"
    }
    
    response = httpx.post(f"{BASE_URL}/api/generate", json=payload, timeout=30.0)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is False
    assert data["feasibility"]["is_feasible"] is False
    assert len(data["feasibility"]["errors"]) > 0
    assert any("teeth" in err for err in data["feasibility"]["errors"])
    assert data["final_code"] is None
