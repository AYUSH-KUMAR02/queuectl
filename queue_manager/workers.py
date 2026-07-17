import os
import time
import subprocess
from datetime import timedelta
import django

def init_worker_process():
    """
    Safely sets up Django's runtime framework inside newly spawned 
    Windows processes before any models are evaluated.
    """
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'queuectl.settings')
    django.setup()

def fetch_and_lock_next_job():
    from .models import Job
    from django.db import transaction
    from django.utils import timezone

    now = timezone.now()
    with transaction.atomic():
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
    from .models import Job
    from .services import get_config_value
    from django.utils import timezone

    now = timezone.now()
    if job.attempts > job.max_retries:
        print(f"[X] Job '{job.id}' reached max retries ({job.max_retries}). Moving to DLQ.")
        job.state = Job.STATE_DEAD
    else:
        backoff_base = get_config_value("backoff-base", 2)
        delay_seconds = backoff_base ** job.attempts
        job.state = Job.STATE_FAILED
        job.run_at = now + timedelta(seconds=delay_seconds)
        print(f"[*] Job '{job.id}' scheduled for retry in {delay_seconds}s (Attempt {job.attempts}/{job.max_retries})")
    
    job.updated_at = now
    job.save()

def execute_job_command(job):
    # FIXED: Added local Job import here so job.save() doesn't throw a NameError on success
    from .models import Job
    from django.utils import timezone

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
    init_worker_process()
    
    print("[*] Worker polling engine initialized and ready.")
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
                
            try:
                job = fetch_and_lock_next_job()
                if job:
                    execute_job_command(job)
                else:
                    time.sleep(1)
            except Exception as db_err:
                # Safeguard against transient database file locks
                time.sleep(0.5)
    except KeyboardInterrupt:
        # Catch Windows-level broad terminal interrupts to exit cleanly
        pass