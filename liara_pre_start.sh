#!/bin/sh
set -eu

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Pre-start tasks completed."