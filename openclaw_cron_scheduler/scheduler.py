"""
Core scheduler logic for OpenClaw Cron Scheduler.

This module provides queue-based task scheduling to handle rate limiting
when multiple cron tasks trigger simultaneously.
"""

import fcntl
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from openclaw_cron_scheduler.config import SchedulerConfig, get_config


class Scheduler:
    """Main scheduler class for managing queued task execution."""

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """Initialize the scheduler.

        Args:
            config: Optional configuration. If None, uses default config loading.
        """
        self.config = config or get_config()
        self._setup_logging()
        self._lock_file_handle = None

    def _setup_logging(self):
        """Configure logging for the scheduler."""
        self.logger = logging.getLogger("openclaw_cron_scheduler")
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(self.config.log_format)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler
        try:
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            self.logger.warning(f"Could not create log file: {e}")

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        self.config.ensure_directories()

    def _get_lock(self):
        """Acquire file lock for inter-process synchronization.

        Returns:
            File handle for the lock.
        """
        self._ensure_directories()
        lock = open(self.config.lock_file, "w")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return lock

    @staticmethod
    def _release_lock(lock):
        """Release file lock.

        Args:
            lock: File handle to release.
        """
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()

    def _load_queue(self) -> Dict:
        """Load queue from disk.

        Returns:
            Dictionary containing queue data.
        """
        if self.config.queue_file.exists():
            try:
                with open(self.config.queue_file, "r") as f:
                    data = json.load(f)
                    # Clean up expired tasks
                    now = time.time()
                    data["tasks"] = [
                        t
                        for t in data.get("tasks", [])
                        if now - t.get("enqueued_at", 0) < self.config.queue_timeout
                    ]
                    return data
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error loading queue: {e}, creating new queue")
                return {"tasks": [], "last_update": 0}
        return {"tasks": [], "last_update": 0}

    def _save_queue(self, data: Dict):
        """Save queue to disk.

        Args:
            data: Queue data to save.
        """
        with open(self.config.queue_file, "w") as f:
            json.dump(data, f, indent=2)

    def _get_position_file(self, task_id: str) -> Path:
        """Get the position file path for a task.

        Args:
            task_id: Unique task identifier.

        Returns:
            Path to the position file.
        """
        return self.config.position_dir / f"{task_id}.json"

    def _write_position(self, task_id: str, position: int, status: str):
        """Write task position information.

        Args:
            task_id: Unique task identifier.
            position: Position in queue.
            status: Task status.
        """
        pos_file = self._get_position_file(task_id)
        with open(pos_file, "w") as f:
            json.dump({"position": position, "status": status}, f)

    def _read_position(self, task_id: str) -> Optional[Dict]:
        """Read task position information.

        Args:
            task_id: Unique task identifier.

        Returns:
            Position dict or None if not found.
        """
        pos_file = self._get_position_file(task_id)
        if pos_file.exists():
            try:
                with open(pos_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def enqueue_task(self, task_id: str, command: str) -> int:
        """Add a task to the queue.

        Args:
            task_id: Unique task identifier.
            command: Command to execute.

        Returns:
            Position in queue (0-based index).
        """
        lock = self._get_lock()
        try:
            data = self._load_queue()
            position = len(data["tasks"])
            data["tasks"].append(
                {
                    "id": task_id,
                    "command": command,
                    "enqueued_at": time.time(),
                    "status": "pending",
                }
            )
            data["last_update"] = time.time()
            self._save_queue(data)
            self._write_position(task_id, position, "pending")
            self.logger.info(f"Task {task_id} enqueued at position {position}")
            return position
        finally:
            self._release_lock(lock)

    def get_queue_position(self, task_id: str) -> Optional[int]:
        """Get the current position of a task in the queue.

        Args:
            task_id: Unique task identifier.

        Returns:
            Position in queue or None if not found.
        """
        lock = self._get_lock()
        try:
            data = self._load_queue()
            for i, task in enumerate(data["tasks"]):
                if task["id"] == task_id:
                    return i
            return None
        finally:
            self._release_lock(lock)

    def wait_for_turn(self, task_id: str) -> bool:
        """Wait until it's this task's turn to execute.

        Args:
            task_id: Unique task identifier.

        Returns:
            True if ready to execute, False if timeout or not found.
        """
        start_time = time.time()
        last_position = -1

        while True:
            position = self.get_queue_position(task_id)

            if position is None:
                self.logger.warning(
                    f"Task {task_id} not found in queue, may have timed out"
                )
                return False

            if position == 0:
                # Check if ready to start
                lock = self._get_lock()
                try:
                    data = self._load_queue()
                    for task in data["tasks"]:
                        if task["id"] == task_id:
                            if task["status"] == "pending":
                                # Can start executing
                                task["status"] = "running"
                                self._save_queue(data)
                                self._write_position(task_id, 0, "running")
                                self.logger.info(f"Task {task_id} is now running")
                                return True
                            elif task["status"] == "running":
                                # Already running (might be self)
                                return True
                finally:
                    self._release_lock(lock)

            # Log position changes
            if position != last_position:
                self.logger.info(f"Task {task_id} waiting... position: {position + 1}")
                last_position = position

            # Timeout check
            if time.time() - start_time > self.config.queue_timeout:
                self.logger.warning(
                    f"Task {task_id} timeout waiting, forcing execution"
                )
                return True

            time.sleep(0.5)

    def mark_task_done(self, task_id: str):
        """Mark a task as completed and clean up.

        Args:
            task_id: Unique task identifier.
        """
        lock = self._get_lock()
        try:
            data = self._load_queue()
            for i, task in enumerate(data["tasks"]):
                if task["id"] == task_id:
                    task["status"] = "done"
                    task["finished_at"] = time.time()
                    # Calculate wait time
                    wait_until = time.time() + self.config.task_interval
                    task["next_start_at"] = wait_until
                    break
            self._save_queue(data)

            # Remove completed tasks
            self._cleanup_done_tasks(wait_until)
        finally:
            self._release_lock(lock)

        # Clean up position file
        pos_file = self._get_position_file(task_id)
        if pos_file.exists():
            try:
                pos_file.unlink()
            except IOError:
                pass

    def _cleanup_done_tasks(self, now: float):
        """Clean up completed tasks (must be called while holding lock).

        Args:
            now: Current timestamp.
        """
        data = self._load_queue()
        while data["tasks"] and data["tasks"][0]["status"] == "done":
            task = data["tasks"].pop(0)
            next_start = task.get("next_start_at", 0)
            if next_start > now:
                wait_time = next_start - now
                self.logger.info(
                    f"Task {task['id']} done, waiting {wait_time:.1f}s before next task"
                )
                # Save queue state
                self._save_queue(data)
                # Release lock and wait
                self._release_lock(self._get_lock())
                time.sleep(wait_time)
                # Reacquire lock
                lock = self._get_lock()
                data = self._load_queue()
            else:
                self.logger.info(f"Task {task['id']} done and removed from queue")
        self._save_queue(data)

    def run_command(self, command: str) -> int:
        """Execute a command.

        Args:
            command: Command string to execute.

        Returns:
            Exit code from the command.
        """
        self.logger.info(f"Executing: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stdout:
            stdout = result.stdout.strip()
            if stdout:
                # Print full output to stdout for agent to capture
                print(stdout)
                # Log first 200 chars to avoid bloating log file
                self.logger.info(f"STDOUT: {stdout[:200]}...")
        if result.stderr:
            stderr = result.stderr.strip()
            if stderr:
                print(stderr, file=sys.stderr)
                self.logger.error(f"STDERR: {stderr[:200]}...")
        self.logger.info(f"Exit code: {result.returncode}")
        return result.returncode

    def run_task(self, task_id: str, command: str) -> int:
        """Run a task with queue management.

        Args:
            task_id: Unique task identifier.
            command: Command to execute.

        Returns:
            Exit code from the command.
        """
        # Generate unique task ID with timestamp to avoid same-second conflicts
        unique_id = f"{task_id}_{int(time.time() * 1000)}"

        self.logger.info(f"=== Task {unique_id} started ===")

        # Enqueue
        position = self.enqueue_task(unique_id, command)

        if position > 0:
            self.logger.info(f"Position in queue: {position + 1}")
            # Wait for turn
            if not self.wait_for_turn(unique_id):
                return 1  # Timeout or error

        # Execute command
        exit_code = self.run_command(command)

        # Mark done
        self.mark_task_done(unique_id)

        self.logger.info(
            f"=== Task {unique_id} completed with exit code {exit_code} ==="
        )
        return exit_code

    def get_status(self) -> Dict:
        """Get current queue status.

        Returns:
            Dictionary with queue status information.
        """
        lock = self._get_lock()
        try:
            data = self._load_queue()
            return {
                "queue_length": len(data["tasks"]),
                "tasks": [
                    {
                        "id": t["id"],
                        "status": t["status"],
                        "enqueued_at": t["enqueued_at"],
                    }
                    for t in data["tasks"]
                ],
                "last_update": data.get("last_update", 0),
            }
        finally:
            self._release_lock(lock)

    def clear_queue(self):
        """Clear all tasks from the queue."""
        lock = self._get_lock()
        try:
            self._save_queue({"tasks": [], "last_update": time.time()})
            self.logger.info("Queue cleared")
        finally:
            self._release_lock(lock)


# Convenience functions for direct usage


def init_directories(config: Optional[SchedulerConfig] = None) -> None:
    """Initialize scheduler directories.

    Args:
        config: Optional configuration.
    """
    scheduler = Scheduler(config)
    scheduler._ensure_directories()


def enqueue_task(
    task_id: str, command: str, config: Optional[SchedulerConfig] = None
) -> int:
    """Add a task to the queue.

    Args:
        task_id: Unique task identifier.
        command: Command to execute.
        config: Optional configuration.

    Returns:
        Position in queue.
    """
    scheduler = Scheduler(config)
    return scheduler.enqueue_task(task_id, command)


def run_task(
    task_id: str, command: str, config: Optional[SchedulerConfig] = None
) -> int:
    """Run a task with queue management.

    Args:
        task_id: Unique task identifier.
        command: Command to execute.
        config: Optional configuration.

    Returns:
        Exit code from the command.
    """
    scheduler = Scheduler(config)
    return scheduler.run_task(task_id, command)


def get_queue_status(config: Optional[SchedulerConfig] = None) -> Dict:
    """Get current queue status.

    Args:
        config: Optional configuration.

    Returns:
        Dictionary with queue status.
    """
    scheduler = Scheduler(config)
    return scheduler.get_status()


def clear_queue(config: Optional[SchedulerConfig] = None) -> None:
    """Clear all tasks from the queue.

    Args:
        config: Optional configuration.
    """
    scheduler = Scheduler(config)
    scheduler.clear_queue()
