import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'staging_creworder_backend.settings')

app = Celery('staging_creworder_backend')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
