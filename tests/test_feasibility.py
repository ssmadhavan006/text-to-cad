import pytest
from app.feasibility_gate import check_feasibility, parse_dimension

def test_parse_dimension():
    # Int and float
    assert parse_dimension(10) == 10.0
    assert parse_dimension(12.5) == 12.5
    
    # Strings without units (assume default mm)
    assert parse_dimension("15") == 15.0
    assert parse_dimension("  20.5  ") == 20.5
    
    # Strings with standard units (converting to mm)
    assert parse_dimension("10mm") == 10.0
    assert parse_dimension("1 cm") == 10.0
    assert parse_dimension("1 inch") == 25.4
    assert parse_dimension("2 in") == 50.8
    
    # Errors
    with pytest.raises(ValueError):
        parse_dimension(None)
    with pytest.raises(ValueError):
        parse_dimension("invalid_text")

def test_box_feasibility():
    # Valid box
    res = check_feasibility("box", {"length": 10, "width": "20mm", "height": "5 cm"})
    assert res.is_feasible
    assert res.normalized_parameters["length"] == 10.0
    assert res.normalized_parameters["width"] == 20.0
    assert res.normalized_parameters["height"] == 50.0
    
    # Missing param
    res = check_feasibility("box", {"length": 10, "width": 20})
    assert not res.is_feasible
    assert any("requires" in err for err in res.errors)
    
    # Zero or negative
    res = check_feasibility("box", {"length": 0, "width": 20, "height": -5})
    assert not res.is_feasible
    assert len(res.errors) == 2

def test_gear_feasibility():
    # Valid gear
    res = check_feasibility("spur_gear", {
        "module": 2,
        "teeth": 12,
        "bore_diameter": 6,
        "width": 10
    })
    assert res.is_feasible
    # pitch diameter = 2 * 12 = 24
    # root diameter = 24 - 2.5 * 2 = 19
    # wall thickness = (19 - 6) / 2 = 6.5 >= max(2.0, 2*1.2 = 2.4)
    assert res.normalized_parameters["pitch_diameter"] == 24.0
    assert res.normalized_parameters["root_diameter"] == 19.0
    
    # Too few teeth
    res = check_feasibility("spur_gear", {
        "module": 2,
        "teeth": 5,
        "bore_diameter": 6,
        "width": 10
    })
    assert not res.is_feasible
    assert any("at least 6" in err for err in res.errors)
    
    # Bore cuts through root circle
    res = check_feasibility("spur_gear", {
        "module": 2,
        "teeth": 12,
        "bore_diameter": 20, # Root diameter is 19
        "width": 10
    })
    assert not res.is_feasible
    assert any("larger than or equal to root diameter" in err for err in res.errors)
    
    # Wall thickness too thin
    res = check_feasibility("spur_gear", {
        "module": 2.0,
        "teeth": 12,
        "bore_diameter": 16.0, # root diameter = 19. Wall thickness = 1.5mm. Required min wall = 2.4mm
        "width": 10
    })
    assert not res.is_feasible
    assert any("too thin" in err for err in res.errors)

    # Valid gear with string pressure angle units
    res = check_feasibility("spur_gear", {
        "module": 2,
        "teeth": 12,
        "bore_diameter": 6,
        "width": 10,
        "pressure_angle": "20deg"
    })
    assert res.is_feasible
    assert res.normalized_parameters["pressure_angle"] == 20.0

    res = check_feasibility("spur_gear", {
        "module": 2,
        "teeth": 12,
        "bore_diameter": 6,
        "width": 10,
        "pressure_angle": "20 deg"
    })
    assert res.is_feasible
    assert res.normalized_parameters["pressure_angle"] == 20.0

def test_bracket_feasibility():
    # Valid L-bracket/plate
    res = check_feasibility("bracket", {
        "length": 100,
        "width": 50,
        "thickness": 5,
        "fillet_radius": 10,
        "hole_diameter": 8,
        "hole_offset": 15
    })
    assert res.is_feasible
    
    # Fillet too large
    res = check_feasibility("bracket", {
        "length": 100,
        "width": 50,
        "thickness": 5,
        "fillet_radius": 30 # max is 50/2 = 25
    })
    assert not res.is_feasible
    assert any("Fillet radius" in err for err in res.errors)
    
    # Hole wall too thin
    res = check_feasibility("bracket", {
        "length": 100,
        "width": 50,
        "thickness": 5,
        "hole_diameter": 10,
        "hole_offset": 5 # hole offset - dia/2 = 5 - 5 = 0 (cuts edge)
    })
    assert not res.is_feasible
    assert any("too close" in err for err in res.errors)
