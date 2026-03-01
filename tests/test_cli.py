"""
Tests for the CLI module.
"""

from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from openclaw_cron_scheduler.cli import cli


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    return tmp_path


class TestCLI:
    """Tests for the CLI interface."""

    def test_version(self, runner):
        """Test version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "openclaw-scheduler" in result.output

    def test_help(self, runner):
        """Test help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "OpenClaw Cron Scheduler" in result.output
        assert "run" in result.output
        assert "status" in result.output
        assert "clear" in result.output
        assert "init" in result.output

    def test_init_command(self, runner, temp_config_dir):
        """Test init command creates directories."""
        with runner.isolated_filesystem():
            # Use temporary directory for config
            result = runner.invoke(cli, [
                "--queue-dir", str(temp_config_dir / "queue"),
                "--log-file", str(temp_config_dir / "logs" / "scheduler.log"),
                "init"
            ])

            assert result.exit_code == 0
            assert "Initialization complete" in result.output

    def test_run_command_basic(self, runner, temp_config_dir):
        """Test basic run command."""
        with runner.isolated_filesystem():
            log_file = temp_config_dir / "scheduler.log"
            queue_dir = temp_config_dir / "queue"

            result = runner.invoke(cli, [
                "--queue-dir", str(queue_dir),
                "--log-file", str(log_file),
                "run", "test_job", "echo 'hello'"
            ])

            assert result.exit_code == 0
            assert "Task test_job" in result.output

    def test_status_command_empty(self, runner, temp_config_dir):
        """Test status command with empty queue."""
        with runner.isolated_filesystem():
            queue_dir = temp_config_dir / "queue"
            log_file = temp_config_dir / "scheduler.log"

            result = runner.invoke(cli, [
                "--queue-dir", str(queue_dir),
                "--log-file", str(log_file),
                "status"
            ])

            assert result.exit_code == 0
            assert "Queue length: 0" in result.output

    def test_clear_command(self, runner, temp_config_dir):
        """Test clear command."""
        with runner.isolated_filesystem():
            queue_dir = temp_config_dir / "queue"
            log_file = temp_config_dir / "scheduler.log"

            # Add a task first
            runner.invoke(cli, [
                "--queue-dir", str(queue_dir),
                "--log-file", str(log_file),
                "run", "test_job", "echo 'test'"
            ])

            # Clear with confirmation
            result = runner.invoke(cli, [
                "--queue-dir", str(queue_dir),
                "--log-file", str(log_file),
                "clear"
            ], input="y\n")

            assert result.exit_code == 0
            assert "Queue cleared" in result.output

    def test_run_missing_args(self, runner):
        """Test run command with missing arguments."""
        result = runner.invoke(cli, ["run"])
        assert result.exit_code != 0

    def test_verbose_flag(self, runner, temp_config_dir):
        """Test verbose flag."""
        result = runner.invoke(cli, [
            "--verbose",
            "--queue-dir", str(temp_config_dir / "queue"),
            "--log-file", str(temp_config_dir / "scheduler.log"),
            "status"
        ])

        assert result.exit_code == 0
