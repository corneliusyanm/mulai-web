#!/bin/bash

# Format Python files with autopep8
echo "Running autopep8 on Python files..."
find . -type f -name "*.py" -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/.venv/*" -exec autopep8 --in-place --aggressive --aggressive {} \;

# Sort imports with isort
echo "Sorting imports with isort..."
find . -type f -name "*.py" -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/.venv/*" -exec isort {} \;

# Run pylint for code quality check (optional)
echo "Running pylint for code quality check..."
pylint --load-plugins=pylint_django --django-settings-module=mulai_web.settings accounts payments visits mulai_web

echo "Formatting complete!" 