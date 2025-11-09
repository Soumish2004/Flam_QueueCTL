"""Storage layer for QueueCTL using SQLite"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any


class Storage:
    """Handles all database operations for jobs and configuration"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize storage with database connection
        
        Args:
            db_path: Path to SQLite database. If None, uses default ~/.queuectl/data/queuectl.db
        """
        if db_path is None:
            data_dir = Path.home() / '.queuectl' / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / 'queuectl.db')
        
        self.db_path = db_path
        self._initialize_database()
    
    def _get_connection(self):
        """Get a new database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
    
    def _initialize_database(self):
        """Create database and tables if they don't exist"""
        conn = self._get_connection()
        
        try:
            # Read and execute schema
            schema_path = Path(__file__).parent / 'schema.sql'
            with open(schema_path, 'r') as f:
                schema = f.read()
            
            conn.executescript(schema)
            conn.commit()
            
            # Migrations: Add new columns if they don't exist
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(jobs)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'waiting_time' not in columns:
                conn.execute('ALTER TABLE jobs ADD COLUMN waiting_time INTEGER NOT NULL DEFAULT 0')
                conn.commit()
            
            if 'execution_time' not in columns:
                conn.execute('ALTER TABLE jobs ADD COLUMN execution_time REAL')
                conn.commit()
        finally:
            conn.close()
    
    def enqueue_job(self, job_data: Dict[str, Any]) -> bool:
        """Add a new job to the queue
        
        Args:
            job_data: Dictionary containing job fields
        
        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        
        try:
            # Get default config values
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = 'max-retries'")
            row = cursor.fetchone()
            default_max_retries = int(row['value']) if row else 3
            
            cursor.execute("SELECT value FROM config WHERE key = 'backoff-base'")
            row = cursor.fetchone()
            default_backoff_base = int(row['value']) if row else 2
            
            # Increment waiting_time for all pending and failed jobs
            conn.execute('''
                UPDATE jobs
                SET waiting_time = waiting_time + 1
                WHERE state IN ('pending', 'failed') AND locked_by IS NULL
            ''')
            
            # Prepare job data with defaults
            job_id = job_data.get('id')
            command = job_data.get('command')
            max_retries = job_data.get('max_retries', default_max_retries)
            timeout = job_data.get('timeout', 20)
            backoff_base = job_data.get('backoff_base', default_backoff_base)
            priority = job_data.get('priority', 5)
            
            now = datetime.utcnow().isoformat()
            
            conn.execute('''
                INSERT INTO jobs (id, command, state, attempts, max_retries, timeout, 
                                 backoff_base, priority, waiting_time, created_at, updated_at)
                VALUES (?, ?, 'pending', 0, ?, ?, ?, ?, 0, ?, ?)
            ''', (job_id, command, max_retries, timeout, backoff_base, priority, now, now))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error enqueuing job: {e}")
            return False
        finally:
            conn.close()
    
    def acquire_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Atomically acquire a pending job for processing
        
        Args:
            worker_id: Unique identifier for the worker
        
        Returns:
            Job dictionary if acquired, None otherwise
        """
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            # Find pending jobs or failed jobs ready for retry
            # Order by combined priority (priority + waiting_time)
            cursor.execute('''
                SELECT *
                FROM jobs
                WHERE (state = 'pending' OR (state = 'failed' AND next_retry_at <= ?))
                  AND locked_by IS NULL
                ORDER BY (priority + waiting_time) DESC, created_at ASC
                LIMIT 1
            ''', (now,))
            
            job = cursor.fetchone()
            
            if job is None:
                return None
            
            job_id = job['id']
            
            # Try to lock the job atomically
            cursor.execute('''
                UPDATE jobs
                SET state = 'processing',
                    locked_by = ?,
                    locked_at = ?,
                    updated_at = ?
                WHERE id = ? AND locked_by IS NULL
            ''', (worker_id, now, now, job_id))
            
            conn.commit()
            
            # Check if we actually acquired the lock
            if cursor.rowcount == 0:
                return None
            
            # Fetch the updated job
            cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            acquired_job = cursor.fetchone()
            
            return dict(acquired_job) if acquired_job else None
        finally:
            conn.close()
    
    def complete_job(self, job_id: str, output: str = '', execution_time: float = None):
        """Mark job as completed
        
        Args:
            job_id: Job identifier
            output: Job output/result
            execution_time: Time taken to execute in seconds
        """
        conn = self._get_connection()
        
        try:
            now = datetime.utcnow().isoformat()
            conn.execute('''
                UPDATE jobs
                SET state = 'completed',
                    output = ?,
                    execution_time = ?,
                    locked_by = NULL,
                    locked_at = NULL,
                    updated_at = ?
                WHERE id = ?
            ''', (output, execution_time, now, job_id))
            
            conn.commit()
        finally:
            conn.close()
    
    def fail_job(self, job_id: str, error_message: str, execution_time: float = None):
        """Handle job failure with retry logic
        
        Args:
            job_id: Job identifier
            error_message: Error description
            execution_time: Time taken before failure in seconds
        """
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return
            
            attempts = job['attempts'] + 1
            max_retries = job['max_retries']
            backoff_base = job['backoff_base']
            now = datetime.utcnow().isoformat()
            
            if attempts >= max_retries:
                # Move to DLQ
                conn.execute('''
                    UPDATE jobs
                    SET state = 'dead',
                        attempts = ?,
                        error_message = ?,
                        execution_time = ?,
                        locked_by = NULL,
                        locked_at = NULL,
                        next_retry_at = NULL,
                        updated_at = ?
                    WHERE id = ?
                ''', (attempts, error_message, execution_time, now, job_id))
            else:
                # Schedule retry with exponential backoff
                delay = backoff_base ** attempts
                next_retry = datetime.utcnow() + timedelta(seconds=delay)
                next_retry_str = next_retry.isoformat()
                
                conn.execute('''
                    UPDATE jobs
                    SET state = 'failed',
                        attempts = ?,
                        error_message = ?,
                        execution_time = ?,
                        locked_by = NULL,
                        locked_at = NULL,
                        next_retry_at = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (attempts, error_message, execution_time, next_retry_str, now, job_id))
            
            conn.commit()
        finally:
            conn.close()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            job = cursor.fetchone()
            return dict(job) if job else None
        finally:
            conn.close()
    
    def list_jobs(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered by state"""
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            
            if state:
                cursor.execute('SELECT * FROM jobs WHERE state = ? ORDER BY created_at DESC', (state,))
            else:
                cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
            
            jobs = cursor.fetchall()
            return [dict(job) for job in jobs]
        finally:
            conn.close()
    
    def get_status(self) -> Dict[str, Any]:
        """Get summary statistics of all jobs"""
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as total FROM jobs')
            total = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT state, COUNT(*) as count
                FROM jobs
                GROUP BY state
            ''')
            
            by_state = {row['state']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total': total,
                'pending': by_state.get('pending', 0),
                'processing': by_state.get('processing', 0),
                'completed': by_state.get('completed', 0),
                'failed': by_state.get('failed', 0),
                'dead': by_state.get('dead', 0)
            }
        finally:
            conn.close()
    
    def list_dlq_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs in Dead Letter Queue"""
        return self.list_jobs('dead')
    
    def retry_dlq_job(self, job_id: str) -> bool:
        """Retry a job from DLQ"""
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT state FROM jobs WHERE id = ?', (job_id,))
            job = cursor.fetchone()
            
            if not job or job['state'] != 'dead':
                return False
            
            now = datetime.utcnow().isoformat()
            conn.execute('''
                UPDATE jobs
                SET state = 'pending',
                    attempts = 0,
                    error_message = NULL,
                    next_retry_at = NULL,
                    locked_by = NULL,
                    locked_at = NULL,
                    updated_at = ?
                WHERE id = ?
            ''', (now, job_id))
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def set_config(self, key: str, value: str):
        """Set configuration value"""
        conn = self._get_connection()
        
        try:
            conn.execute('''
                INSERT OR REPLACE INTO config (key, value)
                VALUES (?, ?)
            ''', (key, value))
            
            conn.commit()
        finally:
            conn.close()
    
    def get_config(self, key: str, default: str = '') -> str:
        """Get configuration value"""
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
        finally:
            conn.close()
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a specific job from the queue
        
        Args:
            job_id: The ID of the job to delete
            
        Returns:
            True if job was deleted, False if not found
        """
        conn = self._get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def clear_all_jobs(self):
        """Clear all jobs from database (for testing)"""
        conn = self._get_connection()
        
        try:
            conn.execute('DELETE FROM jobs')
            conn.commit()
        finally:
            conn.close()
