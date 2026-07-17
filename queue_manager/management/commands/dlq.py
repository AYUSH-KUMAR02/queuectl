from django.core.management.base import BaseCommand
from django.utils import timezone
from queue_manager.models import Job

class Command(BaseCommand):
    help = "Manages administrative actions (list / retry) over the Dead Letter Queue."

    def add_arguments(self, parser):
        parser.add_argument('action', type=str, choices=['list', 'retry'], help="Action to run: list or retry")
        parser.add_argument('job_id', type=str, nargs='?', default=None, help="Job ID target requirement if running retry action")

    def handle(self, *args, **options):
        action = options['action']
        job_id = options['job_id']

        if action == 'list':
            dead_jobs = Job.objects.filter(state=Job.STATE_DEAD)
            if not dead_jobs.exists():
                self.stdout.write(self.style.SUCCESS("[+] Dead Letter Queue (DLQ) is completely empty."))
                return
            
            self.stdout.write(self.style.ERROR("\n=== Dead Letter Queue (DLQ) Items ==="))
            for job in dead_jobs:
                self.stdout.write(f" ID: {job.id} | Command: {job.command} | Max Retries: {job.max_retries}")
                
        elif action == 'retry':
            if not job_id:
                self.stdout.write(self.style.ERROR("[X] Error: Specifying a valid target job_id string is required for retry actions."))
                return
            
            try:
                job = Job.objects.get(id=job_id, state=Job.STATE_DEAD)
                job.state = Job.STATE_PENDING
                job.attempts = 0
                job.run_at = timezone.now()
                job.save()
                self.stdout.write(self.style.SUCCESS(f"[+] Re-enqueued job '{job.id}' out of DLQ back to active queue execution."))
            except Job.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"[X] Error: Target job '{job_id}' not found inside the Dead Letter Queue Context."))