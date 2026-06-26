import pytest
from app.guardrail import validate_cad_api

def test_known_good_script_passes():
    # A standard valid box creation script
    code = """import cadquery as cq
length = 40.0
width = 30.0
height = 20.0
result = cq.Workplane("XY").box(length, width, height, centered=True)
"""
    err = validate_cad_api(code)
    assert err is None

def test_hallucinated_centered_workplane_caught():
    # Hallucinated centered parameter on workplane()
    code = """import cadquery as cq
result = cq.Workplane("XY").circle(50).extrude(10)
result = result.faces(">Z").workplane(centered=True).polarArray(35, 0, 360, 6).circle(4).cutThruAll()
"""
    err = validate_cad_api(code)
    assert err is not None
    assert "workplane()" in err
    assert "centered" in err
    assert "valid keyword arguments" in err

def test_hallucinated_centerx_workplane_caught():
    # Hallucinated centerX parameter on workplane()
    code = """import cadquery as cq
result = cq.Workplane("XY").circle(50).extrude(10)
result = result.faces(">Z").workplane(centerX=0, centerY=0).polarArray(35, 0, 360, 6).circle(4).cutThruAll()
"""
    err = validate_cad_api(code)
    assert err is not None
    assert "workplane()" in err
    assert "centerX" in err
    assert "valid keyword arguments" in err

def test_completely_invalid_method_caught():
    # Method name completely nonexistent on Workplane
    code = """import cadquery as cq
result = cq.Workplane("XY").nonexistent_method_name_xyz(123)
"""
    err = validate_cad_api(code)
    assert err is not None
    assert "nonexistent_method_name_xyz" in err
    assert "does not have method" in err
