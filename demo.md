# QueueCTL - 2 Minute Demo Commands

## Setup
```powershell
cd D:\QueueCTL
python queuectl.py clear --yes
python queuectl.py worker stop 2>$null
```

---

## Terminal 1 

```powershell
# Enqueue jobs
python queuectl.py enqueue --id job1 --command "echo Hello"
python queuectl.py enqueue --id job2 --command "powershell -Command Start-Sleep -Seconds 30" --timeout 5 --max-retries 3 --backoff-base 2
python queuectl.py enqueue --id job3 --command "powershell -Command 'Start-Sleep -Seconds 3; Write-Output Done'" --timeout 10
python queuectl.py enqueue --id job4 --command "echo High Priority" --priority 8

# List jobs
python queuectl.py list

# Monitor execution
python queuectl.py status
python queuectl.py list
python queuectl.py dlq list

# Real-time demo
python queuectl.py clear --yes
python queuectl.py enqueue --id fast --command "echo Quick" --priority 5
python queuectl.py enqueue --id slow --command "powershell -Command 'Start-Sleep -Seconds 3; Write-Output Done'" --priority 8
python queuectl.py worker start --foreground

# After jobs complete (Ctrl+C)
python queuectl.py show slow
```

---

## Terminal 2 

```powershell
# Start background workers
python queuectl.py worker start --count 2

# Stop workers (after jobs complete)
python queuectl.py worker stop
```
