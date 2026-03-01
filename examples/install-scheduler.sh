#!/bin/bash
# OpenClaw Cron Scheduler - One-Click Deployment Script
#
# This script installs the scheduler and optionally updates existing jobs.json
# to use the new CLI command instead of the old Python script.

set -e

echo "=== OpenClaw Cron Scheduler Installation ==="
echo ""

# Check if pip is available
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "Error: pip is not installed. Please install pip first."
    exit 1
fi

# Use pip3 if available, otherwise pip
PIP_CMD="pip"
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
fi

# Install the package from GitHub
echo "1. Installing openclaw-cron-scheduler..."
$PIP_CMD install git+https://github.com/Fourier7754/openclaw-cron-scheduler.git

# Initialize configuration
echo ""
echo "2. Initializing scheduler..."
openclaw-scheduler init

# Optional: Update jobs.json
echo ""
read -p "3. Update jobs.json to use new command? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    JOBS_FILE="$HOME/.openclaw/cron/jobs.json"

    if [ -f "$JOBS_FILE" ]; then
        echo "   Backing up jobs.json to jobs.json.bak..."
        cp "$JOBS_FILE" "$JOBS_FILE.bak"

        echo "   Updating job commands..."
        python3 <<PYTHON
import json
import sys

try:
    with open('$JOBS_FILE', 'r') as f:
        jobs = json.load(f)

    updated = 0
    for job in jobs.get('jobs', []):
        if 'payload' in job and 'message' in job['payload']:
            msg = job['payload']['message']
            if 'python3 ~/.openclaw/scripts/cron_scheduler.py' in msg or 'python3 /root/.openclaw/scripts/cron_scheduler.py' in msg:
                msg = msg.replace(
                    "python3 ~/.openclaw/scripts/cron_scheduler.py",
                    "openclaw-scheduler run"
                ).replace(
                    "python3 /root/.openclaw/scripts/cron_scheduler.py",
                    "openclaw-scheduler run"
                )
                job['payload']['message'] = msg
                updated += 1

    with open('$JOBS_FILE', 'w') as f:
        json.dump(jobs, f, indent=2)

    print(f"   Updated {updated} job(s)")
except Exception as e:
    print(f"   Error: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON
    else
        echo "   Warning: jobs.json not found at $JOBS_FILE"
    fi
fi

# Optional: Create compatibility wrapper
echo ""
read -p "4. Create compatibility wrapper (no changes to jobs.json needed)? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    WRAPPER_FILE="$HOME/.openclaw/scripts/cron_scheduler.py"

    mkdir -p "$(dirname "$WRAPPER_FILE")"

    cat > "$WRAPPER_FILE" <<'WRAPPER'
#!/usr/bin/env python3
"""
OpenClaw Cron Scheduler - Compatibility Wrapper

This wrapper forwards all calls to the new openclaw-scheduler CLI package.
Install the package: pip install git+https://github.com/Fourier7754/openclaw-cron-scheduler.git
"""
import sys
import subprocess

if len(sys.argv) < 3:
    print("Usage: cron_scheduler.py <task_id> <command>", file=sys.stderr)
    sys.exit(1)

task_id = sys.argv[1]
command = sys.argv[2]

result = subprocess.run(
    ["openclaw-scheduler", "run", task_id, command],
    capture_output=True
)

# Output stdout/stderr from the scheduler (decode bytes to string)
if result.stdout:
    sys.stdout.write(result.stdout.decode('utf-8'))
if result.stderr:
    sys.stderr.write(result.stderr.decode('utf-8'))

sys.exit(result.returncode)
WRAPPER

    chmod +x "$WRAPPER_FILE"
    echo "   Created wrapper at: $WRAPPER_FILE"
fi

# Restart OpenClaw gateway
echo ""
read -p "5. Restart OpenClaw gateway? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v openclaw &> /dev/null; then
        openclaw gateway restart
        echo "   Gateway restarted"
    else
        echo "   Warning: openclaw command not found"
    fi
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Usage examples:"
echo "  openclaw-scheduler run job123 'python3 script.py'"
echo "  openclaw-scheduler status"
echo "  openclaw-scheduler clear"
echo ""
echo "For more information, run: openclaw-scheduler --help"
