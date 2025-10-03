#!/bin/bash

PROJECT_DIR="/home/creworder.com/public_html/staging_creworder_backend"
VENV_DIR="/home/creworder.com/public_html/venv"
GUNICORN_PORT="8002"
GUNICORN_WORKERS=3

source $VENV_DIR/bin/activate
cd $PROJECT_DIR

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn staging_creworder_backend.wsgi:application \
  --bind 127.0.0.1:$GUNICORN_PORT \
  --workers $GUNICORN_WORKERS \
  --timeout 120 \
  --log-level debug \
  --access-logfile $PROJECT_DIR/gunicorn-access.log \
  --error-logfile $PROJECT_DIR/gunicorn-error.log
