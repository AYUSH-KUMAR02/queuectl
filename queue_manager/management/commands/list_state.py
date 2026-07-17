from django.core.management.base import BaseCommand
from queue_manager.models import Job

class Command(BaseCommand):
    help = "Lists detailed records filtered by their explicit lifecycle execution state."

    def add_arguments(self, parser):
        parser.add_argument('state', type=str, help="Target state: pending, processing, completed, failed, dead")

    def handle(self, *args, **options):
        state = options['state'].lower()
        jobs = Job.objects.filter(state=state).order_by('created_at')
        
        if not jobs.exists():
            self.stdout.write(self.style.WARNING(f"No jobs found matching state status: '{state}'"))
            return

        self.stdout.write(self.style.MIGRATE_LABEL(f"\n--- Output Logs for State: {state.upper()} ---"))
        for job in jobs:
            self.stdout.write(f"ID: {job.id} | Command: {job.command} | Attempts: {job.attempts}/{job.max_retries}")