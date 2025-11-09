#!/usr/bin/env python3
"""
QueueCTL - CLI-based background job queue system

Job queue with workers, retries, and DLQ for Windows.
"""

import click
import json
import sys
from tabulate import tabulate

from queuectl.storage import Storage
from queuectl.worker_manager import WorkerManager

__version__ = '1.0.0'


@click.group()
@click.version_option(version=__version__, prog_name='queuectl')
def cli():
    """QueueCTL - Background job queue system
    
    Manage background jobs with automatic retries and worker processes.
    """
    pass


@cli.command()
@click.option('--id', required=True, help='Unique job identifier')
@click.option('--command', required=True, help='Shell command to execute')
@click.option('--max-retries', default=3, help='Maximum retry attempts')
@click.option('--timeout', default=20, help='Execution timeout in seconds')
@click.option('--backoff-base', default=2, help='Base for exponential backoff')
@click.option('--priority', default=5, help='Job priority 1-10 (higher = more urgent)')
def enqueue(id, command, max_retries, timeout, backoff_base, priority):
    """Enqueue a new job
    
    Examples:
        python queuectl.py enqueue --id job1 --command "echo Hello"
        python queuectl.py enqueue --id job2 --command "timeout 30" --timeout 5 --max-retries 3
        python queuectl.py enqueue --id job3 --command "python -c \"print('Hello')\"" --timeout 15
        python queuectl.py enqueue --id job4 --command "echo Priority" --priority 8
    """
    try:
        job_data = {
            'id': id,
            'command': command,
            'max_retries': max_retries,
            'timeout': timeout,
            'backoff_base': backoff_base,
            'priority': priority
        }
        
        # Validate required fields
        if 'id' not in job_data:
            click.echo("Error: Job must have 'id' field", err=True)
            sys.exit(1)
        
        if 'command' not in job_data:
            click.echo("Error: Job must have 'command' field", err=True)
            sys.exit(1)
        
        storage = Storage()
        success = storage.enqueue_job(job_data)
        
        if success:
            click.echo(f"Job '{job_data['id']}' enqueued successfully")
        else:
            click.echo(f"Failed to enqueue job '{job_data['id']}'", err=True)
            sys.exit(1)
    
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def worker():
    """Manage worker processes"""
    pass


@worker.command('start')
@click.option('--count', default=1, help='Number of workers to start')
@click.option('--foreground', '-f', is_flag=True, help='Run worker in foreground (shows real-time output)')
def worker_start(count, foreground):
    """Start worker processes
    
    Examples:
        python queuectl.py worker start
        python queuectl.py worker start --count 3
        python queuectl.py worker start --foreground  (see real-time job execution)
    """
    if foreground and count > 1:
        click.echo("Error: Foreground mode only supports 1 worker", err=True)
        sys.exit(1)
    
    if count < 1:
        click.echo("Error: Count must be at least 1", err=True)
        sys.exit(1)
    
    # Run in foreground mode - import and run worker directly
    if foreground:
        from queuectl.worker import Worker
        click.echo("Starting worker in foreground mode (Press Ctrl+C to stop)...\n")
        try:
            worker = Worker()
            worker.run()
        except KeyboardInterrupt:
            click.echo("\n\nWorker stopped by user")
        sys.exit(0)
    
    # Background mode - use WorkerManager
    manager = WorkerManager()
    
    try:
        pids = manager.start_workers(count)
        
        if pids:
            click.echo(f"Started {len(pids)} worker(s)")
        else:
            click.echo("Failed to start workers", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting workers: {e}", err=True)
        sys.exit(1)


@worker.command('stop')
def worker_stop():
    """Stop all worker processes
    
    Workers will finish their current job before stopping.
    
    Example:
        python queuectl.py worker stop
    """
    manager = WorkerManager()
    
    try:
        stopped = manager.stop_workers()
        
        if stopped > 0:
            click.echo(f"Stopped {stopped} worker(s)")
        else:
            click.echo("No workers to stop")
    except Exception as e:
        click.echo(f"Error stopping workers: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Show system status
    
    Displays job counts by state and active worker information.
    
    Example:
        python queuectl.py status
    """
    storage = Storage()
    manager = WorkerManager()
    
    try:
        stats = storage.get_status()
        workers = manager.get_active_workers()
        
        click.echo("=" * 50)
        click.echo("  QueueCTL Status")
        click.echo("=" * 50)
        click.echo()
        click.echo(f"Total Jobs:          {stats['total']}")
        click.echo()
        click.echo("Jobs by State:")
        click.echo(f"  Pending:           {stats['pending']}")
        click.echo(f"  Processing:        {stats['processing']}")
        click.echo(f"  Completed:         {stats['completed']}")
        click.echo(f"  Failed:            {stats['failed']}")
        click.echo(f"  Dead (DLQ):        {stats['dead']}")
        click.echo()
        click.echo("Workers:")
        click.echo(f"  Active Processes:  {len(workers)}")
        click.echo(f"  Currently Working: {stats['processing']} jobs")
        click.echo("=" * 50)
    
    except Exception as e:
        click.echo(f"Error getting status: {e}", err=True)
        sys.exit(1)


@cli.command('list')
@click.option('--state', help='Filter by job state (pending, processing, completed, failed, dead)')
def list_jobs(state):
    """List jobs
    
    Examples:
        python queuectl.py list
        python queuectl.py list --state pending
        python queuectl.py list --state dead
    """
    storage = Storage()
    
    try:
        jobs = storage.list_jobs(state)
        
        if not jobs:
            if state:
                click.echo(f"No jobs with state '{state}'")
            else:
                click.echo("No jobs found")
            return
        
        # Prepare table data
        headers = ['ID', 'Command', 'State', 'Attempts', 'Priority', 'Wait', 'Effective', 'Created At']
        rows = []
        
        for job in jobs:
            # Truncate command if too long
            command = job['command']
            if len(command) > 40:
                command = command[:37] + '...'
            
            # Format created_at
            created = job['created_at']
            if 'T' in created:
                created = created.split('T')[0] + ' ' + created.split('T')[1][:8]
            
            waiting_time = job.get('waiting_time', 0)
            effective_priority = job['priority'] + waiting_time
            
            rows.append([
                job['id'],
                command,
                job['state'],
                f"{job['attempts']}/{job['max_retries']}",
                job['priority'],
                waiting_time,
                effective_priority,
                created
            ])
        
        click.echo()
        click.echo(tabulate(rows, headers=headers, tablefmt='simple'))
        click.echo()
        click.echo(f"Total: {len(jobs)} job(s)")
    
    except Exception as e:
        click.echo(f"Error listing jobs: {e}", err=True)
        sys.exit(1)


@cli.group()
def dlq():
    """Dead Letter Queue operations"""
    pass


@dlq.command('list')
def dlq_list():
    """List jobs in Dead Letter Queue
    
    Example:
        python queuectl.py dlq list
    """
    storage = Storage()
    
    try:
        jobs = storage.list_dlq_jobs()
        
        if not jobs:
            click.echo("Dead Letter Queue is empty")
            return
        
        # Prepare table data
        headers = ['ID', 'Command', 'Attempts', 'Error', 'Failed At']
        rows = []
        
        for job in jobs:
            # Truncate command and error if too long
            command = job['command']
            if len(command) > 30:
                command = command[:27] + '...'
            
            error = job.get('error_message', '')
            if len(error) > 40:
                error = error[:37] + '...'
            
            # Format updated_at
            updated = job['updated_at']
            if 'T' in updated:
                updated = updated.split('T')[0] + ' ' + updated.split('T')[1][:8]
            
            rows.append([
                job['id'],
                command,
                job['attempts'],
                error,
                updated
            ])
        
        click.echo()
        click.echo(tabulate(rows, headers=headers, tablefmt='simple'))
        click.echo()
        click.echo(f"Total: {len(jobs)} job(s) in DLQ")
    
    except Exception as e:
        click.echo(f"Error listing DLQ: {e}", err=True)
        sys.exit(1)


@dlq.command('retry')
@click.argument('job_id')
def dlq_retry(job_id):
    """Retry a job from Dead Letter Queue
    
    JOB_ID is the unique identifier of the job to retry.
    
    Example:
        python queuectl.py dlq retry job1
    """
    storage = Storage()
    
    try:
        success = storage.retry_dlq_job(job_id)
        
        if success:
            click.echo(f"Job '{job_id}' moved back to pending queue")
        else:
            click.echo(f"Job '{job_id}' not found in DLQ or already retried", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Error retrying job: {e}", err=True)
        sys.exit(1)


@cli.group()
def config():
    """Manage configuration"""
    pass


@config.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """Set configuration value
    
    Available keys:
    - max-retries: Maximum retry attempts (default: 3)
    - backoff-base: Base for exponential backoff (default: 2)
    
    Example:
        python queuectl.py config set max-retries 5
        python queuectl.py config set backoff-base 3
    """
    storage = Storage()
    
    try:
        storage.set_config(key, value)
        click.echo(f"Set {key} = {value}")
    
    except Exception as e:
        click.echo(f"Error setting config: {e}", err=True)
        sys.exit(1)


@config.command('get')
@click.argument('key')
def config_get(key):
    """Get configuration value
    
    Example:
        python queuectl.py config get max-retries
    """
    storage = Storage()
    
    try:
        value = storage.get_config(key)
        
        if value:
            click.echo(f"{key} = {value}")
        else:
            click.echo(f"Config key '{key}' not found", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Error getting config: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
def show(job_id):
    """Show detailed information about a job including output
    
    JOB_ID is the unique identifier of the job to view.
    
    Example:
        python queuectl.py show hello-world
    """
    storage = Storage()
    
    try:
        job = storage.get_job(job_id)
        
        if not job:
            click.echo(f"Job '{job_id}' not found", err=True)
            sys.exit(1)
        
        waiting_time = job.get('waiting_time', 0)
        effective_priority = job['priority'] + waiting_time
        
        click.echo()
        click.echo("=" * 60)
        click.echo(f"  Job: {job['id']}")
        click.echo("=" * 60)
        click.echo(f"Command:      {job['command']}")
        click.echo(f"State:        {job['state']}")
        click.echo(f"Attempts:     {job['attempts']}/{job['max_retries']}")
        click.echo(f"Priority:     {job['priority']}")
        click.echo(f"Waiting Time: {waiting_time}")
        click.echo(f"Effective:    {effective_priority} (priority + waiting_time)")
        click.echo(f"Timeout:      {job['timeout']}s")
        
        if job.get('execution_time'):
            click.echo(f"Exec Time:    {job['execution_time']:.3f}s")
        
        click.echo(f"Created:      {job['created_at']}")
        click.echo(f"Updated:      {job['updated_at']}")
        
        if job['error_message']:
            click.echo(f"\nError:\n{job['error_message']}")
        
        if job['output']:
            click.echo(f"\nOutput:\n{job['output']}")
        
        click.echo("=" * 60)
        click.echo()
    
    except Exception as e:
        click.echo(f"Error showing job: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
def dequeue(job_id):
    """Remove a job from the queue
    
    JOB_ID is the unique identifier of the job to remove.
    
    Example:
        python queuectl.py dequeue job3
    """
    storage = Storage()
    
    try:
        success = storage.delete_job(job_id)
        
        if success:
            click.echo(f"Job '{job_id}' removed from queue")
        else:
            click.echo(f"Job '{job_id}' not found", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Error removing job: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--yes', is_flag=True, help='Skip confirmation')
def clear(yes):
    """Clear all jobs from database (for testing)
    
    WARNING: This will delete all jobs permanently!
    
    Example:
        python queuectl.py clear --yes
    """
    if not yes:
        click.confirm('This will delete ALL jobs. Are you sure?', abort=True)
    
    storage = Storage()
    
    try:
        storage.clear_all_jobs()
        click.echo("All jobs cleared from database")
    except Exception as e:
        click.echo(f"Error clearing jobs: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
