#!/bin/sh
set -eu

echo "Running database migrations..."
python manage.py migrate --noinput

if [ "${SEED_DEMO_ON_START:-false}" = "true" ]; then
  echo "Ensuring demo tenant exists..."
  python manage.py seed_demo
fi

echo "Pre-start tasks completed."
