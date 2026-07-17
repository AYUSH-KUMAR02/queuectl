import sys
import time
import signal
from multiprocessing import Process, Event
from django.core.management.base import BaseCommand
from queue_manager.workers import run_single_worker_loop

# Global placeholder to allow clean access within the structural signal framework
worker_processes = []
stop_event = None

def signal_handler(signum, frame):
    """
    Catches termination requests. Signals the event framework so workers stop
    fetching new tasks, facilitating a graceful drain of active execution threads.
    """
    global stop_event, worker_processes
    print("\n[!] Shutdown signal intercepted. Initiating graceful worker drain-down...")
    
    if stop_event:
        stop_event.set()
        
    # Block and wait for all child sub-processes to exit cleanly
    for proc in worker_processes:
        if proc.is_alive():
            proc.join()
            
    print("[+] All worker processes gracefully terminated. Exiting system.")
    sys.exit(0)

class Command(BaseCommand):
    help = "Starts the QueueCTL background worker process pooling engine."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='Number of parallel worker processes to spawn.'
        )

    def handle(self, *args, **options):
        global stop_event, worker_processes
        count = options['count']
        
        if count < 1:
            self.stdout.write(self.style.ERROR("[X] Worker count must be at least 1."))
            return

        self.stdout.write(self.style.MIGRATE_LABEL(f"[*] Bootstrapping process pool for {count} workers..."))
        
        stop_event = Event()
        worker_processes = []

        # Intercept both CTRL+C (SIGINT) and kill requests (SIGTERM)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Spawn individual processing nodes inside isolated OS-level contexts
        for i in range(count):
            proc = Process(
                target=run_single_worker_loop, 
                args=(stop_event,), 
                name=f"QueueWorker-{i+1}"
            )
            # daemon=True ensures child execution contexts drop cleanly if master drops unexpectedly
            proc.daemon = True 
            proc.start()
            worker_processes.append(proc)
            self.stdout.write(self.style.SUCCESS(f"  -> Spawned process child node: {proc.name} (PID: {proc.pid})"))

        self.stdout.write(self.style.MIGRATE_LABEL("[*] Worker pool active. Press Ctrl+C to gracefully stop..."))

        # Keep the main controller loop active while child processing pipelines drain
        while True:
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                # Fallback intercept mechanism for localized terminal runtimes
                signal_handler(signal.SIGINT, None)