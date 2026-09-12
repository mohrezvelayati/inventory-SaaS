#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  python manage.py migrate --noinput
fi

if [ "${SEED_DEMO_ON_START:-false}" = "true" ]; then
  python manage.py seed_demo --reset
fi

exec "$@"
