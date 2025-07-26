#!/bin/bash

# Daily reminder generation script for Mulai Gym
# Run this script daily via cron to generate member reminders

# Set the working directory
cd /Users/cornel/workspace/mulai_web

# Activate virtual environment if using one
source .venv/bin/activate

# Run the reminder generation command
python manage.py generate_reminders

# Log completion with timestamp
echo "$(date): Daily reminders generated" >> reminder_generation.log 