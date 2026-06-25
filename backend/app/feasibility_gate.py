import logging
from typing import Any
from pint import UnitRegistry, UndefinedUnitError
from app.schemas import FeasibilityResult


logger = logging.getLogger(__name__)

# Initialize Pint unit registry
ureg = UnitRegistry()

def parse_dimension(value: Any, default_unit: str = "mm") -> float:
    """
    Parses a dimension value (which may be float, int, or string with units)
    and returns its magnitude in the specified default_unit (typically mm).
    """
    if value is None:
        raise ValueError("Dimension value cannot be None")
        
    if isinstance(value, (int, float)):
        return float(value)
        
    if isinstance(value, str):
        # Clean string
        val_str = value.strip()
        try:
            # Parse using pint
            quantity = ureg(val_str)
            # If quantity is dimensionless, assume default_unit
            if quantity.dimensionless:
                return float(quantity.magnitude)
            # Convert to target unit
            return float(quantity.to(default_unit).magnitude)
        except Exception as e:
            logger.warning(f"Failed to parse dimension '{value}' with pint: {e}. Attempting basic float conversion.")
            # Fallback: try stripping non-numeric chars and parse as float
            cleaned = "".join([c for c in val_str if c.isdigit() or c in ".-"])
            if cleaned:
                return float(cleaned)
            raise ValueError(f"Invalid dimension format: '{value}'")
            
    raise ValueError(f"Unsupported dimension type: {type(value)}")

def parse_angle(value: Any, default_unit: str = "degree") -> float:
    """
    Parses an angle value (which may be float, int, or string with units like deg, rad)
    and returns its magnitude in degrees.
    """
    if value is None:
        return 20.0
        
    if isinstance(value, (int, float)):
        return float(value)
        
    if isinstance(value, str):
        val_str = value.strip()
        try:
            quantity = ureg(val_str)
            if quantity.dimensionless:
                return float(quantity.magnitude)
            return float(quantity.to(default_unit).magnitude)
        except Exception as e:
            logger.warning(f"Failed to parse angle '{value}' with pint: {e}. Attempting basic float conversion.")
            cleaned = "".join([c for c in val_str if c.isdigit() or c in ".-"])
            if cleaned:
                return float(cleaned)
            return 20.0
            
    return 20.0


def check_feasibility(shape_type: str, raw_params: dict) -> FeasibilityResult:
    errors = []
    warnings = []
    normalized = {}
    
    # Standard min/max limits to prevent giant or microscopic shapes
    MIN_DIM = 0.1     # 0.1 mm
    MAX_DIM = 2000.0  # 2 meters (2000 mm)
    
    try:
        if shape_type == "box":
            # Extract length, width, height
            l_val = raw_params.get("length")
            w_val = raw_params.get("width")
            h_val = raw_params.get("height")
            
            if l_val is None or w_val is None or h_val is None:
                errors.append("Box requires length, width, and height parameters")
                return FeasibilityResult(is_feasible=False, errors=errors, warnings=warnings)
                
            length = parse_dimension(l_val)
            width = parse_dimension(w_val)
            height = parse_dimension(h_val)
            
            normalized = {"length": length, "width": width, "height": height}
            
            for name, val in [("length", length), ("width", width), ("height", height)]:
                if val <= 0:
                    errors.append(f"Box {name} must be greater than 0")
                elif val < MIN_DIM:
                    errors.append(f"Box {name} ({val} mm) is below the minimum allowed size of {MIN_DIM} mm")
                elif val > MAX_DIM:
                    errors.append(f"Box {name} ({val} mm) exceeds the maximum allowed size of {MAX_DIM} mm")
                    
        elif shape_type == "cylinder":
            r_val = raw_params.get("radius")
            d_val = raw_params.get("diameter")
            h_val = raw_params.get("height")
            
            if r_val is None and d_val is None:
                errors.append("Cylinder requires either radius or diameter")
            if h_val is None:
                errors.append("Cylinder requires height")
                
            if errors:
                return FeasibilityResult(is_feasible=False, errors=errors, warnings=warnings)
                
            height = parse_dimension(h_val)
            
            if r_val is not None:
                radius = parse_dimension(r_val)
                diameter = radius * 2.0
            else:
                diameter = parse_dimension(d_val)
                radius = diameter / 2.0
                
            normalized = {"radius": radius, "diameter": diameter, "height": height}
            
            if radius <= 0:
                errors.append("Cylinder radius must be greater than 0")
            elif radius < MIN_DIM/2:
                errors.append(f"Cylinder radius ({radius} mm) is below the minimum limit")
            elif radius > MAX_DIM/2:
                errors.append(f"Cylinder radius ({radius} mm) exceeds the maximum limit")
                
            if height <= 0:
                errors.append("Cylinder height must be greater than 0")
            elif height < MIN_DIM:
                errors.append(f"Cylinder height ({height} mm) is below the minimum limit")
            elif height > MAX_DIM:
                errors.append(f"Cylinder height ({height} mm) exceeds the maximum limit")
                
        elif shape_type == "sphere":
            r_val = raw_params.get("radius")
            d_val = raw_params.get("diameter")
            
            if r_val is None and d_val is None:
                errors.append("Sphere requires either radius or diameter")
                return FeasibilityResult(is_feasible=False, errors=errors, warnings=warnings)
                
            if r_val is not None:
                radius = parse_dimension(r_val)
                diameter = radius * 2.0
            else:
                diameter = parse_dimension(d_val)
                radius = diameter / 2.0
                
            normalized = {"radius": radius, "diameter": diameter}
            
            if radius <= 0:
                errors.append("Sphere radius must be greater than 0")
            elif radius < MIN_DIM/2:
                errors.append(f"Sphere radius ({radius} mm) is below the minimum limit")
            elif radius > MAX_DIM/2:
                errors.append(f"Sphere radius ({radius} mm) exceeds the maximum limit")
                
        elif shape_type == "cone":
            r1_val = raw_params.get("radius1") or raw_params.get("base_radius")
            r2_val = raw_params.get("radius2") or raw_params.get("top_radius")
            h_val = raw_params.get("height")
            
            if r1_val is None or r2_val is None or h_val is None:
                errors.append("Cone requires radius1 (base), radius2 (top), and height parameters")
                return FeasibilityResult(is_feasible=False, errors=errors, warnings=warnings)
                
            radius1 = parse_dimension(r1_val)
            radius2 = parse_dimension(r2_val)
            height = parse_dimension(h_val)
            
            normalized = {"radius1": radius1, "radius2": radius2, "height": height}
            
            if radius1 < 0 or radius2 < 0:
                errors.append("Cone radii must be non-negative")
            if radius1 == 0 and radius2 == 0:
                errors.append("Cone cannot have both radii equal to 0")
            if height <= 0:
                errors.append("Cone height must be greater than 0")
                
            for name, val in [("radius1", radius1), ("radius2", radius2), ("height", height)]:
                if val > MAX_DIM:
                    errors.append(f"Cone {name} ({val} mm) exceeds the maximum limit")
                    
        elif shape_type == "spur_gear":
            mod_val = raw_params.get("module")
            teeth_val = raw_params.get("teeth") or raw_params.get("num_teeth")
            bore_val = raw_params.get("bore_diameter") or raw_params.get("bore")
            width_val = raw_params.get("width") or raw_params.get("face_width") or raw_params.get("thickness")
            pa_val = raw_params.get("pressure_angle", 20.0) # default 20 deg
            
            if mod_val is None or teeth_val is None or bore_val is None or width_val is None:
                errors.append("Spur gear requires module, teeth, bore_diameter, and width (thickness) parameters")
                return FeasibilityResult(is_feasible=False, errors=errors, warnings=warnings)
                
            module = parse_dimension(mod_val)
            teeth = int(float(str(teeth_val)))
            bore_diameter = parse_dimension(bore_val)
            width = parse_dimension(width_val)
            pressure_angle = parse_angle(pa_val)
            
            # Geometry calculations
            pitch_diameter = module * teeth
            root_diameter = pitch_diameter - 2.5 * module
            outer_diameter = pitch_diameter + 2.0 * module
            
            normalized = {
                "module": module,
                "teeth": teeth,
                "bore_diameter": bore_diameter,
                "width": width,
                "pressure_angle": pressure_angle,
                "pitch_diameter": pitch_diameter,
                "root_diameter": root_diameter,
                "outer_diameter": outer_diameter
            }
            
            if module <= 0:
                errors.append("Gear module must be greater than 0")
            if teeth < 6:
                errors.append(f"Gear teeth count ({teeth}) must be at least 6 to avoid severe undercutting/interference")
            if width <= 0:
                errors.append("Gear width must be greater than 0")
            if not (14.0 <= pressure_angle <= 26.0):
                errors.append(f"Gear pressure angle ({pressure_angle} deg) must be between 14 and 26 degrees (standard is 20)")
                
            if bore_diameter <= 0:
                errors.append("Gear bore diameter must be greater than 0")
            else:
                if bore_diameter >= root_diameter:
                    errors.append(
                        f"Gear bore diameter ({bore_diameter} mm) is larger than or equal to root diameter ({root_diameter:.2f} mm). "
                        "The center bore would cut through the gear teeth!"
                    )
                else:
                    # Minimum hub wall thickness check
                    wall_thickness = (root_diameter - bore_diameter) / 2.0
                    min_required_wall = max(2.0, module * 1.2)
                    if wall_thickness < min_required_wall:
                        errors.append(
                            f"Gear hub wall thickness ({wall_thickness:.2f} mm) is too thin for strength. "
                            f"Requires at least {min_required_wall:.2f} mm (based on module and safety)."
                        )
                        
        elif shape_type == "bracket":
            # For brackets (L-bracket or mounting plate)
            l_val = raw_params.get("length")
            w_val = raw_params.get("width")
            t_val = raw_params.get("thickness") or raw_params.get("height") # plate thickness or flange height
            
            # Try to infer length/width for circular, revolved, or polygonal shapes
            is_revolved_or_circular = any(k in raw_params for k in ["diameter", "outer_diameter", "radius", "circumscribed_radius", "outer_radius"])
            if l_val is None or w_val is None:
                rad_val = raw_params.get("radius") or raw_params.get("circumscribed_radius") or raw_params.get("outer_radius")
                dia_val = raw_params.get("diameter") or raw_params.get("outer_diameter")
                if rad_val is not None:
                    parsed_rad = parse_dimension(rad_val)
                    l_val = l_val or str(parsed_rad * 2.0)
                    w_val = w_val or str(parsed_rad * 2.0)
                elif dia_val is not None:
                    parsed_dia = parse_dimension(dia_val)
                    l_val = l_val or str(parsed_dia)
                    w_val = w_val or str(parsed_dia)
                    
            fillet_val = raw_params.get("fillet_radius", 0.0)
            hole_dia_val = raw_params.get("hole_diameter") or raw_params.get("hole_dia", 0.0)
            
            pattern_radius_val = raw_params.get("pattern_radius") or raw_params.get("circle_radius") or raw_params.get("pattern_circle_radius")
            hole_off_val = raw_params.get("hole_offset") or raw_params.get("hole_off")
            if not hole_off_val and pattern_radius_val:
                hole_off_val = pattern_radius_val
            if not hole_off_val:
                hole_off_val = 0.0
            
            if l_val is None or w_val is None or t_val is None:
                errors.append("Bracket/Plate requires length, width, and thickness parameters")
                return FeasibilityResult(is_feasible=False, errors=errors, warnings=warnings)
                
            length = parse_dimension(l_val)
            width = parse_dimension(w_val)
            thickness = parse_dimension(t_val)
            fillet_radius = parse_dimension(fillet_val) if fillet_val else 0.0
            hole_diameter = parse_dimension(hole_dia_val) if hole_dia_val else 0.0
            hole_offset = parse_dimension(hole_off_val) if hole_off_val else 0.0
            
            # Fetch additional circular/pattern params
            circumscribed_radius_val = raw_params.get("circumscribed_radius")
            n_holes_val = raw_params.get("n_holes") or raw_params.get("num_holes") or raw_params.get("holes_count")
            inner_bore_val = raw_params.get("inner_bore_diameter") or raw_params.get("bore_diameter") or raw_params.get("inner_diameter")
            
            normalized = {
                "length": length,
                "width": width,
                "thickness": thickness,
                "fillet_radius": fillet_radius,
                "hole_diameter": hole_diameter,
                "hole_offset": hole_offset
            }
            if circumscribed_radius_val is not None:
                normalized["circumscribed_radius"] = parse_dimension(circumscribed_radius_val)
            if pattern_radius_val is not None:
                normalized["pattern_radius"] = parse_dimension(pattern_radius_val)
            if n_holes_val is not None:
                normalized["n_holes"] = int(float(str(n_holes_val)))
            if inner_bore_val is not None:
                normalized["inner_bore_diameter"] = parse_dimension(inner_bore_val)
            
            if length <= 0 or width <= 0 or thickness <= 0:
                errors.append("Bracket dimensions (length, width, thickness) must be greater than 0")
                
            if not is_revolved_or_circular and (thickness >= length or thickness >= width):
                errors.append(f"Thickness ({thickness} mm) must be smaller than length ({length} mm) and width ({width} mm)")
                
            if fillet_radius > 0:
                max_fillet = min(length, width) / 2.0
                if fillet_radius >= max_fillet:
                    errors.append(f"Fillet radius ({fillet_radius} mm) cannot be greater than half of the smallest face side ({max_fillet} mm)")
                    
            if hole_diameter > 0:
                if hole_diameter >= min(length, width):
                    errors.append(f"Hole diameter ({hole_diameter} mm) is larger than the plate dimensions")
                if hole_offset <= 0:
                    errors.append("Hole offset must be greater than 0 if hole diameter is specified")
                else:
                    # Check if hole lies inside the plate
                    min_dist_to_edge = hole_offset - (hole_diameter / 2.0)
                    if min_dist_to_edge <= 1.0: # 1mm wall thickness minimum
                        errors.append(f"Hole is too close to the plate edge (wall distance: {min_dist_to_edge:.2f} mm, min required: 1.0 mm)")
                    
                    if hole_offset + (hole_diameter / 2.0) > min(length, width):
                        errors.append("Hole position goes outside the plate boundaries")
                        
        else:
            errors.append(f"Unknown shape type '{shape_type}'. Supported shapes are: box, cylinder, sphere, cone, spur_gear, bracket")
            
    except ValueError as ve:
        errors.append(f"Parameter validation error: {str(ve)}")
    except Exception as e:
        logger.exception("Unexpected error in feasibility gate")
        errors.append(f"Unexpected error validating parameters: {str(e)}")
        
    is_feasible = len(errors) == 0
    return FeasibilityResult(
        is_feasible=is_feasible,
        errors=errors,
        warnings=warnings,
        normalized_parameters=normalized
    )
