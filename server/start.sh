#!/bin/sh
set -eu
umask 022
python server/manage.py migrate --noinput
chmod 600 "$CMS_DATA_DIR/cms.sqlite3"
python server/manage.py seed_content
python server/manage.py collectstatic --noinput
exec gunicorn --chdir server orion.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120 --access-logfile - --error-logfile -
