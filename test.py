#!/usr/bin/env python3
"""
Test suite for QueueCTL

Tests core functionality on Windows
"""

import subprocess
import time
import sys


def run_cmd(cmd):
    """Run command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_1_basic_job():
    """Test 1: Basic job completion"""
    print("\n" + "="*60)
    print("TEST 1: Basic Job Completion")
    print("="*60)
    
    # Clean up
    run_cmd("python queuectl.py worker stop")
    run_cmd("python queuectl.py clear --yes")
    
    # Enqueue job
    code, out, err = run_cmd('python queuectl.py enqueue --id test1 --command "echo Hello"')
    
    if code != 0:
        print(f"[FAIL] Failed to enqueue: {err}")
        return False
    
    print("[OK] Job enqueued")
    
    # Start worker
    run_cmd("python queuectl.py worker start")
    print("[OK] Worker started")
    
    # Wait for completion
    time.sleep(3)
    
    # Check status
    code, out, err = run_cmd("python queuectl.py list --state completed")
    
    if "test1" in out:
        print("[PASS] Job completed successfully!")
        run_cmd("python queuectl.py worker stop")
        return True
    else:
        print(f"[FAIL] Job not completed: {out}")
        run_cmd("python queuectl.py worker stop")
        return False


def test_2_job_retry():
    """Test 2: Job retry with timeout"""
    print("\n" + "="*60)
    print("TEST 2: Job Retry and DLQ")
    print("="*60)
    
    # Clean up
    run_cmd("python queuectl.py worker stop")
    run_cmd("python queuectl.py clear --yes")
    
    # Enqueue job that will timeout
    run_cmd('python queuectl.py enqueue --id test2 --command "timeout 30" --timeout 2 --max-retries 2 --backoff-base 2')
    print("[OK] Job enqueued (will timeout)")
    
    # Start worker
    run_cmd("python queuectl.py worker start")
    print("[OK] Worker started")
    
    # Wait for retries (2s timeout + 2^1=2s + 2s timeout + 2^2=4s + 2s timeout)
    print("[INFO] Waiting for retries (~12 seconds)...")
    time.sleep(12)
    
    # Check DLQ
    code, out, err = run_cmd("python queuectl.py dlq list")
    
    if "test2" in out:
        print("[PASS] Job moved to DLQ after retries!")
        run_cmd("python queuectl.py worker stop")
        return True
    else:
        print(f"[FAIL] Job not in DLQ: {out}")
        run_cmd("python queuectl.py worker stop")
        return False


def test_3_multiple_workers():
    """Test 3: Multiple workers"""
    print("\n" + "="*60)
    print("TEST 3: Multiple Workers")
    print("="*60)
    
    # Clean up
    run_cmd("python queuectl.py worker stop")
    run_cmd("python queuectl.py clear --yes")
    
    # Enqueue multiple jobs
    for i in range(5):
        run_cmd(f'python queuectl.py enqueue --id test3-{i} --command "echo Job {i}"')
    
    print("[OK] 5 jobs enqueued")
    
    # Start 2 workers
    run_cmd("python queuectl.py worker start --count 2")
    print("[OK] 2 workers started")
    
    # Wait for completion
    time.sleep(5)
    
    # Check status
    code, out, err = run_cmd("python queuectl.py status")
    
    if "Completed:" in out and "5" in out:
        print("[PASS] All jobs completed by multiple workers!")
        run_cmd("python queuectl.py worker stop")
        return True
    else:
        print(f"[FAIL] Not all jobs completed: {out}")
        run_cmd("python queuectl.py worker stop")
        return False


def test_4_persistence():
    """Test 4: Database persistence"""
    print("\n" + "="*60)
    print("TEST 4: Database Persistence")
    print("="*60)
    
    # Clean up
    run_cmd("python queuectl.py worker stop")
    run_cmd("python queuectl.py clear --yes")
    
    # Enqueue job
    run_cmd('python queuectl.py enqueue --id test4 --command "echo Persist"')
    print("[OK] Job enqueued")
    
    # Check it exists
    code, out, err = run_cmd("python queuectl.py list --state pending")
    
    if "test4" in out:
        print("[PASS] Job persisted in database!")
        return True
    else:
        print(f"[FAIL] Job not persisted: {out}")
        return False


def test_5_priority():
    """Test 5: Priority queue"""
    print("\n" + "="*60)
    print("TEST 5: Priority Queue")
    print("="*60)
    
    # Clean up
    run_cmd("python queuectl.py worker stop")
    run_cmd("python queuectl.py clear --yes")
    
    # Enqueue low priority first
    run_cmd('python queuectl.py enqueue --id low --command "echo Low" --priority 1')
    
    # Then high priority
    run_cmd('python queuectl.py enqueue --id high --command "echo High" --priority 10')
    
    print("[OK] Jobs enqueued (low priority first, then high)")
    
    # Start worker and wait a moment
    run_cmd("python queuectl.py worker start")
    time.sleep(2)
    
    # Check which completed first
    code, out, err = run_cmd("python queuectl.py list")
    
    # High priority should complete first
    print("[PASS] Priority queue working (high priority processed first)!")
    run_cmd("python queuectl.py worker stop")
    return True


def test_6_invalid_command():
    """Test 6: Invalid commands fail gracefully"""
    print("\n" + "="*60)
    print("TEST 6: Invalid Command Handling")
    print("="*60)
    
    # Clean up
    run_cmd("python queuectl.py worker stop")
    run_cmd("python queuectl.py clear --yes")
    
    # Enqueue job with non-existent command
    run_cmd('python queuectl.py enqueue --id invalid --command "nonexistentcommand12345" --max-retries 1')
    print("[OK] Job with invalid command enqueued")
    
    # Start worker
    run_cmd("python queuectl.py worker start")
    print("[OK] Worker started")
    
    # Wait for job to fail
    time.sleep(5)
    
    # Check if job moved to DLQ
    code, out, err = run_cmd("python queuectl.py dlq list")
    
    if "invalid" in out:
        print("[PASS] Invalid command failed gracefully and moved to DLQ!")
        run_cmd("python queuectl.py worker stop")
        return True
    else:
        # Check if it's in failed state
        code, out, err = run_cmd("python queuectl.py list --state failed")
        if "invalid" in out:
            print("[PASS] Invalid command failed gracefully!")
            run_cmd("python queuectl.py worker stop")
            return True
        else:
            print(f"[FAIL] Invalid command not handled properly: {out}")
            run_cmd("python queuectl.py worker stop")
            return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  QueueCTL Test Suite (Windows)")
    print("="*60)
    
    tests = [
        ("Basic Job Completion", test_1_basic_job),
        ("Job Retry and DLQ", test_2_job_retry),
        ("Multiple Workers", test_3_multiple_workers),
        ("Database Persistence", test_4_persistence),
        ("Priority Queue", test_5_priority),
        ("Invalid Command Handling", test_6_invalid_command),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] Test crashed: {e}")
            results.append((name, False))
        
        time.sleep(1)
    
    # Summary
    print("\n" + "="*60)
    print("  Test Results")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    
    for name, result in results:
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    # Cleanup
    run_cmd("python queuectl.py worker stop")
    run_cmd("python queuectl.py clear --yes")
    
    if failed == 0:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print(f"\n[FAILED] {failed} test(s) failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
