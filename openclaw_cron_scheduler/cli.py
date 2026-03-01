"""
Command-line interface for OpenClaw Cron Scheduler.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from openclaw_cron_scheduler.config import SchedulerConfig, get_config, reset_config
from openclaw_cron_scheduler.scheduler import Scheduler


@click.group()
@click.version_option(version="0.1.0", prog_name="openclaw-scheduler")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--queue-dir",
    type=click.Path(path_type=Path),
    help="Override queue directory",
)
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    help="Override log file path",
)
@click.option(
    "--task-interval",
    type=float,
    default=3.0,
    help="Interval between tasks in seconds",
)
@click.option(
    "--queue-timeout",
    type=float,
    default=600.0,
    help="Queue timeout in seconds",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.pass_context
def cli(ctx, config, queue_dir, log_file, task_interval, queue_timeout, verbose):
    """OpenClaw Cron Scheduler - Intelligent queue-based task execution.

    This scheduler manages concurrent cron tasks by queuing them for serial
    execution, preventing API rate limit errors.
    """
    # Load or create configuration
    if config:
        cfg = SchedulerConfig.from_file(config)
    else:
        cfg = get_config()

    # Apply CLI overrides
    if queue_dir:
        cfg.queue_dir = queue_dir
    if log_file:
        cfg.log_file = log_file
    if task_interval:
        cfg.task_interval = task_interval
    if queue_timeout:
        cfg.queue_timeout = queue_timeout
    if verbose:
        cfg.log_level = "DEBUG"

    # Store config in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg


@cli.command()
@click.argument("task_id")
@click.argument("command", type=str)
@click.pass_context
def run(ctx, task_id, command):
    """Run a task with queue management.

    Usage: openclaw-scheduler run TASK_ID COMMAND

    Example: openclaw-scheduler run job123 'python3 /path/to/script.py'
    """
    cfg = ctx.obj["config"]
    scheduler = Scheduler(cfg)
    exit_code = scheduler.run_task(task_id, command)
    sys.exit(exit_code)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current queue status."""
    cfg = ctx.obj["config"]
    scheduler = Scheduler(cfg)
    status_info = scheduler.get_status()

    click.echo(f"Queue Status:")
    click.echo(f"  Queue length: {status_info['queue_length']}")
    click.echo(f"  Last update: {status_info['last_update']}")

    if status_info['tasks']:
        click.echo(f"\nTasks:")
        for task in status_info['tasks']:
            click.echo(f"  - {task['id']}: {task['status']}")


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to clear the queue?")
@click.pass_context
def clear(ctx):
    """Clear all tasks from the queue."""
    cfg = ctx.obj["config"]
    scheduler = Scheduler(cfg)
    scheduler.clear_queue()
    click.echo("Queue cleared successfully.")


@cli.command()
@click.option("--force", is_flag=True, help="Reinitialize even if directories exist")
@click.pass_context
def init(ctx, force):
    """Initialize directory structure and default configuration."""
    cfg = ctx.obj["config"]
    scheduler = Scheduler(cfg)

    # Create directories
    scheduler._ensure_directories()
    click.echo(f"Created queue directory: {cfg.queue_dir}")
    click.echo(f"Created log directory: {cfg.log_file.parent}")

    # Create default config if it doesn't exist
    default_config_path = Path.home() / ".openclaw" / "scheduler.yaml"
    if not default_config_path.exists() or force:
        default_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(default_config_path, "w") as f:
            f.write(f"""# OpenClaw Cron Scheduler Configuration

scheduler:
  queue_dir: {cfg.queue_dir}
  log_file: {cfg.log_file}
  task_interval: {cfg.task_interval}
  queue_timeout: {cfg.queue_timeout}

logging:
  level: {cfg.log_level}
  format: "[%(asctime)s] %(message)s"
""")
        click.echo(f"Created configuration file: {default_config_path}")
    else:
        click.echo(f"Configuration file already exists: {default_config_path}")
        click.echo("Use --force to overwrite")

    click.echo("\nInitialization complete!")


def main():
    """Main entry point for the CLI."""
    cli(obj={}, auto_envvar_prefix="OPENCLAW_SCHEDULER")


if __name__ == "__main__":
    main()
