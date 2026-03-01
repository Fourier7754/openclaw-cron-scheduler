"""
Unit tests for the scheduler module.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from openclaw_cron_scheduler.config import SchedulerConfig
from openclaw_cron_scheduler.scheduler import Scheduler


@pytest.fixture
def temp_config():
    """Create a temporary configuration for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_dir = Path(tmpdir) / "queue"
        log_file = Path(tmpdir) / "scheduler.log"

        config = SchedulerConfig(
            queue_dir=queue_dir,
            log_file=log_file,
            task_interval=0.1,  # Fast for testing
            queue_timeout=10.0,
        )
        yield config


@pytest.fixture
def scheduler(temp_config):
    """Create a scheduler instance for testing."""
    return Scheduler(temp_config)


class TestScheduler:
    """Tests for the Scheduler class."""

    def test_init_directories(self, scheduler):
        """Test that directories are created on initialization."""
        scheduler._ensure_directories()
        assert scheduler.config.queue_dir.exists()
        assert scheduler.config.position_dir.exists()
        assert scheduler.config.log_file.parent.exists()

    def test_enqueue_task(self, scheduler):
        """Test enqueuing a single task."""
        scheduler._ensure_directories()
        position = scheduler.enqueue_task("test_task", "echo hello")

        assert position == 0
        assert scheduler.config.queue_file.exists()

        status = scheduler.get_status()
        assert status["queue_length"] == 1
        assert status["tasks"][0]["id"] == "test_task"

    def test_enqueue_multiple_tasks(self, scheduler):
        """Test enqueuing multiple tasks."""
        scheduler._ensure_directories()

        scheduler.enqueue_task("task1", "echo 1")
        position2 = scheduler.enqueue_task("task2", "echo 2")
        position3 = scheduler.enqueue_task("task3", "echo 3")

        assert position2 == 1
        assert position3 == 2

        status = scheduler.get_status()
        assert status["queue_length"] == 3

    def test_get_queue_position(self, scheduler):
        """Test getting the position of a task."""
        scheduler._ensure_directories()

        scheduler.enqueue_task("task1", "echo 1")
        scheduler.enqueue_task("task2", "echo 2")

        assert scheduler.get_queue_position("task1") == 0
        assert scheduler.get_queue_position("task2") == 1
        assert scheduler.get_queue_position("nonexistent") is None

    def test_clear_queue(self, scheduler):
        """Test clearing the queue."""
        scheduler._ensure_directories()

        scheduler.enqueue_task("task1", "echo 1")
        scheduler.enqueue_task("task2", "echo 2")

        assert scheduler.get_status()["queue_length"] == 2

        scheduler.clear_queue()

        assert scheduler.get_status()["queue_length"] == 0

    def test_run_command_success(self, scheduler):
        """Test running a successful command."""
        exit_code = scheduler.run_command("echo 'test output'")
        assert exit_code == 0

    def test_run_command_failure(self, scheduler):
        """Test running a failing command."""
        exit_code = scheduler.run_command("exit 1")
        assert exit_code == 1

    def test_run_single_task(self, scheduler):
        """Test running a single task (no queueing)."""
        scheduler._ensure_directories()

        exit_code = scheduler.run_task("test_task", "echo 'single task'")
        assert exit_code == 0

        # Queue should be empty after execution
        status = scheduler.get_status()
        assert status["queue_length"] == 0

    def test_mark_task_done(self, scheduler):
        """Test marking a task as done."""
        scheduler._ensure_directories()

        scheduler.enqueue_task("test_task", "echo test")
        scheduler.mark_task_done("test_task")

        # Position file should be cleaned up
        pos_file = scheduler._get_position_file("test_task")
        assert not pos_file.exists()

    def test_cleanup_done_tasks(self, scheduler):
        """Test cleanup of completed tasks."""
        scheduler._ensure_directories()
        scheduler.config.task_interval = 0.01  # Very fast for testing

        # Add and complete a task
        scheduler.enqueue_task("done_task", "echo done")

        lock = scheduler._get_lock()
        try:
            data = scheduler._load_queue()
            data['tasks'][0]['status'] = 'done'
            data['tasks'][0]['next_start_at'] = time.time() - 1  # Already passed
            scheduler._save_queue(data)

            scheduler._cleanup_done_tasks(time.time())

            data = scheduler._load_queue()
            assert len(data['tasks']) == 0
        finally:
            scheduler._release_lock(lock)


class TestSchedulerConfig:
    """Tests for SchedulerConfig."""

    def test_default_paths(self):
        """Test default path configuration."""
        config = SchedulerConfig()
        home = Path.home()

        assert config.queue_dir == home / ".openclaw" / "cron" / "queue"
        assert config.log_file == home / ".openclaw" / "logs" / "scheduler.log"

    def test_computed_properties(self, temp_config):
        """Test computed path properties."""
        assert temp_config.lock_file == temp_config.queue_dir / "scheduler.lock"
        assert temp_config.queue_file == temp_config.queue_dir / "queue.json"
        assert temp_config.position_dir == temp_config.queue_dir / "positions"

    def test_ensure_directories(self, temp_config):
        """Test directory creation."""
        temp_config.ensure_directories()

        assert temp_config.queue_dir.exists()
        assert temp_config.position_dir.exists()
        assert temp_config.log_file.parent.exists()


@pytest.mark.integration
class TestSchedulerIntegration:
    """Integration tests for the scheduler."""

    def test_sequential_task_execution(self, scheduler):
        """Test that tasks execute sequentially with proper delays."""
        scheduler._ensure_directories()
        scheduler.config.task_interval = 0.1

        # Run two tasks in sequence
        exit1 = scheduler.run_task("task1", "echo 'task 1'")
        exit2 = scheduler.run_task("task2", "echo 'task 2'")

        assert exit1 == 0
        assert exit2 == 0

    def test_concurrent_task_simulation(self, scheduler):
        """Test behavior when multiple tasks are enqueued quickly."""
        scheduler._ensure_directories()
        scheduler.config.task_interval = 0.05

        # Enqueue multiple tasks
        positions = [
            scheduler.enqueue_task(f"task{i}", f"echo 'task {i}'")
            for i in range(3)
        ]

        assert positions == [0, 1, 2]

        # Simulate waiting and executing
        for i in range(3):
            task_id = f"task{i}"
            if scheduler.wait_for_turn(task_id):
                scheduler.run_command(f"echo 'task {i}'")
                scheduler.mark_task_done(task_id)

        # Queue should be empty
        assert scheduler.get_status()["queue_length"] == 0
