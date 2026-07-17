import time
import subprocess
from django.db import transaction
from django.utils import timezone
from .models import Job

def fetch_and_lock_next_job():
    """
    Uses atomic transactions and row-level locking to safely acquire 
    the next available pending job without race conditions.
    """
    with transaction.atomic():
        # Select the oldest pending job that isn't currently locked by another worker
        job = Job.objects.filter(
            state=Job.STATE_PENDING
        ).order_by('created_at').select_for_update(skip_locked=True).first()
        
        if job:
            job.state = Job.STATE_PROCESSING
            job.attempts += 1
            job.updated_at = timezone.now()
            job.save()
            return job
    return None

def execute_job_command(job):
    """
    Executes the command string safely inside a native OS shell wrapper,
    capturing success or failure from the process return code.
    """
    print(f"[*] Worker processing Job '{job.id}': Executing '{job.command}'...")
    
    try:
        # Run command via shell to natively handle primitives like 'echo' or 'sleep'
        result = subprocess.run(
            job.command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"[+] Job '{job.id}' completed successfully.")
            job.state = Job.STATE_COMPLETED
        else:
            print(f"[-] Job '{job.id}' failed with exit code {result.returncode}.")
            print(f"[!] Stderr: {result.stderr.strip()}")
            job.state = Job.STATE_FAILED
            
    except Exception as e:
        print(f"[-] Critical system exception executing job '{job.id}': {str(e)}")
        job.state = Job.STATE_FAILED

    job.updated_at = timezone.now()
    job.save()
    return job

def run_single_worker_loop(stop_event=None):
    """
    Runs a continuous execution loop for a single worker thread/process.
    """
    print("[*] Worker polling engine initialized.")
    while True:
        # Graceful check for external multi-process shutdown loops (expanded in Commit 6)
        if stop_event and stop_event.is_set():
            break
            
        job = fetch_and_lock_next_job()
        
        if job:
            execute_job_command(job)
        else:
            # Idle sleep poll to save CPU cycles when queue is empty
            time.sleep(1)