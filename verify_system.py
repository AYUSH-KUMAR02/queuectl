import os
import sys
import time
import json
import subprocess
from django.utils import timezone

def log(msg, symbol="[*]"):
    print(f"{symbol} {msg}")

def run_command(cmd_list):
    result = subprocess.run([sys.executable] + cmd_list, capture_output=True, text=True)
    return result.stdout, result.stderr

def main():
    log("Initializing automated integration verification suite...", "[+]")
    
    # Bootstrap Django environment configurations for data cleanup
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'queuectl.settings')
    try:
        import django
        django.setup()
        from queue_manager.models import Job, AppConfig
    except Exception as e:
        log(f"Failed to bootstrap Django environment directly: {e}", "[X]")
        sys.exit(1)

    # 1. Flush database state for fresh integration run
    log("Purging tracking database and configurations...")
    Job.objects.all().delete()
    AppConfig.objects.all().delete()

    # 2. Seed configuration values
    log("Configuring runtime overrides (backoff-base=2)...")
    run_command(["manage.py", "config", "set", "backoff-base", "2"])

    # 3. Ingest varying job patterns to validate paths
    log("Ingesting test job payload matrix...")
    
    # Job A: Guaranteed Success (Windows ping localhost acts as a cross-version sleep command)
    job_success = {
        "id": "verify_success_01",
        "command": "ping 127.0.0.1 -n 2",
        "max_retries": 3
    }
    # Job B: Guaranteed Failure (invalid command name ensures code exits with error)
    job_fail = {
        "id": "verify_fail_01",
        "command": "invalid_system_command_xyz",
        "max_retries": 1
    }
    
    run_command(["manage.py", "enqueue", json.dumps(job_success)])
    run_command(["manage.py", "enqueue", json.dumps(job_fail)])

    # 4. Bootstrap processing pool briefly
    log("Spawning active background worker pool for processing cycle (3 seconds)...")
    worker_proc = subprocess.Popen([sys.executable, "manage.py", "worker", "--count", "2"])
    
    # Allow the worker cluster enough runtime to process jobs and evaluate retries
    time.sleep(4.0)
    
    log("Sending termination signal to worker process pool...")
    worker_proc.terminate()
    try:
        worker_proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        worker_proc.kill()

    # 5. Extract system status outputs and compile report
    log("Compiling final diagnostic verification matrix...", "[+]")
    stdout, _ = run_command(["manage.py", "status"])
    print(stdout)

    # Double check underlying structures directly
    log("Detailed Database Record State Audit:")
    for j in Job.objects.all():
        print(f" -> Job ID: {j.id.ljust(18)} | State: {j.state.ljust(10)} | Attempts: {j.attempts}/{j.max_retries}")
        
    log("Integration script run complete. Verify that failure jobs transitioned to DEAD.", "[+]")

if __name__ == "__main__":
    main()