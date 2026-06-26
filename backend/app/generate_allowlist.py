import inspect
import json
import os
import cadquery as cq



def get_method_params(method):
    try:
        sig = inspect.signature(method)
        params = []
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                params.append("**kwargs")
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                params.append("*args")
            else:
                params.append(name)
        return params
    except (ValueError, TypeError):
        return []

def main():
    allowlist = {}

    # 1. Inspect cq.Workplane methods
    workplane_methods = {}
    for name, member in inspect.getmembers(cq.Workplane):
        if name.startswith('_') and name != '__init__':
            continue
        if inspect.isfunction(member) or inspect.ismethod(member) or inspect.isroutine(member):
            workplane_methods[name] = get_method_params(member)
    allowlist["Workplane"] = workplane_methods

    # 2. Inspect cq.Assembly methods
    assembly_methods = {}
    for name, member in inspect.getmembers(cq.Assembly):
        if name.startswith('_') and name != '__init__':
            continue
        if inspect.isfunction(member) or inspect.ismethod(member) or inspect.isroutine(member):
            assembly_methods[name] = get_method_params(member)
    allowlist["Assembly"] = assembly_methods

    # 3. Inspect cq.Shape / cq.Solid methods
    shape_methods = {}
    for name, member in inspect.getmembers(cq.Shape):
        if name.startswith('_') and name != '__init__':
            continue
        if inspect.isfunction(member) or inspect.ismethod(member) or inspect.isroutine(member):
            shape_methods[name] = get_method_params(member)
    for name, member in inspect.getmembers(cq.Solid):
        if name.startswith('_') and name != '__init__':
            continue
        if inspect.isfunction(member) or inspect.ismethod(member) or inspect.isroutine(member):
            # Do not overwrite shape methods unless solid has a more specific one
            if name not in shape_methods:
                shape_methods[name] = get_method_params(member)
    allowlist["Shape"] = shape_methods

    # 4. Top-level cadquery module functions (e.g. cq.exporters.export)
    module_funcs = {}
    # Top-level direct functions or modules we use
    # In worked examples: cq.exporters.export, cq.Assembly, cq.Workplane, cq.Solid.makeCone, etc.
    # Let's inspect cq.Solid static/class methods (like makeCone)
    solid_static_methods = {}
    for name, member in inspect.getmembers(cq.Solid):
        if name.startswith('_') and name != '__init__':
            continue
        # Check if it is a class method or static method
        if inspect.ismethod(member) or inspect.isfunction(member) or inspect.isroutine(member):
            solid_static_methods[name] = get_method_params(member)
    allowlist["Solid"] = solid_static_methods

    # Exporters functions
    exporter_funcs = {}
    for name, member in inspect.getmembers(cq.exporters):
        if name.startswith('_'):
            continue
        if inspect.isfunction(member) or inspect.isroutine(member):
            exporter_funcs[name] = get_method_params(member)
    allowlist["exporters"] = exporter_funcs

    # Save to json file
    output_path = os.path.join(os.path.dirname(__file__), "cad_api_allowlist.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(allowlist, f, indent=2)
    
    print(f"Allowlist generated and saved to {output_path}")

if __name__ == "__main__":
    main()
