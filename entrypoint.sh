#!/bin/bash

# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn with memory-optimized settings
exec gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --threads 2 \
  --worker-class gthread \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --timeout 30 \
  --access-logfile - \
  --error-logfile - \
  mulai_web.wsgi:application 