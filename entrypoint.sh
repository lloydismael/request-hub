#!/bin/sh
set -e

python manage.py collectstatic --noinput
python manage.py migrate

if [ "$#" -gt 0 ]; then
	exec "$@"
fi

exec gunicorn request_hub.wsgi:application --bind 0.0.0.0:8000
