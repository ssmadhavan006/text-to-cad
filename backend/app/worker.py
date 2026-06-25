import sys
import os
import json
import time
import traceback
import cadquery as cq

# Configure stdout and stderr to be line-buffered for real-time IPC
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Notify the parent process that the worker is pre-warmed and ready
print("READY")

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        job = json.loads(line.strip())
        code = job["code"]
        output_id = job["output_id"]
        outputs_dir = job["outputs_dir"]

        # Prepare isolated execution environment
        local_vars = {}
        global_vars = {
            "cq": cq,
            "__builtins__": __builtins__
        }

        stdout_capture = []
        stderr_capture = []

        class StreamCapture:
            def __init__(self, target_list):
                self.target_list = target_list
            def write(self, text):
                self.target_list.append(text)
            def flush(self):
                pass

        # Redirect standard streams to capture user prints and errors
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StreamCapture(stdout_capture)
        sys.stderr = StreamCapture(stderr_capture)

        success = False
        error_message = None
        start_time = time.time()

        try:
            # Execute generated CAD script
            exec(code, global_vars, local_vars)
            elapsed = time.time() - start_time

            # Verify that the final shape was successfully assigned to 'result'
            if "result" in local_vars:
                result = local_vars["result"]
                os.makedirs(outputs_dir, exist_ok=True)

                step_path = os.path.join(outputs_dir, f"{output_id}.step")
                stl_path = os.path.join(outputs_dir, f"{output_id}.stl")
                glb_path = os.path.join(outputs_dir, f"{output_id}.glb")

                # Export STEP and STL
                cq.exporters.export(result, step_path)
                cq.exporters.export(result, stl_path)

                # Export size-aware GLB/glTF mesh preview for smooth Three.js rendering
                try:
                    bbox = result.val().BoundingBox()
                    diag = bbox.DiagonalLength
                    tolerance = max(1e-4, min(0.5, diag * 0.0015))
                    angularTolerance = 0.05
                except Exception:
                    tolerance = 0.01
                    angularTolerance = 0.1

                assy = cq.Assembly()
                assy.add(result, name="part")
                assy.save(glb_path, tolerance=tolerance, angularTolerance=angularTolerance)

                success = True
            else:
                error_message = "ERROR: 'result' variable is not defined in the generated script"
        except Exception as e:
            elapsed = time.time() - start_time
            traceback.print_exc(file=sys.stderr)
            error_message = str(e)
        finally:
            # Restore original streams
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # Return execution results to parent
        response = {
            "success": success,
            "stdout": "".join(stdout_capture),
            "stderr": "".join(stderr_capture),
            "error_message": error_message,
            "elapsed": elapsed
        }
        print(json.dumps(response))

    except Exception as e:
        # Catch-all for IPC json-parsing or internal logic errors
        print(json.dumps({
            "success": False,
            "stdout": "",
            "stderr": traceback.format_exc(),
            "error_message": f"Worker internal error: {str(e)}",
            "elapsed": 0.0
        }))
