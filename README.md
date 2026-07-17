# queuectl

A lightweight, production-grade, highly-concurrent background job queue system built entirely using Python, Django, and SQLite. Engineered specifically to run seamlessly within Windows environments (`cmd.exe`), `queuectl` provides parallel worker execution pools, transparent state management, robust crash resilience, dynamic backoff retry configurations, and an administrative Dead Letter Queue (DLQ).

---

## Technical Architecture Overview

*   **Concurrency Model**: Implements a dedicated parallel process architecture via Python's `multiprocessing` library, routing through custom decoupled execution layers to handle asynchronous workloads cleanly.
*   **Database Lock Mitigation**: Optimized for SQLite leveraging **WAL (Write-Ahead Logging)** mode and extended busy timeouts, avoiding traditional single-file locking bottlenecks under high process volumes.
*   **Row-Level Synchronization**: Employs transactional isolation mechanisms (`select_for_update(skip_locked=True)`) to ensure multiple active concurrent workers pick up distinct payloads without race conditions or execution duplication.
*   **Lazy Bootstrapping**: Explicitly configures Django context states inside newly spawned Windows child processes before importing or processing application model layers, preventing `AppRegistryNotReady` fatal runtime traps.

---

## Directory Structure

```text
queuectl/
│
├── db.sqlite3                  # High-concurrency optimized database
├── manage.py                   # Django entrypoint wrapper
│
├── queuectl/                   # Project Core Configuration
│   ├── __init__.py
│   ├── settings.py             # Configured database WAL profiles
│   ├── urls.py
│   └── wsgi.py
│
└── queue_manager/              # Primary Application Engine
    ├── __init__.py
    ├── apps.py
    ├── models.py               # Job and AppConfig database schemas
    ├── services.py             # System configuration retrievers
    ├── workers.py              # Multiprocessing polling engine core
    ├── migrations/
    └── management/
        └── commands/           # Command-Line Toolchain Interface
            ├── config.py
            ├── dlq.py
            ├── enqueue.py
            ├── list_state.py
            ├── status.py
            └── worker.py
```
# Installation & Setup

## 1. Activate the Virtual Environment

Navigate to the project directory and activate the virtual environment.

```text
cd D:\queuectl
python -m venv venv
venv\Scripts\activate
```

Ensure all required Python packages have been installed before proceeding.

---

## 2. Initialize the Database

Run Django migrations to create all required database tables.

```text
python manage.py migrate
```

### Enable SQLite Write-Ahead Logging (WAL)

To improve concurrent database access, enable SQLite's **Write-Ahead Logging (WAL)** mode.

```text
python manage.py shell --command "from django.db import connection; cursor = connection.cursor(); cursor.execute('PRAGMA journal_mode=WAL;')"
```

---

# Command Line Interface (CLI)

## 1. Enqueue a Job

Submit a new job to the queue using a JSON configuration.

```text
python manage.py enqueue "{\"id\":\"job_01\", \"command\":\"timeout 5\", \"max_retries\":2}"
```

Example fields:

* **id** – Unique job identifier
* **command** – Command to execute
* **max_retries** – Maximum retry attempts before moving the job to the Dead Letter Queue (DLQ)

---

## 2. Start Worker Processes

Launch multiple worker processes to execute pending jobs.

```text
python manage.py worker --count 3
```

* `--count` specifies the number of worker processes.
* Press **Ctrl + C** at any time to gracefully stop all workers.

---

## 3. View Queue Status

Display the number of jobs currently in each execution state.

```text
python manage.py status
```

---

## 4. List Jobs by State

View all jobs belonging to a specific state.

```text
python manage.py list_state completed
```

Supported states:

* pending
* processing
* completed
* failed
* dead

---

## 5. Dead Letter Queue (DLQ)

### List Dead Jobs

```text
python manage.py dlq list
```

### Retry a Dead Job

```text
python manage.py dlq retry job_01
```

This moves the specified job back into the active queue for reprocessing.

---

## 6. Update Runtime Configuration

Modify configuration values stored in the database without restarting worker processes.

Set the retry backoff base:

```text
python manage.py config set backoff-base 3
```

Set the maximum retry count:

```text
python manage.py config set max-retries 5
```

---

# Job Lifecycle

```text
                ENQUEUE
                   │
                   ▼
              ┌─────────┐
              │ Pending │
              └────┬────┘
                   │
          Worker picks job
                   │
                   ▼
            ┌────────────┐
            │ Processing │
            └─────┬──────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
   Completed             Failed
                              │
               Retries Remaining?
                    │
          Yes ──────┴──────► Pending
                    │
                    No
                    ▼
             Dead Letter Queue
```

**State Descriptions**

| State          | Description                                                                    |
| -------------- | ------------------------------------------------------------------------------ |
| **Pending**    | Job is waiting to be picked up by a worker.                                    |
| **Processing** | A worker is currently executing the job.                                       |
| **Completed**  | The job finished successfully.                                                 |
| **Failed**     | The current execution attempt failed and may be retried.                       |
| **Dead**       | The job exceeded its retry limit and was moved to the Dead Letter Queue (DLQ). |
