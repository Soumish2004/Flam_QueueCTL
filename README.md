# QueueCTL - CLI-Based Background Job Queue System

A Windows-native job queue system with worker processes, automatic retries with exponential backoff, and Dead Letter Queue (DLQ) for permanently failed jobs.

**Platform:** Windows Only

---

📺 **[QueueCTL Demo Video](https://drive.google.com/file/d/1-JknvUK10GXpTTq_HFYbLStj2N9pK8RR/view?usp=sharing)**

---

## Features

- **Enqueue Jobs** - Add background jobs to persistent SQLite queue  
- **Multiple Workers** - Run concurrent worker processes  
- **Retry Mechanism** - Automatic retries with exponential backoff  
- **Dead Letter Queue (DLQ)** - Track permanently failed jobs  
- **Persistent Storage** - SQLite database survives restarts  
- **Worker Management** - Start/stop workers gracefully  
- **Job States** - Pending, processing, completed, failed, dead  
- **Configuration** - Manage retry and backoff settings  
- **Race-Safe** - Atomic job locking prevents duplicate execution  
- **Priority Queues** - Jobs with priority 1-10 (higher = more urgent)
- **Real-time Monitoring** - Foreground worker mode with execution timing

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Command Reference](#command-reference)
- [Architecture Overview](#architecture-overview)
- [Testing](#testing)
- [Building Executable](#building-executable)

---

## Prerequisites

- Python 3.8 or higher
- Windows OS (PowerShell)
- pip (Python package manager)

---

## Installation

```powershell
# Clone the repository
git clone https://github.com/Soumish2004/Flam_QueueCTL.git
cd Flam_QueueCTL

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

### 1. Enqueue Jobs

```powershell
# Simple job
python queuectl.py enqueue --id job1 --command "echo Hello World"

# Job with timeout and retries
python queuectl.py enqueue --id job2 --command "powershell -Command Start-Sleep -Seconds 2" --timeout 5 --max-retries 3

# High priority job
python queuectl.py enqueue --id job3 --command "echo Priority Task" --priority 8
```

### 2. Start Workers

```powershell
# Start 2 background workers
python queuectl.py worker start --count 2

# OR start 1 worker in foreground (real-time output)
python queuectl.py worker start --foreground
```

### 3. Monitor Progress

```powershell
# Check system status
python queuectl.py status

# List all jobs
python queuectl.py list

# Show specific job details
python queuectl.py show job1
```

### 4. Stop Workers

```powershell
python queuectl.py worker stop
```

---

## Usage Examples

### Enqueue Jobs

**Basic Job:**
```powershell
python queuectl.py enqueue --id job1 --command "echo Hello World"
```

**Output:**
```
Job 'job1' enqueued successfully
```

**Job with Custom Settings:**
```powershell
python queuectl.py enqueue --id job2 --command "timeout 30" --timeout 5 --max-retries 3 --backoff-base 2 --priority 8
```

**Available Options:**
- `--id` (required): Unique job identifier
- `--command` (required): Shell command to execute  
- `--timeout` (default: 20): Execution timeout in seconds  
- `--max-retries` (default: 3): Maximum retry attempts  
- `--backoff-base` (default: 2): Base for exponential backoff  
- `--priority` (default: 5): Priority level (1-10, higher = more urgent)

### Start Workers

**Background Workers (Multiple):**
```powershell
# Start 3 workers
python queuectl.py worker start --count 3
```

**Output:**
```
Started 3 worker(s)
Worker PIDs: [12345, 12346, 12347]
```

**Foreground Worker (Real-time Output):**
```powershell
# Start 1 worker with live output
python queuectl.py worker start --foreground
```

**Output:**
```
======================================================================
[worker-abc123] WORKER STARTED
  PID:       45678
  Timestamp: 2025-11-09 10:30:15
======================================================================

======================================================================
[worker-abc123] JOB STARTED
  Job ID:    job1
  Command:   echo Hello World
  Priority:  5
  Attempt:   1/3
  Timeout:   20s
  Started:   2025-11-09 10:30:20
======================================================================

======================================================================
[worker-abc123] JOB COMPLETED SUCCESSFULLY
  Job ID:         job1
  Execution Time: 0.234s
  Exit Code:      0
======================================================================
```

### Monitor Jobs

**Check Status:**
```powershell
python queuectl.py status
```

**Output:**
```
QueueCTL System Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Metric               Value
───────────────────  ─────
Total Jobs           10
Pending              3
Processing           2
Completed            4
Failed               1
Dead (DLQ)           0
Workers              2
Database             ~/.queuectl/data/queuectl.db
```

**List Jobs:**
```powershell
# List all jobs
python queuectl.py list

# List by state
python queuectl.py list --state pending
python queuectl.py list --state completed
python queuectl.py list --state failed
```

**Show Job Details:**
```powershell
python queuectl.py show job1
```

**Output:**
```
Job Details: job1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Field              Value
─────────────────  ─────────────────────────────
ID                 job1
Command            echo Hello World
State              completed
Priority           5
Timeout            20
Max Retries        3
Backoff Base       2
Attempts           1
Exec Time          0.234s
Created            2025-11-09 10:30:15
Started            2025-11-09 10:30:20
Finished           2025-11-09 10:30:20
Output             Hello World
```

### Dead Letter Queue (DLQ)

**List Failed Jobs:**
```powershell
python queuectl.py dlq list
```

**Output:**
```
Dead Letter Queue (DLQ)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Job ID    Command           Attempts  Last Error
────────  ────────────────  ────────  ─────────────────────
job2      timeout 30        3         Timeout exceeded (5s)
```

**Retry a Failed Job:**
```powershell
# Retry with original settings
python queuectl.py dlq retry job2

# Retry with increased timeout
python queuectl.py dlq retry job2 --timeout 60
```

**Clear DLQ:**
```powershell
python queuectl.py dlq clear --yes
```

### Configuration

**View Current Configuration:**
```powershell
python queuectl.py config get max_retries
python queuectl.py config get backoff_base
```

**Update Configuration:**
```powershell
python queuectl.py config set max_retries 5
python queuectl.py config set backoff_base 3
```

**View All Settings:**
```powershell
python queuectl.py config get
```

### Clear All Jobs

```powershell
# Interactive confirmation
python queuectl.py clear

# Skip confirmation
python queuectl.py clear --yes
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `python queuectl.py enqueue --id ID --command CMD` | Add a new job |
| `python queuectl.py worker start` | Start 1 worker |
| `python queuectl.py worker start --count N` | Start N workers |
| `python queuectl.py worker start --foreground` | Start 1 worker with real-time output |
| `python queuectl.py worker stop` | Stop all workers |
| `python queuectl.py status` | View system status |
| `python queuectl.py list` | List all jobs |
| `python queuectl.py list --state STATE` | List jobs by state |
| `python queuectl.py show JOB_ID` | Show job details |
| `python queuectl.py dlq list` | List failed jobs in DLQ |
| `python queuectl.py dlq retry JOB_ID` | Retry a DLQ job |
| `python queuectl.py dlq clear` | Clear all DLQ jobs |
| `python queuectl.py config set KEY VALUE` | Set configuration |
| `python queuectl.py config get KEY` | Get configuration |
| `python queuectl.py clear --yes` | Clear all jobs |

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         QueueCTL                            │
│                                                             │
│  ┌──────────────┐     ┌──────────────┐    ┌─────────────┐ │
│  │   CLI        │────▶│   Storage    │◀───│   Worker    │ │
│  │ (queuectl.py)│     │ (storage.py) │    │ (worker.py) │ │
│  └──────────────┘     └──────────────┘    └─────────────┘ │
│         │                     │                    │        │
│         └─────────────────────┼────────────────────┘        │
│                               │                             │
│                        ┌──────▼──────┐                      │
│                        │   SQLite    │                      │
│                        │  Database   │                      │
│                        └─────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Job Lifecycle

```
pending ──▶ processing ──▶ completed
   │            │
   │            ├─────▶ failed ──▶ pending (retry)
   │            │
   │            └─────▶ dead (max retries exceeded)
   │
   └──────────────────▶ dead (manual clear)
```

### Priority Queue System

Jobs are selected based on **effective priority**:

```
effective_priority = priority + waiting_time
```

- **priority**: User-defined priority (1-10, higher = more urgent)
- **waiting_time**: Seconds waiting in queue / 60 (anti-starvation)

**Example:**
- Job A: priority=8, waiting=0s → effective=8.0
- Job B: priority=5, waiting=180s → effective=8.0 (5 + 3)
- Both have equal effective priority, selected by creation time

### Worker Management

- **Background Mode**: Detached worker processes
  - Multiple workers supported (`--count N`)
  - Managed by `WorkerManager`
  - PIDs tracked in `workers.json`
  - Runs independently of terminal

- **Foreground Mode**: Interactive worker process
  - Single worker only (`--foreground`)
  - Real-time output in current terminal
  - Displays execution timing
  - Ctrl+C to stop

### Retry Logic

Failed jobs are retried with **exponential backoff**:

```
delay = backoff_base ^ attempts

Example (backoff_base=2):
- Attempt 1: immediate
- Attempt 2: 2^1 = 2 seconds
- Attempt 3: 2^2 = 4 seconds
- Attempt 4: 2^3 = 8 seconds
```

After `max_retries` attempts, job moves to **Dead Letter Queue (DLQ)**.

### Race Condition Prevention

Jobs are locked atomically using SQL:

```sql
UPDATE jobs 
SET state='processing', locked_at=CURRENT_TIMESTAMP 
WHERE id IN (
  SELECT id FROM jobs 
  WHERE state='pending' 
  ORDER BY priority DESC, created_at ASC 
  LIMIT 1
)
AND state='pending'
```

Only one worker can lock a job, preventing duplicate execution.

---

## Project Structure

```
QueueCTL/
├── queuectl/
│   ├── __init__.py          # Package initialization
│   ├── schema.sql           # Database schema
│   ├── storage.py           # Database operations
│   ├── worker.py            # Job execution worker
│   └── worker_manager.py    # Worker process management
├── queuectl.py              # Main CLI entry point
├── requirements.txt         # Python dependencies
├── test.py                  # Test suite
├── README.md                # Documentation
├── ARCHITECTURE.md          # Architecture details
├── REALTIME_FEATURE.md      # Real-time monitoring docs
├── BUILD_EXE.md             # Building executable guide
└── DEMO_2MIN.md             # Quick demo commands
```

### Data Location

- **Database:** `C:\Users\<YourName>\.queuectl\data\queuectl.db`
- **Worker Tracking:** `C:\Users\<YourName>\.queuectl\data\workers.json`

---

## Testing

### Run Automated Tests

```powershell
python test.py
```

**Test Coverage:**
1. ✅ Enqueue and dequeue jobs
2. ✅ Worker processes execute jobs
3. ✅ Retry mechanism with exponential backoff
4. ✅ Dead Letter Queue after max retries
5. ✅ Priority queue ordering
6. ✅ Waiting time anti-starvation

**Expected Output:**
```
Test 1: Enqueue and dequeue job...................... PASS
Test 2: Worker execution............................. PASS
Test 3: Job timeout and retry........................ PASS
Test 4: Dead Letter Queue (DLQ)...................... PASS
Test 5: Priority queue ordering...................... PASS
Test 6: Waiting time increases effective priority.... PASS

All 6 tests passed!
```

### Manual Testing

See **[DEMO_2MIN.md](DEMO_2MIN.md)** for a complete demo script.

---

## Building Executable

To compile QueueCTL into a standalone `.exe` file:

```powershell
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --add-data "queuectl\schema.sql;queuectl" --name queuectl queuectl.py
```

**Output:** `dist\queuectl.exe`

For detailed instructions, see **[BUILD_EXE.md](BUILD_EXE.md)**.

---

## Troubleshooting

### Issue: "Module not found"

**Solution:** Install dependencies:
```powershell
pip install -r requirements.txt
```

### Issue: Workers not starting

**Solution:** Check if workers are already running:
```powershell
python queuectl.py status
python queuectl.py worker stop
```

### Issue: Jobs stuck in "processing"

**Solution:** Clear stale locks (if worker crashed):
```powershell
# Stop all workers first
python queuectl.py worker stop

# Then clear database
python queuectl.py clear --yes
```

---

## System Requirements

- **OS:** Windows 10/11
- **Python:** 3.8 or higher
- **Dependencies:** click, tabulate (installed via `pip install -r requirements.txt`)
- **Disk Space:** ~10MB for database (grows with job history)

---

## Configuration Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| `max_retries` | 5 | Maximum retry attempts |
| `backoff_base` | 3 | Exponential backoff base |
| `timeout` | 20 | Default job timeout (seconds) |
| `priority` | 1 | Default job priority (1-10) |

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed architecture documentation
- **[REALTIME_FEATURE.md](REALTIME_FEATURE.md)** - Real-time monitoring feature guide
- **[BUILD_EXE.md](BUILD_EXE.md)** - Building executable instructions
- **[DEMO_2MIN.md](DEMO_2MIN.md)** - Quick 2-minute demo commands
