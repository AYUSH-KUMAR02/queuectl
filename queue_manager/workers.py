import time
import subprocess
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import Job, AppConfig
from .services import get_config_value

def fetch_and_lock_next_job():
    """
    Safely acquires the next eligible job (either pending or failed-retryable)
    whose scheduled runtime has arrived.
    """
    now = timezone.now()
    with transaction.atomic():
        # A job is eligible if it's pending OR if it failed but its backoff delay has passed
        job = Job.objects.filter(
            state__in=[Job.STATE_PENDING, Job.STATE_FAILED],
            run_at__lte=now
        ).order_by('created_at').select_for_update(skip_locked=True).first()
        
        if job:
            job.state = Job.STATE_PROCESSING
            job.attempts += 1
            job.updated_at = now
            job.save()
            return job
    return None

def handle_job_failure(job):
    """
    Implements backoff calculation logic or pushes permanently failed jobs to the DLQ.
    """
    now = timezone.now()
    
    if job.attempts > job.max_retries:
        print(f"[X] Job '{job.id}' reached max retries ({job.max_retries}). Moving to DLQ.")
        job.state = Job.STATE_DEAD
    else:
        # Fetch configurable backoff base from DB (defaulting to 2 seconds)
        backoff_base = get_config_value("backoff-base", 2)
        
        # Calculate delay using formula: base ^ attempts
        delay_seconds = backoff_base ** job.attempts
        job.state = Job.STATE_FAILED
        job.run_at = now + timedelta(seconds=delay_seconds)
        
        print(f"[*] Job '{job.id}' scheduled for retry in {delay_seconds}s (Attempt {job.attempts}/{job.max_retries})")
    
    job.updated_at = now
    job.save()

def execute_job_command(job):
    print(f"[*] Worker processing Job '{job.id}': Executing '{job.command}'...")
    try:
        result = subprocess.run(
            job.command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"[+] Job '{job.id}' completed successfully.")
            job.state = Job.STATE_COMPLETED
            job.updated_at = timezone.now()
            job.save()
        else:
            print(f"[-] Job '{job.id}' failed with exit code {result.returncode}.")
            handle_job_failure(job)
            
    except Exception as e:
        print(f"[-] Critical system exception executing job '{job.id}': {str(e)}")
        handle_job_failure(job)

def run_single_worker_loop(stop_event=None):
    print("[*] Worker polling engine initialized.")
    while True:
        if stop_event and stop_event.is_set():
            break
            
        job = fetch_and_lock_next_job()
        if job:
            execute_job_command(job)
        else:
            time.sleep(1)