import os
import httpx
import pytest
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_bracket_iterative_editing_chain():
    session_id = str(uuid.uuid4())
    
    # Turn 1: Create base mounting plate bracket
    payload1 = {
        "prompt": "design a simple mounting plate bracket with length 80mm, width 40mm, thickness 5mm",
        "session_id": session_id
    }
    print(f"\n[Turn 1] Sending prompt: {payload1['prompt']}")
    response1 = httpx.post(f"{BASE_URL}/api/generate", json=payload1, timeout=300.0)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["success"] is True
    assert data1["shape_type"] == "bracket"
    assert "length" in data1["extracted_parameters"]
    assert data1["extracted_parameters"]["length"] == "80mm"
    
    # Turn 2: Add 4 mounting holes to that plate
    payload2 = {
        "prompt": "now add 4 mounting holes to that of diameter 6mm and offset 12mm",
        "session_id": session_id
    }
    print(f"[Turn 2] Sending prompt: {payload2['prompt']}")
    response2 = httpx.post(f"{BASE_URL}/api/generate", json=payload2, timeout=300.0)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["success"] is True
    # The session should retain 'bracket' category
    assert data2["shape_type"] == "bracket"
    
    # Check parameters are merged
    params2 = data2["extracted_parameters"]
    assert "length" in params2
    assert "hole_diameter" in params2 or "n_holes" in params2
    # Ensure code contains hole-cutting operations
    code2 = data2["final_code"]
    assert "cut" in code2 or "hole" in code2
    
    # Turn 3: Add a 3mm fillet to the vertical edges
    payload3 = {
        "prompt": "add a fillet of 3mm to the Z edges",
        "session_id": session_id
    }
    print(f"[Turn 3] Sending prompt: {payload3['prompt']}")
    response3 = httpx.post(f"{BASE_URL}/api/generate", json=payload3, timeout=300.0)
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3["success"] is True
    assert data3["shape_type"] == "bracket"
    
    # Check final parameters are completely merged
    params3 = data3["extracted_parameters"]
    assert "length" in params3
    assert "fillet_radius" in params3 or "fillet" in params3 or "radius" in params3
    
    # Check final code has fillet and cut
    code3 = data3["final_code"]
    assert "fillet" in code3
    assert "cut" in code3 or "hole" in code3


def test_gear_iterative_editing_chain():
    session_id = str(uuid.uuid4())
    
    # Turn 1: Create base gear
    payload1 = {
        "prompt": "design a spur gear with teeth 12, module 2mm, width 8mm, bore 6mm",
        "session_id": session_id
    }
    print(f"\n[Turn 1] Sending prompt: {payload1['prompt']}")
    response1 = httpx.post(f"{BASE_URL}/api/generate", json=payload1, timeout=300.0)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["success"] is True
    assert data1["shape_type"] == "spur_gear"
    assert data1["extracted_parameters"]["teeth"] == 12
    assert data1["extracted_parameters"]["bore_diameter"] == "6mm"
    
    # Turn 2: Modify center bore size
    payload2 = {
        "prompt": "make the center bore diameter 12mm instead",
        "session_id": session_id
    }
    print(f"[Turn 2] Sending prompt: {payload2['prompt']}")
    response2 = httpx.post(f"{BASE_URL}/api/generate", json=payload2, timeout=300.0)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["success"] is True
    assert data2["shape_type"] == "spur_gear"
    
    # Verify updated bore diameter
    params2 = data2["extracted_parameters"]
    assert params2["bore_diameter"] == "12mm"
    assert params2["teeth"] == 12  # Merged parameter retained
    
    code2 = data2["final_code"]
    # Check if 12.0 is assigned to bore_diameter in the code
    assert "bore_diameter = 12.0" in code2 or "bore_diameter = 12" in code2
