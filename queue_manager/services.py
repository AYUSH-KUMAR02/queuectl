import json
from django.utils import timezone
from .models import Job, AppConfig

def get_config_value(key, default):
    """Helper to fetch configuration values from the database or fall back to defaults."""
    try:
        config_obj = AppConfig.objects.get(key=key)
        return int(config_obj.value) if config_obj.value.isdigit() else config_obj.value
    except AppConfig.DoesNotExist:
        return default

def enqueue_job(json_string):
    """
    Parses a JSON string containing job parameters, merges them with 
    system configurations, and persists the new job into the database.
    """
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON format."}

    job_id = data.get("id")
    command = data.get("command")

    if not job_id or not command:
        return {"success": False, "error": "Missing required fields: 'id' and 'command'."}

    # Fetch global max_retries default override if set, otherwise fallback to assignment spec (3)
    default_max_retries = get_config_value("max-retries", 3)
    max_retries = data.get("max_retries", default_max_retries)

    # Check if a job with this ID already exists to prevent duplicate key conflicts
    if Job.objects.filter(id=job_id).exists():
        return {"success": False, "error": f"Job with ID '{job_id}' already exists."}

    # Create and persist the Job row
    job = Job.objects.create(
        id=job_id,
        command=command,
        state=Job.STATE_PENDING,
        attempts=0,
        max_retries=max_retries,
        created_at=timezone.now(),
        updated_at=timezone.now()
    )

    return {"success": True, "job": job}