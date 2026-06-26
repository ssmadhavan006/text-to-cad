import ast
import json
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class CADApiValidator(ast.NodeVisitor):
    def __init__(self, allowlist: Dict[str, Any]):
        self.allowlist = allowlist
        self.errors = []
        # Maps variable name to its inferred CAD type category
        self.cad_vars = {
            'cq': 'module',
            'result': 'Workplane',
            'cube': 'Workplane',
            'cylinder': 'Workplane',
            'cutter': 'Workplane',
            'assy': 'Assembly',
            'plate': 'Workplane',
            'gear': 'Workplane',
            'bracket': 'Workplane',
            'bushing': 'Workplane',
            'shape': 'Shape',
            'solid': 'Shape',
            'part': 'Shape',
            'base': 'Workplane'
        }

    def infer_type(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return self.cad_vars.get(node.id)
            
        elif isinstance(node, ast.Attribute):
            # Check for module reference like cq.Workplane or cq.Solid
            if isinstance(node.value, ast.Name) and node.value.id == 'cq':
                if node.attr == 'Workplane':
                    return 'Workplane'
                elif node.attr == 'Assembly':
                    return 'Assembly'
                elif node.attr == 'Solid':
                    return 'Solid'
                elif node.attr == 'Shape':
                    return 'Shape'
                elif node.attr == 'exporters':
                    return 'exporters'
            
            # Check chained properties
            recv_type = self.infer_type(node.value)
            if recv_type == 'Solid' or recv_type == 'Shape':
                return 'Shape'
            return recv_type
            
        elif isinstance(node, ast.Call):
            # Constructor call or method call
            func_type = self.infer_type(node.func)
            if func_type in {"Workplane", "Assembly", "Solid", "Shape"}:
                return func_type
            if isinstance(node.func, ast.Attribute):
                recv_type = self.infer_type(node.func.value)
                method_name = node.func.attr
                if recv_type == 'Workplane':
                    if method_name in {'val', 'vals', 'all'}:
                        return 'Shape'
                    return 'Workplane'
                elif recv_type in {'Solid', 'Shape'}:
                    return 'Shape'
                elif recv_type == 'Assembly':
                    return 'Assembly'
            elif isinstance(node.func, ast.Name):
                return self.cad_vars.get(node.func.id)
        return None

    def visit_Assign(self, node: ast.Assign):
        # Visit children to process any method calls on RHS first
        self.generic_visit(node)
        
        # Trace data flow: if RHS is a CAD expression, add targets to cad_vars
        inferred = self.infer_type(node.value)
        if inferred:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.cad_vars[target.id] = inferred

    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)
        
        if isinstance(node.func, ast.Attribute):
            recv_type = self.infer_type(node.func.value)
            if recv_type in {"Workplane", "Assembly", "Solid", "Shape", "exporters"}:
                method_name = node.func.attr
                
                # Exclude standard internal/private python calls or methods we don't check
                if method_name.startswith('_'):
                    return

                # Map inferred type to allowlist category
                category = recv_type
                if recv_type in {"Solid", "Shape"}:
                    category = "Shape"
                
                cat_allowlist = self.allowlist.get(category)
                if not cat_allowlist:
                    # If Solid is static method call, fallback to Solid category
                    if recv_type == "Solid":
                        cat_allowlist = self.allowlist.get("Solid", {})
                    else:
                        return
                
                # Check method existence
                if method_name not in cat_allowlist:
                    # Fallback check for Shape vs Solid static methods
                    if category == "Shape" and method_name in self.allowlist.get("Solid", {}):
                        cat_allowlist = self.allowlist["Solid"]
                    else:
                        self.errors.append(
                            f"CadQuery {category} object does not have method '{method_name}'"
                        )
                        return

                # Check keyword arguments
                allowed_args = cat_allowlist[method_name]
                
                # If method accepts **kwargs, any keyword arguments are valid
                if "**kwargs" in allowed_args:
                    return

                for kw in node.keywords:
                    # Ignore keyword arguments passed via dict unpacking (e.g. **some_dict)
                    if kw.arg is None:
                        continue
                    if kw.arg not in allowed_args:
                        clean_allowed = [a for a in allowed_args if not a.startswith('*')]
                        err = (
                            f"CadQuery {category}.{method_name}() does not accept keyword argument '{kw.arg}' "
                            f"— valid keyword arguments are: {clean_allowed}"
                        )
                        self.errors.append(err)

def validate_cad_api(code: str) -> Optional[str]:
    """
    Parses the generated python code and statically validates that all method calls on
    CadQuery objects exist in the allowlist and use valid keyword arguments.
    Returns the first validation error string, or None if validation passes.
    """
    try:
        tree = ast.parse(code)
    except Exception as e:
        return f"Syntax error in script: {e}"

    # Load allowlist
    allowlist_path = os.path.join(os.path.dirname(__file__), "cad_api_allowlist.json")
    try:
        with open(allowlist_path, "r", encoding="utf-8") as f:
            allowlist = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load CAD API allowlist: {e}")
        allowlist = {}

    validator = CADApiValidator(allowlist)
    validator.visit(tree)
    
    if validator.errors:
        logger.warning(f"Static validation failed: {validator.errors[0]}")
        return validator.errors[0]
    return None
