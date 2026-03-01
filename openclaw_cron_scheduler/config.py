"""
Configuration management for OpenClaw Cron Scheduler.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SchedulerConfig:
    """Configuration for the cron scheduler."""

    # Directory paths
    queue_dir: Path = field(
        default_factory=lambda: Path.home() / ".openclaw" / "cron" / "queue"
    )
    log_file: Path = field(
        default_factory=lambda: Path.home() / ".openclaw" / "logs" / "scheduler.log"
    )

    # Timing parameters
    task_interval: float = 3.0  # Seconds between tasks
    queue_timeout: float = 600.0  # Queue timeout in seconds

    # Logging
    log_level: str = "INFO"
    log_format: str = "[%(asctime)s] %(message)s"

    # File paths (computed from queue_dir)
    @property
    def lock_file(self) -> Path:
        return self.queue_dir / "scheduler.lock"

    @property
    def queue_file(self) -> Path:
        return self.queue_dir / "queue.json"

    @property
    def position_dir(self) -> Path:
        return self.queue_dir / "positions"

    @classmethod
    def from_file(cls, path: Optional[Path] = None) -> "SchedulerConfig":
        """Load configuration from a YAML file.

        Args:
            path: Path to config file. If None, checks default locations.

        Returns:
            SchedulerConfig instance with loaded values.
        """
        import yaml

        config_path = path or cls._find_config_file()
        if not config_path or not config_path.exists():
            return cls()

        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}

            config = cls()
            if "scheduler" in data:
                scheduler_cfg = data["scheduler"]
                if "queue_dir" in scheduler_cfg:
                    config.queue_dir = Path(scheduler_cfg["queue_dir"])
                if "log_file" in scheduler_cfg:
                    config.log_file = Path(scheduler_cfg["log_file"])
                if "task_interval" in scheduler_cfg:
                    config.task_interval = float(scheduler_cfg["task_interval"])
                if "queue_timeout" in scheduler_cfg:
                    config.queue_timeout = float(scheduler_cfg["queue_timeout"])

            if "logging" in data:
                logging_cfg = data["logging"]
                if "level" in logging_cfg:
                    config.log_level = logging_cfg["level"]
                if "format" in logging_cfg:
                    config.log_format = logging_cfg["format"]

            return config
        except (yaml.YAMLError, IOError, ValueError) as e:
            # Fall back to defaults on error
            return cls()

    @classmethod
    def _find_config_file(cls) -> Optional[Path]:
        """Find configuration file in standard locations.

        Checks in order:
        1. Environment variable OPENCLAW_SCHEDULER_CONFIG
        2. ~/.openclaw/scheduler.yaml
        3. /etc/openclaw/scheduler.yaml

        Returns:
            Path to config file if found, None otherwise.
        """
        # Check environment variable
        env_path = os.environ.get("OPENCLAW_SCHEDULER_CONFIG")
        if env_path:
            return Path(env_path)

        # Check user config directory
        user_config = Path.home() / ".openclaw" / "scheduler.yaml"
        if user_config.exists():
            return user_config

        # Check system config directory
        system_config = Path("/etc/openclaw/scheduler.yaml")
        if system_config.exists():
            return system_config

        return None

    def ensure_directories(self) -> None:
        """Create all necessary directories if they don't exist."""
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.position_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


# Default global configuration
_default_config: Optional[SchedulerConfig] = None


def get_config(config_path: Optional[Path] = None) -> SchedulerConfig:
    """Get the current configuration, loading from file if needed.

    Args:
        config_path: Optional path to config file.

    Returns:
        SchedulerConfig instance.
    """
    global _default_config
    if _default_config is None:
        _default_config = SchedulerConfig.from_file(config_path)
    return _default_config


def reset_config() -> None:
    """Reset the global configuration (mainly for testing)."""
    global _default_config
    _default_config = None
