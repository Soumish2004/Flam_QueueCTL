"""Worker process manager for Windows"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict


class WorkerManager:
    """Manages worker processes on Windows"""
    
    def __init__(self):
        """Initialize worker manager"""
        data_dir = Path.home() / '.queuectl' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        self.workers_file = data_dir / 'workers.json'
    
    def _load_workers(self) -> List[Dict]:
        """Load worker list from file"""
        if not self.workers_file.exists():
            return []
        
        try:
            with open(self.workers_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_workers(self, workers: List[Dict]):
        """Save worker list to file"""
        with open(self.workers_file, 'w') as f:
            json.dump(workers, f, indent=2)
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running on Windows"""
        try:
            # Use tasklist to check if process exists
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                capture_output=True,
                text=True
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    
    def cleanup_dead_workers(self):
        """Remove dead worker entries"""
        workers = self._load_workers()
        active_workers = [w for w in workers if self._is_process_running(w['pid'])]
        
        if len(active_workers) != len(workers):
            self._save_workers(active_workers)
    
    def start_workers(self, count: int = 1) -> List[int]:
        """Start worker processes
        
        Args:
            count: Number of workers to start
        
        Returns:
            List of PIDs for started workers
        """
        self.cleanup_dead_workers()
        
        workers = self._load_workers()
        started_pids = []
        
        # Get the Python executable from the current environment
        python_exe = sys.executable
        
        # Get the worker script path
        worker_script = Path(__file__).parent / 'worker.py'
        
        for i in range(count):
            worker_id = f"worker-{len(workers) + i + 1}"
            
            # Start worker process in background
            # CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS | CREATE_NO_WINDOW
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NO_WINDOW = 0x08000000
            
            process = subprocess.Popen(
                [python_exe, str(worker_script), worker_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
            )
            
            workers.append({
                'pid': process.pid,
                'worker_id': worker_id
            })
            
            started_pids.append(process.pid)
            print(f"Started worker '{worker_id}' (PID: {process.pid})")
        
        self._save_workers(workers)
        return started_pids
    
    def stop_workers(self) -> int:
        """Stop all worker processes
        
        Returns:
            Number of workers stopped
        """
        self.cleanup_dead_workers()
        workers = self._load_workers()
        
        if not workers:
            print("No workers running")
            return 0
        
        stopped_count = 0
        
        for worker in workers:
            pid = worker['pid']
            worker_id = worker['worker_id']
            
            try:
                # Use taskkill to terminate process
                subprocess.run(
                    ['taskkill', '/PID', str(pid), '/F'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                print(f"Stopped worker '{worker_id}' (PID: {pid})")
                stopped_count += 1
            except Exception as e:
                print(f"Warning: Could not stop worker {worker_id} (PID: {pid}): {e}")
        
        # Wait a bit for processes to terminate
        time.sleep(1)
        
        # Clear workers file
        self._save_workers([])
        
        return stopped_count
    
    def get_active_workers(self) -> List[Dict]:
        """Get list of active workers"""
        self.cleanup_dead_workers()
        return self._load_workers()
    
    def get_worker_count(self) -> int:
        """Get count of active workers"""
        return len(self.get_active_workers())
