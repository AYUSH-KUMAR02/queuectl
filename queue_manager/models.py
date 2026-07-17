from django.db import models
from django.utils import timezone

class Job(models.Model):
    STATE_PENDING = 'pending'
    STATE_PROCESSING = 'processing'
    STATE_COMPLETED = 'completed'
    STATE_FAILED = 'failed'
    STATE_DEAD = 'dead'

    STATE_CHOICES = [
        (STATE_PENDING, 'Pending'),
        (STATE_PROCESSING, 'Processing'),
        (STATE_COMPLETED, 'Completed'),
        (STATE_FAILED, 'Failed'),
        (STATE_DEAD, 'Dead (DLQ)'),
    ]

    id = models.CharField(max_length=255, primary_key=True)
    command = models.TextField()
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default=STATE_PENDING)
    attempts = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # New column tracking when a retryable failed job is eligible to run again
    run_at = models.DateTimeField(default=timezone.now)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=timezone.now)

    def __str__(self):
        return f"Job {self.id} [{self.state}]"

class AppConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value}"