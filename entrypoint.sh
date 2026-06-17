#!/bin/sh
set -eu

# Restrict default file permissions for any files created at runtime.
umask 027

python manage.py collectstatic --noinput
python manage.py migrate

if [ "$#" -gt 0 ]; then
	exec "$@"
fi

exec gunicorn request_hub.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --worker-class gthread \
    --max-requests 1000 \
    --max-requests-jitter 100
