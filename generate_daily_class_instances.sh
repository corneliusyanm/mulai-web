#!/bin/bash

# Daily class instance generation script for Mulai Gym
# Run this script daily via cron to generate class instances
# Works with Docker setup on DigitalOcean droplet

# Configuration
CONTAINER_NAME="mulai_web"
LOG_FILE="/root/mulai_web/class_instance_generation.log"

# Get the number of days parameter (default to 3 if not provided)
DAYS=${1:-3}

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
log_message "Starting class instance generation for $DAYS days"

# Check if container is running
check_container

# Run the management command
log_message "Generating class instances..."
if docker exec "$CONTAINER_NAME" python manage.py generate_class_instances "$DAYS"; then
    log_message "Class instance generation completed successfully"
else
    log_message "ERROR: Class instance generation failed"
    exit 1
fi

log_message "Script execution finished" 