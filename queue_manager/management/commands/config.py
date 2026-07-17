from django.core.management.base import BaseCommand
from queue_manager.models import AppConfig

class Command(BaseCommand):
    help = "Sets system-wide configurations keys dynamically."

    def add_arguments(self, parser):
        parser.add_argument('action', type=str, choices=['set'], help="Action to perform (set)")
        parser.add_argument('key', type=str, help="Configuration key identifier (e.g., max-retries)")
        parser.add_argument('value', type=str, help="Value mapping string for target entity key")

    def handle(self, *args, **options):
        key = options['key']
        value = options['value']
        
        config, created = AppConfig.objects.update_or_create(
            key=key,
            defaults={'value': value}
        )
        self.stdout.write(self.style.SUCCESS(f"[+] Global Configuration updated successfully: {key} = {value}"))