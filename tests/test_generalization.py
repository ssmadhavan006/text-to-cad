import os
import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"

def run_generalization_case(case_name: str, prompt: str):
    print(f"\nRunning Generalization Case: {case_name}")
    print(f"Prompt: '{prompt}'")
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/generate",
            json={"prompt": prompt},
            timeout=180.0
        )
        assert response.status_code == 200, f"HTTP error {response.status_code}"
        data = response.json()
        
        # Verify response format
        assert "success" in data, "Missing success field"
        
        # Verify feasibility results
        assert data["feasibility"]["is_feasible"] is True, f"Feasibility rejected: {data['feasibility']['errors']}"
        assert data["success"] is True, f"Pipeline failed: {data['error_message']}"
        
        # Verify STEP/STL outputs
        step_url = data["step_file_url"]
        stl_url = data["stl_file_url"]
        
        assert step_url is not None
        assert stl_url is not None
        
        step_filename = os.path.basename(step_url)
        stl_filename = os.path.basename(stl_url)
        
        # Paths relative to backend root
        step_path = os.path.join("backend", "static", "outputs", step_filename)
        stl_path = os.path.join("backend", "static", "outputs", stl_filename)
        
        assert os.path.exists(step_path), f"STEP file not found on disk: {step_path}"
        assert os.path.exists(stl_path), f"STL file not found on disk: {stl_path}"
        
        history_last = data['history'][-1] if data.get('history') else None
        output_id = history_last.get('output_id') if history_last else 'N/A'
        print(f"[OK] {case_name} PASSED! Output ID: {output_id} in {data['attempts']} attempts.")
        return data
        
    except Exception as e:
        print(f"[FAIL] {case_name} FAILED: {e}")
        raise e

def test_case_1_sphere_slice():
    # Sphere with a flat cut
    run_generalization_case(
        "Sphere with Flat Cut",
        "design a sphere with radius 20mm, with the top 5mm sliced off"
    )

def test_case_2_cone_frustum():
    # Truncated cone / frustum
    run_generalization_case(
        "Cone Frustum",
        "design a truncated cone with base radius 30mm, top radius 10mm, and height 40mm"
    )

def test_case_3_hex_plate_pattern():
    # Hexagonal plate with circular patterns of holes
    run_generalization_case(
        "Hexagonal Plate Pattern",
        "design a hexagonal plate with circumscribed radius 50mm, thickness 6mm, and 6 holes of 8mm diameter arranged in a circle of 30mm radius around the center"
    )

def test_case_4_revolved_bushing():
    # Revolved bushing
    run_generalization_case(
        "Revolved Bushing",
        "design a hollow bushing made by revolving an L-shaped profile of height 15mm, outer diameter 40mm, and inner bore diameter 20mm around the axis"
    )

def test_case_5_gear_generalization():
    # Spur gear with unusual parameters
    run_generalization_case(
        "Gear Parameter Generalization",
        "design a spur gear with 36 teeth, module 1.5mm, 15mm width, 12mm bore diameter, 20deg pressure angle"
    )

def test_case_6_compound_flange():
    # Compound circular flange with edge chamfer and circular pattern holes
    run_generalization_case(
        "Compound Circular Flange",
        "design a circular flange with diameter 120mm, thickness 8mm, 4 mounting holes of 10mm diameter on a pattern circle of 45mm radius, and a 2mm chamfer on the outer top edge"
    )
