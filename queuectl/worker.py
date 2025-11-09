"""Worker process for executing jobs"""

import subprocess
import time
import signal
import sys
import os
import uuid

# Handle both direct execution and package import
try:
    from .storage import Storage
except ImportError:
    # If run directly, add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from queuectl.storage import Storage


class Worker:
    """Worker that processes jobs from the queue"""
    
    def __init__(self, worker_id: str = None):
        """Initialize worker
        
        Args:
            worker_id: Unique worker identifier. If None, generates one.
        """
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.storage = Storage()
        self.running = True
        self.current_job = None
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n[{self.worker_id}] Received shutdown signal, finishing current job...")
        self.running = False
    
    def run(self):
        """Main worker loop"""
        print(f"\n{'='*70}")
        print(f"[{self.worker_id}] WORKER STARTED")
        print(f"  PID:      {os.getpid()}")
        print(f"  Started:  {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Status:   Polling for jobs...")
        print(f"{'='*70}\n")
        sys.stdout.flush()
        
        poll_count = 0
        while self.running:
            try:
                # Try to acquire a job
                job = self.storage.acquire_job(self.worker_id)
                
                if job:
                    self.current_job = job
                    self._execute_job(job)
                    self.current_job = None
                    poll_count = 0  # Reset poll counter after executing a job
                else:
                    # No jobs available, wait a bit
                    poll_count += 1
                    if poll_count % 10 == 0:  # Print every 10 seconds
                        print(f"[{self.worker_id}] Waiting for jobs... ({poll_count}s elapsed)")
                        sys.stdout.flush()
                    time.sleep(1)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"\n[{self.worker_id}] ERROR in worker loop: {e}\n")
                sys.stdout.flush()
                time.sleep(1)
        
        print(f"\n{'='*70}")
        print(f"[{self.worker_id}] WORKER STOPPED")
        print(f"  Shutdown:  {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        sys.stdout.flush()
    
    def _execute_job(self, job: dict):
        """Execute a single job
        
        Args:
            job: Job dictionary from storage
        """
        job_id = job['id']
        command = job['command']
        timeout = job['timeout']
        priority = job['priority']
        attempts = job['attempts']
        
        # Start timing
        start_time = time.time()
        
        print(f"\n{'='*70}")
        print(f"[{self.worker_id}] STARTING JOB")
        print(f"  Job ID:   {job_id}")
        print(f"  Command:  {command}")
        print(f"  Priority: {priority}")
        print(f"  Attempt:  {attempts + 1}/{job['max_retries'] + 1}")
        print(f"  Timeout:  {timeout}s")
        print(f"  Started:  {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        sys.stdout.flush()
        
        try:
            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Check exit code
            if result.returncode == 0:
                # Success
                output = result.stdout.strip() if result.stdout else ''
                
                print(f"\n[{self.worker_id}] JOB COMPLETED SUCCESSFULLY")
                print(f"  Job ID:        {job_id}")
                print(f"  Execution Time: {execution_time:.3f}s")
                print(f"  Exit Code:     {result.returncode}")
                if output:
                    print(f"  Output:        {output[:100]}{'...' if len(output) > 100 else ''}")
                print(f"{'='*70}\n")
                sys.stdout.flush()
                
                self.storage.complete_job(job_id, output, execution_time)
            else:
                # Command failed
                error_msg = f"Exit code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr.strip()}"
                
                execution_time = time.time() - start_time
                
                print(f"\n[{self.worker_id}] JOB FAILED")
                print(f"  Job ID:        {job_id}")
                print(f"  Execution Time: {execution_time:.3f}s")
                print(f"  Exit Code:     {result.returncode}")
                print(f"  Error:         {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}")
                
                # Calculate next retry info
                next_attempt = attempts + 2
                if next_attempt <= job['max_retries'] + 1:
                    delay = job['backoff_base'] ** (attempts + 1)
                    print(f"  Next Retry:    Attempt {next_attempt} in {delay}s")
                else:
                    print(f"  Next Retry:    None (moving to DLQ)")
                
                print(f"{'='*70}\n")
                sys.stdout.flush()
                
                self.storage.fail_job(job_id, error_msg, execution_time)
        
        except subprocess.TimeoutExpired:
            # Job exceeded timeout
            execution_time = time.time() - start_time
            error_msg = f"Timeout exceeded ({timeout}s)"
            
            print(f"\n[{self.worker_id}] JOB TIMED OUT")
            print(f"  Job ID:        {job_id}")
            print(f"  Execution Time: {execution_time:.3f}s (timeout: {timeout}s)")
            print(f"  Error:         {error_msg}")
            
            # Calculate next retry info
            next_attempt = attempts + 2
            if next_attempt <= job['max_retries'] + 1:
                delay = job['backoff_base'] ** (attempts + 1)
                print(f"  Next Retry:    Attempt {next_attempt} in {delay}s")
            else:
                print(f"  Next Retry:    None (moving to DLQ)")
            
            print(f"{'='*70}\n")
            sys.stdout.flush()
            
            self.storage.fail_job(job_id, error_msg, execution_time)
        
        except Exception as e:
            # Other errors
            execution_time = time.time() - start_time
            error_msg = f"Exception: {str(e)}"
            
            print(f"\n[{self.worker_id}] JOB ERROR")
            print(f"  Job ID:        {job_id}")
            print(f"  Execution Time: {execution_time:.3f}s")
            print(f"  Error:         {error_msg}")
            
            # Calculate next retry info
            next_attempt = attempts + 2
            if next_attempt <= job['max_retries'] + 1:
                delay = job['backoff_base'] ** (attempts + 1)
                print(f"  Next Retry:    Attempt {next_attempt} in {delay}s")
            else:
                print(f"  Next Retry:    None (moving to DLQ)")
            
            print(f"{'='*70}\n")
            sys.stdout.flush()
            
            self.storage.fail_job(job_id, error_msg, execution_time)


def start_worker(worker_id: str = None):
    """Start a worker process
    
    Args:
        worker_id: Optional worker identifier
    """
    worker = Worker(worker_id)
    worker.run()


if __name__ == '__main__':
    # Allow running worker directly
    worker_id = sys.argv[1] if len(sys.argv) > 1 else None
    start_worker(worker_id)
