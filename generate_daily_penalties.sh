#!/bin/bash

# Daily class no-show penalty script for Mulai Gym
# Runs after the gym closes, when every class that day is settled.
# Works with Docker setup on DigitalOcean droplet
#
# Crontab, 21:00 Jakarta. The droplet clock is UTC, so that is 14:00 there:
#   0 14 * * * /root/mulai_web/generate_daily_penalties.sh
# Check with `date` on the droplet before trusting that, and confirm with
# `crontab -l` that the other two jobs use the same convention.
#
# Pass --dry-run as the first argument to see what would happen without
# changing anything.

# Configuration
CONTAINER_NAME="mulai_web"
LOG_FILE="/root/mulai_web/class_penalty.log"
DRY_RUN=${1:-""}

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" | tee -a "$LOG_FILE"
}

# Function to check if container is running
check_container() {
    if ! docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        log_message "ERROR: Container $CONTAINER_NAME is not running"
        exit 1
    fi
}

# Main execution
log_message "Starting class penalty run${DRY_RUN:+ (DRY RUN)}"

check_container

if [ "$DRY_RUN" = "--dry-run" ]; then
    if docker exec "$CONTAINER_NAME" python manage.py apply_class_penalties --dry-run; then
        log_message "Dry run completed successfully"
    else
        log_message "ERROR: Dry run failed"
        exit 1
    fi
else
    if docker exec "$CONTAINER_NAME" python manage.py apply_class_penalties; then
        log_message "Class penalty run completed successfully"
    else
        log_message "ERROR: Class penalty run failed"
        exit 1
    fi
fi

log_message "Script execution finished"
