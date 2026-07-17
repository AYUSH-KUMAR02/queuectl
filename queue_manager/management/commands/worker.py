from django.core.management.base import BaseCommand
from queue_manager.workers import run_single_worker_loop

class Command(BaseCommand):
    help = "Starts the QueueCTL background worker polling engine."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='Number of worker processes to spawn (Defaults to 1).'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        if count == 1:
            self.stdout.write(self.style.MIGRATE_LABEL("[*] Starting a single standalone worker process..."))
            try:
                run_single_worker_loop()
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\n[+] Worker safely stopped via keyboard interrupt."))
        else:
            self.stdout.write(
                self.style.WARNING(f"[!] Concurrency request for {count} workers received. Spawning process pool...")
            )
