from django.core.management.base import BaseCommand
from django.db.models import Count
from queue_manager.models import Job

class Command(BaseCommand):
    help = "Displays a complete summary metric of all job states in the database."

    def handle(self, *args, **options):
        # Aggregate query grouped by the state column
        stats = Job.objects.values('state').annotate(total=Count('state'))
        
        self.stdout.write(self.style.MIGRATE_LABEL("\n=== QueueCTL System Status Summary ==="))
        
        # Build out structural lookups for all required specs
        state_counts = {state[0]: 0 for state in Job.STATE_CHOICES}
        for item in stats:
            state_counts[item['state']] = item['total']
            
        for state, count in state_counts.items():
            self.stdout.write(f"  {state.upper().ljust(12)} : {count}")
        self.stdout.write(self.style.MIGRATE_LABEL("======================================\n"))