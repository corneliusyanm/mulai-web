#!/bin/bash

# Daily reminder generation script for Mulai Gym
# Run this script daily via cron to generate member reminders
# Works with Docker setup on DigitalOcean droplet

# Configuration
CONTAINER_NAME="mulai_web"
LOG_FILE="/root/mulai_web/reminder_generation.log"
DRY_RUN=${1:-""}

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" | tee -a "$LOG_FILE"
}

# Function to check if container is running
check_container() {
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_message "ERROR: Container $CONTAINER_NAME is not running"
        exit 1
    fi
}

# Main execution
log_message "Starting reminder generation${DRY_RUN:+ (DRY RUN)}"

# Check if container is running
check_container

# Run the reminder generation command
if [ "$DRY_RUN" = "--dry-run" ]; then
    log_message "Running in dry-run mode..."
    if docker exec "$CONTAINER_NAME" python manage.py generate_reminders --dry-run; then
        log_message "Dry run completed successfully"
    else
        log_message "ERROR: Dry run failed"
        exit 1
    fi
else
    log_message "Generating reminders..."
    if docker exec "$CONTAINER_NAME" python manage.py generate_reminders; then
        log_message "Reminder generation completed successfully"
    else
        log_message "ERROR: Reminder generation failed"
        exit 1
    fi
fi

log_message "Script execution finished" 