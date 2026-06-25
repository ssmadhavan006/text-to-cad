import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_demo_case(title, prompt, expected_success):
    print("\n" + "="*50)
    print(f"DEMO CASE: {title}")
    print(f"PROMPT: '{prompt}'")
    print("="*50)
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/generate",
            json={"prompt": prompt},
            timeout=180.0
        )

        response.raise_for_status()
        res = response.json()
        
        print(f"Success: {res['success']}")
        print(f"Shape Identified: {res['shape_type']}")
        
        # Feasibility gate check
        print(f"Feasibility Check: {res['feasibility']['is_feasible']}")
        if not res['feasibility']['is_feasible']:
            print(f"Rejection Errors: {res['feasibility']['errors']}")
            
        # Self-correction check
        print(f"Total Compilation Attempts: {res['attempts']}")
        
        if res['success']:
            print(f"STEP File URL: {res['step_file_url']}")
            print(f"STL File URL: {res['stl_file_url']}")
            print("First 5 lines of code:")
            code_lines = res['final_code'].split("\n")
            for line in code_lines[:5]:
                print(f"  {line}")
                
        # Assert expectations
        assert res['success'] == expected_success, f"Expected success={expected_success}, but got {res['success']}"
        print("[OK] VERIFIED SUCCESSFULLY!")
        return True
    except Exception as e:
        print(f"[FAIL] FAILED VERIFICATION: {e}")
        return False

def main():
    print("Running Demo Hardening & Walkthrough Verification...")
    
    # 1. Simple Box primitive (Success)
    box_ok = run_demo_case(
        "Simple Primitive",
        "design a box with length 15mm, width 10mm, height 5mm",
        expected_success=True
    )
    
    # 2. Parametric Spur Gear (Success)
    gear_ok = run_demo_case(
        "Spur Gear (Domain Showcase)",
        "design a spur gear with 12 teeth, module 2mm, 10mm width, 6mm bore diameter",
        expected_success=True
    )
    
    # 3. L-bracket / Mounting plate (Success)
    bracket_ok = run_demo_case(
        "Bracket / Mounting Plate",
        "design a mounting plate bracket 80mm length, 40mm width, 5mm thickness, fillet 4mm, hole 6mm, offset 10mm",
        expected_success=True
    )
    
    # 4. Feasibility gate rejection
    reject_ok = run_demo_case(
        "Feasibility Gate Rejection (Undercut / Too thin hub)",
        "design a spur gear with 12 teeth, module 2mm, 18mm bore, 8mm width", # root diameter = 19mm, bore = 18mm, wall = 0.5mm (too thin)
        expected_success=False
    )
    
    all_ok = box_ok and gear_ok and bracket_ok and reject_ok
    if all_ok:
        print("\n[SUCCESS] ALL DEMO HARDENING CASES VERIFIED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\n[WARNING] SOME DEMO HARDENING CASES FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
