from django.core.management.base import BaseCommand
from queue_manager.services import enqueue_job

class Command(BaseCommand):
    help = "Enqueues a new background job into the persistent database using a JSON string."

    def add_arguments(self, parser):
        # A single positional argument for the JSON text payload
        parser.add_argument('job_json', type=str, help="JSON string representing the job payload.")

    def handle(self, *args, **options):
        payload = options['job_json']
        result = enqueue_job(payload)

        if result["success"]:
            job = result["job"]
            self.stdout.write(
                self.style.SUCCESS(f"Successfully enqueued job: {job.id} -> '{job.command}'")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Failed to enqueue job. Error: {result['error']}")
            )