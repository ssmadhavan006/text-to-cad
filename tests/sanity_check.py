import os
import cadquery as cq

def run_sanity_check():
    print("Running CadQuery sanity check...")
    # Create a simple box
    box = cq.Workplane("XY").box(10.0, 20.0, 30.0)
    
    # Ensure outputs directory exists
    os.makedirs("tests/output", exist_ok=True)
    
    # Export to STEP and STL
    step_path = "tests/output/sanity_box.step"
    stl_path = "tests/output/sanity_box.stl"
    
    cq.exporters.export(box, step_path)
    cq.exporters.export(box, stl_path)
    
    print(f"Exported STEP to: {step_path} (exists: {os.path.exists(step_path)})")
    print(f"Exported STL to: {stl_path} (exists: {os.path.exists(stl_path)})")
    
    if os.path.exists(step_path) and os.path.exists(stl_path):
        print("Sanity check passed successfully!")
    else:
        raise RuntimeError("Sanity check files not found!")

if __name__ == "__main__":
    run_sanity_check()
