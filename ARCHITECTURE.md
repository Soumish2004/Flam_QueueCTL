# QueueCTL Architecture

## System Overview

```
┌──────────┐
│   User   │
└────┬─────┘
     │ Commands
     ▼
┌─────────────────────────┐
│   queuectl.py (CLI)     │
│   • enqueue, list       │
│   • worker start/stop   │
│   • show, dlq, config   │
└────┬──────────────┬─────┘
     │              │
     │              │ Spawn/Kill
     ▼              ▼
┌──────────┐   ┌───────────────┐
│ Storage  │   │Worker Manager │
│ (DB ops) │   │(tasklist/kill)│
└────┬─────┘   └───────┬───────┘
     │                 │
     ▼                 ▼
┌────────────────────────────┐
│   SQLite (WAL mode)        │
│   ~/.queuectl/data/        │
│   ┌──────────────────────┐ │
│   │ JOBS: id, command,   │ │
│   │ state, priority,     │ │
│   │ waiting_time, output │ │
│   └──────────────────────┘ │
└──────────┬─────────────────┘
           │
           │ Poll (1 sec)
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────┐
│Worker-1 │  │Worker-N │
└────┬────┘  └────┬────┘
     │            │
     └─────┬──────┘
           │
           ▼
    ┌──────────────┐
    │ Worker Loop: │
    │ 1. Acquire   │
    │ 2. Execute   │
    │ 3. Update DB │
    └──────────────┘
```

## Job Lifecycle

```
     Enqueue
        │
        ▼
   ┌─────────┐
   │ PENDING │◄─────┐
   └────┬────┘      │
        │           │
   Worker picks     │ Retry
        │           │ (if attempts < max)
        ▼           │
  ┌───────────┐    │
  │PROCESSING │    │
  └─────┬─────┘    │
        │          │
    ┌───┴───┐      │
    │       │      │
 Success  Failure  │
    │       │      │
    ▼       ▼      │
 ┌──────┐ ┌────────┐
 │ DONE │ │ FAILED │─┘
 └──────┘ └───┬────┘
              │
              │ Max retries
              ▼
          ┌──────┐
          │ DEAD │ (DLQ)
          └──────┘
```

**States:**
- **PENDING**: Waiting for worker, `waiting_time` increments
- **PROCESSING**: Locked by worker, executing command
- **FAILED**: Retry scheduled with exponential backoff
- **DEAD**: In Dead Letter Queue, no more retries
- **COMPLETED**: Job finished successfully

## Priority & Anti-Starvation

**Effective Priority:** `priority + waiting_time`

```
When job enqueued:
  1. UPDATE all pending/failed jobs: waiting_time++
  2. INSERT new job with waiting_time = 0

Worker selection:
  SELECT * FROM jobs
  WHERE state IN ('pending', 'failed')
    AND locked_by IS NULL
  ORDER BY (priority + waiting_time) DESC
  LIMIT 1
```

**Example Queue:**
```
Job    Priority  Wait  Effective  → Selection
job1      3       5       8
job2      5       3       8
job3      8       0       8
job4      2       7       9        ← Picked! (oldest low-priority)
```

**Result:** Old jobs eventually execute, preventing starvation

## Worker Management

**Start Workers:**
```
worker start --count 3
     │
     ▼
subprocess.Popen(
  [python, worker.py, worker-id],
  creationflags=DETACHED_PROCESS |
                CREATE_NEW_PROCESS_GROUP |
                CREATE_NO_WINDOW
)
     │
     └─► Save PID to workers.json
```

**Worker Process:**
- Runs as detached Windows process (no console)
- Polls database every 1 second
- Acquires jobs with atomic lock
- Executes via `subprocess.run(timeout=N)`
- Captures stdout/stderr

**Stop Workers:**
```
worker stop
     │
     └─► Load workers.json
         └─► taskkill /PID <pid>
```

## Complete Job Flow

```
1. User Enqueues Job
   └─► storage.enqueue_job()
       ├─► UPDATE jobs SET waiting_time++
       └─► INSERT job1 (state=pending)

2. Worker Polls Database
   └─► storage.acquire_job(worker_id)
       ├─► SELECT job by priority+waiting_time
       └─► UPDATE jobs SET state=processing,
                          locked_by=worker-1
           WHERE id=job1 AND locked_by IS NULL
       └─► Return job (or None if already locked)

3. Worker Executes Command
   └─► subprocess.run(
         command,
         timeout=20,
         capture_output=True
       )
       └─► Captures: stdout, stderr, exit_code

4. Worker Saves Result
   ├─► Success: storage.complete_job()
   │   └─► UPDATE jobs SET state=completed,
   │                      output=<stdout>
   │
   └─► Failure: storage.fail_job()
       └─► attempts++
       ├─► If attempts < max:
       │   └─► UPDATE state=failed,
       │          next_retry_at=now+(base^attempts)
       └─► Else:
           └─► UPDATE state=dead (DLQ)

5. User Views Result
   └─► queuectl.py show job1
       └─► Display: state, output, error
```

## Retry & Exponential Backoff

**Formula:** `delay = backoff_base ^ attempts`

```
Job Execution Flow:
  Execute → Fails
     │
     ▼
  attempts++
     │
     ├─► attempts < max_retries?
     │   
     YES: Calculate delay
     │    └─► next_retry_at = now + (base ^ attempts)
     │    └─► State = FAILED
     │    └─► Worker will retry after delay
     │
     NO: Move to DLQ
         └─► State = DEAD
         └─► No more retries
```

**Example (base=2, max=3):**
```
Attempt 1 fails → retry in 2¹ = 2 seconds
Attempt 2 fails → retry in 2² = 4 seconds
Attempt 3 fails → retry in 2³ = 8 seconds
Attempt 4 fails → state = DEAD (moved to DLQ)
```

## Race Condition Prevention

**Problem:** Multiple workers trying to execute the same job

**Solution:** Atomic UPDATE with `locked_by` check

```
Time T0: Both Worker-1 and Worker-2 see job1
         ┌─────────────┬─────────────┐
         │  Worker-1   │  Worker-2   │
         └──────┬──────┴──────┬──────┘
                │             │
Time T1:        │             │
         Both execute:        │
         UPDATE jobs          │
         SET locked_by=<worker_id>
         WHERE id='job1'
           AND locked_by IS NULL
                │             │
                ▼             ▼
         SUCCESS (1 row)   FAIL (0 rows)
         rowcount=1        rowcount=0
                │             │
                ▼             ▼
         Process job1     Skip, query next job
```

**Result:** Only ONE worker acquires the job. Others skip and find different jobs.

## File Structure

```
QueueCTL/
├── queuectl.py              Main CLI entry point (Click framework)
│                            Routes commands to Storage/WorkerManager
│
├── queuectl/
│   ├── __init__.py          Package marker
│   ├── schema.sql           Database schema (jobs + config tables)
│   ├── storage.py           Database layer (all SQL operations)
│   ├── worker.py            Worker process (job execution loop)
│   └── worker_manager.py    Process manager (spawn/kill workers)
│
├── test.py                  Automated test suite (6 tests)
├── requirements.txt         Dependencies (click, tabulate)
└── README.md                Complete documentation

Runtime Data (~/.queuectl/data/):
├── queuectl.db              SQLite database (main data store)
├── queuectl.db-wal          Write-Ahead Log (WAL mode)
├── queuectl.db-shm          Shared memory (WAL mode)
└── workers.json             Active worker tracking (PID + worker_id)
```

## Database Schema

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,              -- pending, processing, completed, failed, dead
    attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout INTEGER DEFAULT 20,
    backoff_base INTEGER DEFAULT 2,
    priority INTEGER DEFAULT 5,       -- 1-10 (higher = more urgent)
    waiting_time INTEGER DEFAULT 0,   -- anti-starvation counter
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    next_retry_at TEXT,
    error_message TEXT,
    output TEXT,
    locked_by TEXT,                   -- worker_id holding the lock
    locked_at TEXT
);

CREATE INDEX idx_jobs_state ON jobs(state);
CREATE INDEX idx_jobs_next_retry ON jobs(next_retry_at);
CREATE INDEX idx_jobs_priority ON jobs(priority DESC, created_at ASC);
CREATE INDEX idx_jobs_locked ON jobs(locked_by);
```

---

**QueueCTL Architecture v1.0.0**
