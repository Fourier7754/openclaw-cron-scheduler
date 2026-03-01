"""
OpenClaw Cron Scheduler

An intelligent cron task scheduler for OpenClaw that handles rate limiting
through queue-based serial execution of concurrent tasks.
"""

__version__ = "0.1.0"
__author__ = "OpenClaw Contributors"
__license__ = "MIT"

from openclaw_cron_scheduler.scheduler import (
    enqueue_task,
    run_task,
    get_queue_status,
    clear_queue,
    init_directories,
)

__all__ = [
    "__version__",
    "enqueue_task",
    "run_task",
    "get_queue_status",
    "clear_queue",
    "init_directories",
]
