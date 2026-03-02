# OpenClaw Cron Scheduler

[![CI](https://github.com/Fourier7754/openclaw-cron-scheduler/actions/workflows/ci.yml/badge.svg)](https://github.com/Fourier7754/openclaw-cron-scheduler/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent cron task scheduler for OpenClaw that handles rate limiting through queue-based serial execution of concurrent tasks.

## Problem Solved

When multiple cron tasks trigger simultaneously in OpenClaw, concurrent API requests can trigger rate limit errors. This scheduler uses a file-lock-based queue system to serialize task execution while maintaining the original task intervals.

## Features

- **Queue-based scheduling**: Multiple concurrent tasks are automatically queued
- **Single-task direct execution**: No overhead when only one task runs
- **File-based locking**: Safe for multiple processes
- **Configurable intervals**: Control task spacing and timeouts
- **Zero OpenClaw modification**: Works with existing OpenClaw installations

## Installation

### Option 1: Install from GitHub (recommended)

```bash
pip install git+https://github.com/Fourier7754/openclaw-cron-scheduler.git
```

### Option 2: Clone and install in editable mode

```bash
git clone https://github.com/Fourier7754/openclaw-cron-scheduler.git
cd openclaw-cron-scheduler
pip install -e .
```

## Quick Start

### 1. Install and create the compatibility wrapper

```bash
# Install from GitHub
pip install git+https://github.com/Fourier7754/openclaw-cron-scheduler.git

# Initialize the scheduler
openclaw-scheduler init

# Create the compatibility wrapper
mkdir -p ~/.openclaw/scripts
cat > ~/.openclaw/scripts/cron_scheduler.py <<'WRAPPER'
#!/usr/bin/env python3
import sys
import subprocess

if len(sys.argv) < 3:
    sys.exit(1)

task_id = sys.argv[1]
command = sys.argv[2]

result = subprocess.run(
    ["openclaw-scheduler", "run", task_id, command],
    capture_output=True
)
sys.exit(result.returncode)
WRAPPER

chmod +x ~/.openclaw/scripts/cron_scheduler.py
```

### 2. Create an OpenClaw cron job

Use the wrapper command in your cron job:

```json
{
  "name": "my_scheduled_task",
  "schedule": { "kind": "cron", "expr": "0 */6 * * *" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "运行命令: python3 ~/.openclaw/scripts/cron_scheduler.py my_job 'python3 /path/to/your/script.py'"
  }
}
```

### 3. Configure SOUL.md for automatic scheduler usage

Add this rule to your `~/.openclaw/workspace/SOUL.md` so that AI automatically uses the scheduler when creating new cron jobs:

```markdown
## Cron Task Scheduler Rule

When creating cron jobs that run external commands, ALWAYS use the scheduler wrapper:

```
python3 ~/.openclaw/scripts/cron_scheduler.py <job_id> '<command>'
```

Example:
```
运行命令: python3 ~/.openclaw/scripts/cron_scheduler.py data_sync 'python3 /scripts/sync.py'
```

This prevents rate limiting when multiple cron tasks trigger simultaneously.
```

## Usage

### CLI Commands

```bash
# Run a task
openclaw-scheduler run <task_id> <command>

# View queue status
openclaw-scheduler status

# Clear the queue
openclaw-scheduler clear

# Initialize directories and config
openclaw-scheduler init

# Show help
openclaw-scheduler --help
```

### Python API

```python
from openclaw_cron_scheduler import run_task, get_queue_status

# Run a task with queue management
exit_code = run_task("my_job", "python3 /path/to/script.py")

# Check queue status
status = get_queue_status()
print(f"Queue length: {status['queue_length']}")
```

## Configuration

### Config File Locations

The scheduler looks for configuration in this order:

1. `--config` CLI flag
2. `OPENCLAW_SCHEDULER_CONFIG` environment variable
3. `~/.openclaw/scheduler.yaml` (default user config)
4. `/etc/openclaw/scheduler.yaml` (system config)

### Configuration File Format

```yaml
# ~/.openclaw/scheduler.yaml
scheduler:
  queue_dir: ~/.openclaw/cron/queue
  log_file: ~/.openclaw/logs/scheduler.log
  task_interval: 3          # Seconds between tasks
  queue_timeout: 600        # Queue timeout in seconds

logging:
  level: INFO               # DEBUG, INFO, WARNING, ERROR
  format: "[%(asctime)s] %(message)s"
```

### CLI Overrides

You can override configuration values via CLI flags:

```bash
openclaw-scheduler run \
  --queue-dir /custom/queue \
  --task-interval 5 \
  --verbose \
  job123 "python3 script.py"
```

## Migration from Old Scheduler

If you were previously using the old `cron_scheduler.py` script, you have two options:

### Option 1: Compatibility Wrapper (Recommended - Zero-Change)

Create a wrapper script at `~/.openclaw/scripts/cron_scheduler.py` that calls the new scheduler:

```bash
mkdir -p ~/.openclaw/scripts
cat > ~/.openclaw/scripts/cron_scheduler.py <<'WRAPPER'
#!/usr/bin/env python3
import sys
import subprocess

if len(sys.argv) < 3:
    sys.exit(1)

task_id = sys.argv[1]
command = sys.argv[2]

result = subprocess.run(
    ["openclaw-scheduler", "run", task_id, command],
    capture_output=True
)
sys.exit(result.returncode)
WRAPPER

chmod +x ~/.openclaw/scripts/cron_scheduler.py
```

**Benefits:**
- No changes to existing `jobs.json` needed
- Works with all existing cron jobs automatically
- AI will continue creating jobs in the same format

### Option 2: Direct CLI Usage (Manual Per-Job)

Update each OpenClaw job configuration to use the new CLI command directly:

**Before:**
```json
"运行命令": "python3 ~/.openclaw/scripts/cron_scheduler.py JOB_ID 'python3 /path/to/script.py'"
```

**After:**
```json
"运行命令": "openclaw-scheduler run JOB_ID 'python3 /path/to/script.py'"
```

Then restart the gateway:
```bash
openclaw gateway restart
```

**Note:** This requires manually updating each existing job, and new jobs created by AI will NOT automatically use the scheduler unless you also configure SOUL.md (see Quick Start).

## How It Works

1. **Task Enqueuing**: When a task starts, it's added to a shared queue
2. **Position Tracking**: Each task knows its position in the queue
3. **Waiting**: Tasks wait (polling) until they reach position 0
4. **Execution**: Tasks execute one at a time with configured intervals
5. **Cleanup**: Completed tasks are removed from the queue

### Queue States

- `pending`: Task is waiting in queue
- `running`: Task is currently executing
- `done`: Task has completed

## Deployment Script

For easy deployment on multiple servers, use the provided script in `examples/install-scheduler.sh`. It:

1. Installs the package from GitHub
2. Initializes the scheduler configuration
3. Creates the compatibility wrapper
4. (Optional) Updates existing jobs.json
5. (Optional) Restarts the gateway

```bash
bash examples/install-scheduler.sh
```

## Development

### Running Tests

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=openclaw_cron_scheduler
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please submit issues and pull requests on GitHub.
