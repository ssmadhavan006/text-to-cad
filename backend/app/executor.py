import os
import sys
import uuid
import subprocess
import logging
import time
import json
import queue
import threading
from app.config import settings
from app.schemas import ExecutionAttempt
from app.guardrail import validate_cad_api

logger = logging.getLogger(__name__)

class WorkerPool:
    def __init__(self):
        self.worker_proc = None
        self.run_count = 0
        self.lock = threading.Lock()
        
    def get_worker(self):
        with self.lock:
            # Recycle worker if it ran 10 times to prevent memory leaks/pollution
            if self.run_count >= 10:
                logger.info("Recycling worker process after 10 runs...")
                self.kill_worker()
                self.run_count = 0
                
            if self.worker_proc is None or self.worker_proc.poll() is not None:
                logger.info("Spawning a new persistent CadQuery worker process...")
                worker_path = os.path.join(settings.BASE_DIR, "app", "worker.py")
                self.worker_proc = subprocess.Popen(
                    [sys.executable, worker_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1, # Line buffered
                    cwd=settings.BASE_DIR
                )
                
                # Wait for READY signal
                ready = self.worker_proc.stdout.readline().strip()
                if ready != "READY":
                    err_msg = self.worker_proc.stderr.read()
                    self.kill_worker()
                    raise RuntimeError(f"Failed to start worker: {ready}. Stderr: {err_msg}")
                    
            self.run_count += 1
            return self.worker_proc
            
    def kill_worker(self):
        if self.worker_proc:
            try:
                self.worker_proc.kill()
            except Exception:
                pass
            self.worker_proc = None

# Global pool instance
worker_pool = WorkerPool()

def execute_code(code: str, attempt_num: int) -> ExecutionAttempt:
    """
    Executes the generated CadQuery script in a persistent worker process.
    """
    output_id = str(uuid.uuid4())
    
    # Pre-execution static AST validation guardrail
    validation_err = validate_cad_api(code)
    if validation_err:
        logger.warning(f"AST validation rejected script on attempt {attempt_num}: {validation_err}")
        return ExecutionAttempt(
            attempt=attempt_num,
            code=code,
            success=False,
            stdout="",
            stderr="",
            error_message=validation_err,
            output_id=output_id,
            latency_generation=0.0,
            latency_execution=0.0
        )
    
    exec_latency = 0.0
    try:
        proc = worker_pool.get_worker()
        logger.info(f"Sending code to worker (Attempt {attempt_num})...")
        
        payload = {
            "code": code,
            "output_id": output_id,
            "outputs_dir": settings.OUTPUTS_DIR
        }
        
        exec_start = time.time()
        # Write job payload to worker stdin
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
        
        # Read stdout line-by-line with a 30s timeout using a helper thread
        q = queue.Queue()
        def read_stdout(p, out_q):
            try:
                line = p.stdout.readline()
                out_q.put(line)
            except Exception as ex:
                out_q.put(ex)
                
        t = threading.Thread(target=read_stdout, args=(proc, q), daemon=True)
        t.start()
        
        try:
            line = q.get(timeout=30.0)
        except queue.Empty:
            # Timeout occurred! Kill worker and raise exception
            logger.warning("Worker execution timed out! Killing worker process...")
            worker_pool.kill_worker()
            raise subprocess.TimeoutExpired(cmd=["worker.py"], timeout=30.0)
            
        if isinstance(line, Exception):
            raise line
            
        exec_latency = time.time() - exec_start
        response = json.loads(line.strip())
        
        success = response["success"]
        stdout = response["stdout"]
        stderr = response["stderr"]
        error_msg = response["error_message"]
        
        # Recycle worker on errors to keep execution pristine
        if not success:
            logger.warning(f"Execution failed: {error_msg}. Recycling worker...")
            worker_pool.kill_worker()
            
        return ExecutionAttempt(
            attempt=attempt_num,
            code=code,
            success=success,
            stdout=stdout,
            stderr=stderr,
            error_message=error_msg,
            output_id=output_id if success else None,
            latency_execution=exec_latency
        )
        
    except subprocess.TimeoutExpired as te:
        return ExecutionAttempt(
            attempt=attempt_num,
            code=code,
            success=False,
            stdout="",
            stderr="TimeoutExpired",
            error_message="Execution timed out (exceeded 30 seconds limit)",
            latency_execution=30.0
        )
    except Exception as e:
        logger.exception("Failed to run script in worker process")
        # Recycle worker on any unexpected exception to be safe
        worker_pool.kill_worker()
        return ExecutionAttempt(
            attempt=attempt_num,
            code=code,
            success=False,
            stdout="",
            stderr=str(e),
            error_message=f"Executor system error: {str(e)}",
            latency_execution=0.0
        )


