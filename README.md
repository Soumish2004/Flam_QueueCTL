# QueueCTL - CLI-Based Background Job Queue System(Windows)



Job queue system with worker processes, automatic retries with exponential backoff, and Dead Letter Queue (DLQ) for permanently failed jobs.Job queue system with worker processes, automatic retries with exponential backoff, and Dead Letter Queue (DLQ) for permanently failed jobs.



**Platform:** Windows Only**Platform:** Windows Only



------

[QueueCTL demo video](https://drive.google.com/file/d/1-JknvUK10GXpTTq_HFYbLStj2N9pK8RR/view?usp=sharing)

## Table of Contents## Features



- [Setup Instructions](#setup-instructions)- **Enqueue Jobs** - Add background jobs to persistent SQLite queue  

- [Usage Examples](#usage-examples)- **Multiple Workers** - Run concurrent worker processes  

- [Architecture Overview](#architecture-overview)- **Retry Mechanism** - Automatic retries with exponential backoff  

- [Assumptions & Trade-offs](#assumptions--trade-offs)- **Dead Letter Queue (DLQ)** - Track permanently failed jobs  

- [Testing Instructions](#testing-instructions)- **Persistent Storage** - SQLite database survives restarts  

- **Worker Management** - Start/stop workers gracefully  

---- **Job States** - Pending, processing, completed, failed, dead  

- **Configuration** - Manage retry and backoff settings  

## Setup Instructions- **Race-Safe** - Atomic job locking prevents duplicate execution  

- **Priority Queues** - Jobs with priority 1-10 (higher = more urgent)

### Prerequisites

---

- Python 3.8 or higher

- Windows OS (PowerShell)## Getting Started

- Git (optional, for cloning)

### 1. Setup (One-Time)

### Installation Steps

```powershell

1. **Clone or Download the Project**# Navigate to project directory

cd d:\QueueCTL

```powershell

cd d:\QueueCTL# Run setup script

```.\setup.ps1

```

2. **Run the Setup Script**

### 2. Enqueue Jobs

The setup script creates a virtual environment and installs dependencies:

```powershell

```powershell# Activate virtual environment

.\setup.ps1.\venv\Scripts\Activate.ps1

```

# Enqueue jobs using JSON strings

This will:python queuectl.py enqueue "{\"id\":\"job1\",\"command\":\"echo Hello\"}"

- Create a Python virtual environment in `venv/`python queuectl.py enqueue "{\"id\":\"job2\",\"command\":\"timeout 30\",\"timeout\":5,\"max_retries\":3,\"backoff_base\":2}"

- Install required packages (`click`, `tabulate`)python queuectl.py enqueue "{\"id\":\"job3\",\"command\":\"echo High Priority\",\"priority\":8}"

- Verify the installation```



3. **Activate Virtual Environment**### 3. Start Workers



```powershell```powershell

.\venv\Scripts\Activate.ps1# Start 2 workers

```python queuectl.py worker start --count 2

```

4. **Verify Installation**

### 4. Monitor Progress

```powershell

python queuectl.py --version```powershell

# Output: queuectl, version 1.0.0# Check status

```python queuectl.py status



### Project Structure# List all jobs

python queuectl.py list

```

QueueCTL/# List pending jobs only

├── queuectl/python queuectl.py list --state pending

│   ├── __init__.py          # Package initialization```

│   ├── schema.sql           # Database schema

│   ├── storage.py           # Database operations### 5. Stop Workers

│   ├── worker.py            # Job execution worker

│   └── worker_manager.py    # Worker process management```powershell

├── queuectl.py              # Main CLI entry pointpython queuectl.py worker stop

├── requirements.txt         # Python dependencies```

├── setup.ps1               # Setup script

├── test.py                 # Test suite---

└── README.md               # This file

```## Command Reference



### Data Location| Command | Description |

|---------|-------------|

- **Database:** `C:\Users\<YourName>\.queuectl\data\queuectl.db`| `python queuectl.py enqueue "JSON"` | Add a new job |

- **Worker Tracking:** `C:\Users\<YourName>\.queuectl\data\workers.json`| `python queuectl.py worker start` | Start 1 worker |

| `python queuectl.py worker start --count N` | Start N workers |

---| `python queuectl.py worker stop` | Stop all workers |

| `python queuectl.py status` | View system status |

## Usage Examples| `python queuectl.py list` | List all jobs |

| `python queuectl.py list --state STATE` | List jobs by state |

### 1. Enqueue Jobs| `python queuectl.py dlq list` | List failed jobs in DLQ |

| `python queuectl.py dlq retry JOB_ID` | Retry a DLQ job |

**Basic Job:**| `python queuectl.py config set KEY VALUE` | Set configuration |

```powershell| `python queuectl.py config get KEY` | Get configuration |

python queuectl.py enqueue --id job1 --command "echo Hello World"| `python queuectl.py clear --yes` | Clear all jobs |

```

---

**Output:**

```## Job Configuration

Job 'job1' enqueued successfully

```### Required Fields

- **id**: Unique job identifier (string)

**Job with Custom Timeout and Retries:**- **command**: Shell command to execute (string)

```powershell

python queuectl.py enqueue --id job2 --command "timeout 30" --timeout 5 --max-retries 3 --backoff-base 2### Optional Fields

```- **timeout**: Maximum execution time in seconds (default: 20)

- **max_retries**: Maximum retry attempts (default: 3)

**High Priority Job:**- **backoff_base**: Base for exponential backoff (default: 2)

```powershell- **priority**: Job priority 1-10, higher = more urgent (default: 5)

python queuectl.py enqueue --id job3 --command "echo Priority Task" --priority 8

```### Example



**Available Options:**```json

- `--id` (required): Unique job identifier{

- `--command` (required): Shell command to execute  "id": "my-job",

- `--timeout` (default: 20): Execution timeout in seconds  "command": "echo Processing...",

- `--max-retries` (default: 3): Maximum retry attempts  "timeout": 30,

- `--backoff-base` (default: 2): Base for exponential backoff  "max_retries": 5,

- `--priority` (default: 5): Priority level (1-10, higher = more urgent)  "backoff_base": 2,

  "priority": 8

### 2. Start Workers}

```

**Start Single Worker:**

```powershell---

python queuectl.py worker start

```## Architecture



**Output:**```

```User Commands (queuectl.py)

Started worker 'worker-1' (PID: 12345)         │

Started 1 worker(s)         ├──> Storage (SQLite Database)

```         │    └─> ~/.queuectl/data/queuectl.db

         │

**Start Multiple Workers:**         └──> Worker Manager

```powershell              └─> Worker Processes

python queuectl.py worker start --count 3                  ├─> Worker 1 (acquires jobs)

```                  ├─> Worker 2 (acquires jobs)

                  └─> Worker N (acquires jobs)

**Output:**```

```

Started worker 'worker-1' (PID: 12345)### Job Lifecycle

Started worker-2' (PID: 12346)

Started worker 'worker-3' (PID: 12347)```

Started 3 worker(s)Pending -> Processing -> Completed

```                      -> Failed -> Pending (retry)

                              -> Dead (DLQ) after max retries

### 3. Monitor Jobs```



**Check System Status:**### Exponential Backoff

```powershell

python queuectl.py status**Formula:** `delay = backoff_base ^ attempts` seconds

```

**Example** (backoff_base=2, max_retries=3):

**Output:**1. Attempt 1 fails - Wait 2^1 = 2 seconds

```2. Attempt 2 fails - Wait 2^2 = 4 seconds  

==================================================3. Attempt 3 fails - Wait 2^3 = 8 seconds

  QueueCTL Status4. Move to DLQ (max_retries reached)

==================================================

---

Total Jobs:          5

## Database Persistence

Jobs by State:

  Pending:           2- **Location:** `C:\Users\<YourName>\.queuectl\data\queuectl.db`

  Processing:        1- **Technology:** SQLite with WAL mode

  Completed:         2- **Survives:** System restarts, terminal closures, worker crashes

  Failed:            0

  Dead (DLQ):        0To verify persistence:

1. Enqueue jobs

Workers:2. Close terminal

  Active Processes:  23. Reopen and run `python queuectl.py list` - jobs still there!

  Currently Working: 1 jobs

==================================================---

```

## Testing

**List All Jobs:**

```powershellRun the automated test suite:

python queuectl.py list

``````powershell

.\venv\Scripts\Activate.ps1

**Output:**python test.py

``````

ID    Command       State      Attempts    Priority  Wait  Effective  Created At

----  ------------  ---------  ----------  --------  ----  ---------  -------------------Tests cover:

job3  echo Task     completed  0/3         8         0     8          2025-11-09 10:15:23- Basic job completion

job1  echo Hello    completed  0/3         5         0     5          2025-11-09 10:14:12- Failed job retry and DLQ

job2  timeout 30    pending    0/3         5         2     7          2025-11-09 10:14:50- Multiple workers (no overlap)

- Job persistence

Total: 3 job(s)- Invalid command handling

```

---

**Filter by State:**

```powershell## Troubleshooting

python queuectl.py list --state pending

python queuectl.py list --state completed### Issue: "Cannot find python"

python queuectl.py list --state failed**Solution:** Make sure virtual environment is activated:

``````powershell

.\venv\Scripts\Activate.ps1

**View Job Details:**```

```powershell

python queuectl.py show job1### Issue: "Workers not processing jobs"

```**Solution:** Check if workers are running:

```powershell

**Output:**python queuectl.py status

``````

============================================================

  Job: job1### Issue: "Jobs stuck in processing"

============================================================**Solution:** Restart workers:

Command:      echo Hello World```powershell

State:        completedpython queuectl.py worker stop

Attempts:     0/3python queuectl.py worker start --count 2

Priority:     5```

Waiting Time: 0

Effective:    5 (priority + waiting_time)### Issue: "Database locked"

Timeout:      20s**Solution:** Stop all workers and try again:

Created:      2025-11-09T10:14:12.123456```powershell

Updated:      2025-11-09T10:14:15.789012python queuectl.py worker stop

timeout 2

Output:python queuectl.py status

Hello World```

============================================================

```---



### 4. Dead Letter Queue (DLQ)## Project Structure



**List Failed Jobs in DLQ:**```

```powershellQueueCTL/

python queuectl.py dlq list├── queuectl/

```│   ├── __init__.py         # Package initialization

│   ├── schema.sql          # Database schema

**Output:**│   ├── storage.py          # Storage layer (SQLite)

```│   ├── worker.py           # Worker logic

ID    Command       Attempts  Error                     Failed At│   └── worker_manager.py   # Worker process management

----  ----------    --------  ------------------------  -------------------├── queuectl.py             # Main CLI entry point

job2  timeout 30    3         Exit code 1: Timeout...   2025-11-09 10:20:15├── test.py                 # Automated test suite

├── requirements.txt        # Python dependencies

Total: 1 job(s) in DLQ├── setup.ps1               # Setup script

```├── .gitignore              # Git ignore patterns

└── README.md               # This file

**Retry a Job from DLQ:**```

```powershell

python queuectl.py dlq retry job2---

```

## Requirements

**Output:**

```- **Python:** 3.8 or higher

Job 'job2' moved back to pending queue- **OS:** Windows 10/11

```- **Dependencies:** click, tabulate (auto-installed by setup.ps1)



### 5. Worker Management---



**Stop All Workers:**## License

```powershell

python queuectl.py worker stopMIT License

```

---

**Output:**

```## Author

Stopped worker 'worker-1' (PID: 12345)

Stopped worker 'worker-2' (PID: 12346)Built for the QueueCTL Backend Developer Internship Assignment.

Stopped 2 worker(s)

```For issues, check the Troubleshooting section or review the code.


### 6. Configuration Management

**View Configuration:**
```powershell
python queuectl.py config get max-retries
```

**Output:**
```
max-retries = 3
```

**Update Configuration:**
```powershell
python queuectl.py config set max-retries 5
python queuectl.py config set backoff-base 3
```

### 7. Remove Jobs

**Remove Specific Job:**
```powershell
python queuectl.py dequeue job3
```

**Output:**
```
Job 'job3' removed from queue
```

**Clear All Jobs (Testing):**
```powershell
python queuectl.py clear --yes
```

---

## Architecture Overview

### System Components

```
┌─────────────┐
│   CLI       │  (queuectl.py)
│  Interface  │  User commands
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Storage   │  (storage.py)
│    Layer    │  SQLite operations
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  SQLite DB  │  (queuectl.db)
│  WAL Mode   │  Persistent storage
└─────────────┘
       ▲
       │
┌──────┴──────┐
│   Worker    │  (worker.py)
│  Processes  │  Job execution
└─────────────┘
       ▲
       │
┌──────┴──────┐
│   Worker    │  (worker_manager.py)
│   Manager   │  Process lifecycle
└─────────────┘
```

### Job Lifecycle

```
                    ┌─────────────┐
                    │   PENDING   │ ← New job enqueued
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ PROCESSING  │ ← Worker acquires job
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
         ┌─────────────┐       ┌─────────────┐
         │  COMPLETED  │       │   FAILED    │ ← Timeout/Error
         └─────────────┘       └──────┬──────┘
                                      │
                           ┌──────────┴──────────┐
                           │                     │
                           ▼                     ▼
                    ┌─────────────┐       ┌─────────────┐
                    │   PENDING   │       │    DEAD     │
                    │   (retry)   │       │    (DLQ)    │
                    └─────────────┘       └─────────────┘
                         │                       ▲
                         └───(max retries)───────┘
```

### Job States

- **pending**: Job is queued, waiting for a worker
- **processing**: Job is currently being executed by a worker
- **completed**: Job finished successfully
- **failed**: Job failed but will be retried (with backoff delay)
- **dead**: Job exhausted all retries, moved to Dead Letter Queue

### Data Persistence

**Database Technology:** SQLite with WAL (Write-Ahead Logging) mode

**Why SQLite?**
- Single-file database (easy deployment)
- ACID compliance (atomic operations)
- No separate server process required
- Built-in Python support
- WAL mode enables concurrent readers

**Schema Overview:**

**jobs table:**
```sql
- id (TEXT PRIMARY KEY)           -- Unique job identifier
- command (TEXT)                  -- Shell command to execute
- state (TEXT)                    -- Job state (pending/processing/etc.)
- attempts (INTEGER)              -- Number of execution attempts
- max_retries (INTEGER)           -- Maximum retry limit
- timeout (INTEGER)               -- Execution timeout in seconds
- backoff_base (INTEGER)          -- Base for exponential backoff
- priority (INTEGER)              -- Job priority (1-10)
- waiting_time (INTEGER)          -- Incremented when new jobs enqueue
- created_at (DATETIME)           -- Job creation timestamp
- updated_at (DATETIME)           -- Last update timestamp
- next_retry_at (DATETIME)        -- When to retry failed job
- error_message (TEXT)            -- Error details if failed
- output (TEXT)                   -- Command stdout/stderr
- locked_by (TEXT)                -- Worker ID that acquired job
- locked_at (DATETIME)            -- When job was locked
```

**config table:**
```sql
- key (TEXT PRIMARY KEY)          -- Configuration key
- value (TEXT)                    -- Configuration value
```

### Worker Logic

**Worker Process Flow:**

1. **Initialization**
   - Worker gets unique ID
   - Connects to database
   - Sets up signal handlers (SIGINT/SIGTERM)

2. **Job Acquisition Loop** (every 1 second)
   - Query for pending/failed jobs ready for retry
   - Order by effective priority: `priority + waiting_time` (DESC)
   - Atomically lock job with worker ID
   - If no job available, wait and retry

3. **Job Execution**
   - Run command via subprocess with timeout
   - Capture stdout and stderr
   - Monitor for timeout or errors

4. **Result Handling**
   - **Success**: Mark job as completed, store output
   - **Failure**: Increment attempts, calculate backoff delay
     - If `attempts < max_retries`: Schedule retry
     - If `attempts >= max_retries`: Move to DLQ (dead state)

5. **Graceful Shutdown**
   - On SIGINT/SIGTERM, finish current job
   - Release locks and exit cleanly

**Race Condition Prevention:**

Jobs are locked atomically using SQL:
```sql
UPDATE jobs
SET state = 'processing', locked_by = ?, locked_at = ?
WHERE id = ? AND locked_by IS NULL
```

Only one worker can successfully lock a job due to the `locked_by IS NULL` condition.

### Exponential Backoff

**Formula:** `delay = backoff_base ^ attempts` seconds

**Example** (backoff_base=2, max_retries=3):
1. Attempt 1 fails - Wait 2^1 = 2 seconds
2. Attempt 2 fails - Wait 2^2 = 4 seconds  
3. Attempt 3 fails - Wait 2^3 = 8 seconds
4. Move to DLQ (max_retries reached)

**Benefits:**
- Reduces system load from rapid retries
- Gives time for transient issues to resolve
- Prevents thundering herd problem

### Priority Queue with Waiting Time

**Effective Priority Calculation:**
```
effective_priority = priority + waiting_time
```

**Behavior:**
- When a new job is enqueued, all pending jobs have `waiting_time` incremented by 1
- Workers select jobs by highest effective priority
- Prevents starvation: low-priority jobs eventually get high effective priority

**Example:**
```
Time 0: Enqueue job1 (priority=3, waiting_time=0, effective=3)
Time 1: Enqueue job2 (priority=5, waiting_time=0, effective=5)
        - job1 now has waiting_time=1, effective=4
Time 2: Enqueue job3 (priority=4, waiting_time=0, effective=4)
        - job1 now has waiting_time=2, effective=5
        - job2 now has waiting_time=1, effective=6

Worker selects: job2 (effective=6) first
```

### Worker Process Management

**Windows-Specific Implementation:**

Workers run as detached background processes using:
```python
subprocess.Popen(
    [python_exe, worker_script, worker_id],
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
)
```

**Flags:**
- `DETACHED_PROCESS`: Process not attached to parent console
- `CREATE_NEW_PROCESS_GROUP`: Independent process group
- `CREATE_NO_WINDOW`: No console window created

**Worker Tracking:**
- Active workers stored in `workers.json`
- Tracks worker_id and PID
- Manager uses `tasklist` to verify process existence
- Manager uses `taskkill` to stop workers

---

## Assumptions & Trade-offs

### Assumptions

1. **Single Machine Deployment**
   - System designed for single Windows machine
   - Not distributed across multiple servers
   - SQLite sufficient for local persistence

2. **Command Execution Environment**
   - Commands run in PowerShell/CMD context
   - Worker has same permissions as user
   - No sandboxing or security isolation

3. **Moderate Job Volume**
   - Designed for hundreds to thousands of jobs
   - Not optimized for millions of jobs
   - Single SQLite database file handles load

4. **Network Not Required**
   - All components run locally
   - No network communication between components
   - No remote worker nodes

5. **Job Commands are Trusted**
   - No input sanitization on commands
   - User responsible for command safety
   - No command injection protection

### Trade-offs

#### 1. **SQLite vs. Redis/PostgreSQL**

**Choice:** SQLite

**Pros:**
- Zero configuration (no server setup)
- Single file database (easy backup)
- Built into Python standard library
- ACID compliance
- Perfect for local deployments

**Cons:**
- Limited concurrent writes
- Not suitable for distributed systems
- No network access
- Limited scalability compared to Redis

**Rationale:** For a local Windows job queue, SQLite provides the best balance of simplicity and reliability. Redis would add unnecessary complexity for a single-machine system.

#### 2. **Polling vs. Event-Driven Architecture**

**Choice:** Polling (1-second interval)

**Pros:**
- Simple implementation
- No complex event handling
- Easy to debug
- Works reliably on Windows

**Cons:**
- 1-second delay before job pickup
- Constant CPU wake-ups
- Not real-time

**Rationale:** Polling is simpler and more reliable than Windows event mechanisms. 1-second delay is acceptable for background job processing.

#### 3. **Process-Based Workers vs. Thread-Based**

**Choice:** Separate processes

**Pros:**
- True parallelism (no GIL issues)
- Isolation (crash doesn't affect others)
- Can be monitored/killed independently
- Survives parent process crashes

**Cons:**
- Higher memory overhead
- More complex IPC (through database)
- Process creation overhead

**Rationale:** Process isolation is critical for reliability. Jobs may crash or hang, so isolating them in separate processes prevents cascading failures.

#### 4. **Priority + Waiting Time vs. Simple Priority**

**Choice:** Combined priority system

**Pros:**
- Prevents starvation of low-priority jobs
- Fair scheduling over time
- Automatic priority boost for waiting jobs

**Cons:**
- More complex query logic
- Increment overhead on enqueue
- Harder to predict exact execution order

**Rationale:** Pure priority queues can starve low-priority jobs indefinitely. The waiting_time mechanism ensures all jobs eventually execute.

#### 5. **Synchronous Command Execution vs. Async**

**Choice:** Synchronous subprocess execution

**Pros:**
- Simple implementation
- Easy timeout handling
- Straightforward error capture
- No async complexity

**Cons:**
- Worker blocked during job execution
- Can't handle multiple jobs per worker
- Less efficient resource usage

**Rationale:** Each worker handles one job at a time for simplicity. Scale horizontally with more workers instead of async complexity.

#### 6. **Exponential Backoff vs. Fixed Delay**

**Choice:** Exponential backoff

**Pros:**
- Reduces load on failing systems
- More time for transient issues to resolve
- Industry best practice

**Cons:**
- Long delays after multiple failures
- May delay recovery unnecessarily

**Rationale:** Exponential backoff is the standard approach for retries and prevents overwhelming failing services.

#### 7. **WAL Mode vs. Default SQLite**

**Choice:** WAL (Write-Ahead Logging) mode

**Pros:**
- Concurrent readers don't block writers
- Better concurrency
- More resilient to crashes

**Cons:**
- Extra files created (db-wal, db-shm)
- Slightly more complex

**Rationale:** WAL mode is essential for multiple workers querying the database while jobs are being enqueued.

### Simplifications

1. **No Authentication/Authorization**
   - Any user on the machine can access the queue
   - No multi-user support
   - No permission checking

2. **No Job Dependencies**
   - Jobs execute independently
   - No DAG (Directed Acyclic Graph) support
   - No job chaining or workflows

3. **No Job Scheduling**
   - Jobs run as soon as workers are available
   - No cron-like scheduling
   - No delayed execution (except retry backoff)

4. **No Job Cancellation**
   - Running jobs cannot be interrupted
   - Only pending jobs can be removed
   - Must wait for timeout or completion

5. **No Resource Limits**
   - No memory or CPU constraints
   - No disk space monitoring
   - No worker count limits enforced

6. **Minimal Logging**
   - Basic stdout/stderr capture
   - No structured logging
   - No log rotation

### Known Limitations

1. **Command Output Size**
   - Large outputs stored in database
   - No streaming or pagination
   - May cause performance issues with huge outputs

2. **Worker Discovery**
   - Workers only discovered through workers.json
   - If file corrupted, workers "lost"
   - No self-healing mechanism

3. **Timeout Precision**
   - Timeout based on subprocess.run()
   - Not precise to the second
   - No guarantee of exact timeout

4. **Windows Only**
   - Process management Windows-specific
   - Path handling Windows-specific
   - No cross-platform support

---

## Testing Instructions

### Automated Test Suite

Run the complete test suite:

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run all tests
python test.py
```

**Expected Output:**
```
============================================================
  QueueCTL Test Suite (Windows)
============================================================

============================================================
TEST 1: Basic Job Completion
============================================================
[OK] Job enqueued
[OK] Worker started
[PASS] Job completed successfully!

============================================================
TEST 2: Job Retry and DLQ
============================================================
[OK] Job enqueued (will timeout)
[OK] Worker started
[INFO] Waiting for retries (~12 seconds)...
[PASS] Job moved to DLQ after retries!

============================================================
TEST 3: Multiple Workers
============================================================
[OK] 5 jobs enqueued
[OK] 2 workers started
[PASS] All jobs completed by multiple workers!

============================================================
TEST 4: Database Persistence
============================================================
[OK] Job enqueued
[PASS] Job persisted in database!

============================================================
TEST 5: Priority Queue
============================================================
[OK] Jobs enqueued (low priority first, then high)
[PASS] Priority queue working (high priority processed first)!

============================================================
TEST 6: Invalid Command Handling
============================================================
[OK] Job with invalid command enqueued
[OK] Worker started
[PASS] Invalid command failed gracefully and moved to DLQ!

============================================================
  Test Results
============================================================
Basic Job Completion: [PASSED]
Job Retry and DLQ: [PASSED]
Multiple Workers: [PASSED]
Database Persistence: [PASSED]
Priority Queue: [PASSED]
Invalid Command Handling: [PASSED]

Total: 6 passed, 0 failed

[SUCCESS] All tests passed!
```

### Test Coverage

| Test | Scenario | Validates |
|------|----------|-----------|
| **Test 1** | Basic Job Completion | Job enqueues, worker executes, marks completed |
| **Test 2** | Job Retry and DLQ | Failed job retries with backoff, moves to DLQ after max attempts |
| **Test 3** | Multiple Workers | Multiple workers process jobs concurrently without overlap (race-safe) |
| **Test 4** | Database Persistence | Jobs survive system restart, data persisted to disk |
| **Test 5** | Priority Queue | Higher priority jobs processed first |
| **Test 6** | Invalid Command | Invalid commands fail gracefully, don't crash system |

### Manual Testing

#### Test 1: Basic Workflow

```powershell
# Clear any existing data
python queuectl.py clear --yes

# Enqueue a simple job
python queuectl.py enqueue --id test1 --command "echo Testing QueueCTL"

# Verify job is pending
python queuectl.py list
# Should show test1 in pending state

# Start worker
python queuectl.py worker start

# Wait a moment
Start-Sleep -Seconds 2

# Check job completed
python queuectl.py show test1
# Should show state: completed with output "Testing QueueCTL"

# Stop worker
python queuectl.py worker stop
```

#### Test 2: Priority System

```powershell
# Clear queue
python queuectl.py clear --yes

# Enqueue low priority job first
python queuectl.py enqueue --id low --command "echo Low" --priority 2

# Enqueue medium priority
python queuectl.py enqueue --id med --command "echo Medium" --priority 5

# Enqueue high priority
python queuectl.py enqueue --id high --command "echo High" --priority 9

# View effective priorities (note waiting_time)
python queuectl.py list
# High priority should be listed first

# Start worker
python queuectl.py worker start

# Monitor which completes first
Start-Sleep -Seconds 3
python queuectl.py list
# High priority job should complete first

# Stop worker
python queuectl.py worker stop
```

#### Test 3: Retry Mechanism

```powershell
# Clear queue
python queuectl.py clear --yes

# Enqueue job that will timeout
python queuectl.py enqueue --id retry-test --command "timeout 30" --timeout 2 --max-retries 2

# Start worker
python queuectl.py worker start

# Monitor job attempts
Start-Sleep -Seconds 3
python queuectl.py show retry-test
# Should show attempts: 1/2 and state: failed

# Wait for second retry (2^1 = 2 seconds backoff)
Start-Sleep -Seconds 5
python queuectl.py show retry-test
# Should show attempts: 2/2

# Wait for move to DLQ (2^2 = 4 seconds backoff + execution)
Start-Sleep -Seconds 7
python queuectl.py dlq list
# Should show retry-test in DLQ

# Stop worker
python queuectl.py worker stop
```

#### Test 4: Multiple Workers

```powershell
# Clear queue
python queuectl.py clear --yes

# Enqueue multiple jobs
1..10 | ForEach-Object { python queuectl.py enqueue --id "job$_" --command "timeout 2" }

# Check status
python queuectl.py status
# Should show 10 pending jobs

# Start 3 workers
python queuectl.py worker start --count 3

# Monitor progress
Start-Sleep -Seconds 2
python queuectl.py status
# Should show 3 processing, rest pending

Start-Sleep -Seconds 3
python queuectl.py status
# Should show more completed

# Stop workers
python queuectl.py worker stop
```

#### Test 5: Persistence

```powershell
# Clear and enqueue job
python queuectl.py clear --yes
python queuectl.py enqueue --id persist --command "echo Persistent Job"

# Close terminal completely (simulate restart)
# Open new terminal, activate venv

# Check job still exists
python queuectl.py list
# Should show persist job still pending

# Start worker to complete it
python queuectl.py worker start
Start-Sleep -Seconds 2

# Verify completion persisted
python queuectl.py show persist
# Should show completed with output

# Stop worker
python queuectl.py worker stop
```

### Troubleshooting Tests

#### Issue: Tests Fail with "no such column"

**Cause:** Old database schema

**Solution:**
```powershell
Remove-Item -Force $HOME\.queuectl\data\queuectl.db*
python test.py
```

#### Issue: Workers Don't Process Jobs

**Cause:** Workers.json corrupted or workers crashed

**Solution:**
```powershell
# Stop all workers
python queuectl.py worker stop

# Manually kill any stuck Python processes
taskkill /F /IM python.exe

# Clear workers file
Remove-Item -Force $HOME\.queuectl\data\workers.json

# Start fresh
python queuectl.py worker start
```

#### Issue: Jobs Stuck in Processing

**Cause:** Worker crashed while processing

**Solution:**
```powershell
# Stop workers
python queuectl.py worker stop

# Manually reset stuck jobs in database
# Or clear and re-enqueue
python queuectl.py clear --yes
```

### Performance Benchmarks

Run performance test with 100 jobs:

```powershell
# Enqueue 100 jobs
1..100 | ForEach-Object { 
    python queuectl.py enqueue --id "perf$_" --command "echo Job $_"
}

# Time execution with 5 workers
$start = Get-Date
python queuectl.py worker start --count 5
Start-Sleep -Seconds 30
python queuectl.py worker stop
$duration = (Get-Date) - $start

# Check results
python queuectl.py status
Write-Output "Duration: $duration"
```

**Expected Performance:**
- Single worker: ~1-2 jobs/second (depends on command)
- 5 workers: ~5-10 jobs/second
- Database overhead: ~50-100ms per operation

---

## License

This project is provided as-is for educational and evaluation purposes.

---

## Support

For issues or questions:
1. Check the [Testing Instructions](#testing-instructions) section
2. Review [Troubleshooting Tests](#troubleshooting-tests)
3. Verify setup with `python queuectl.py --version`

---

**QueueCTL v1.0.0** - Built for Windows
