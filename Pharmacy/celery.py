# Pharmacy/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Pharmacy.settings')

app = Celery('Pharmacy')

# Load task modules from all registered Django apps
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Optional: see debug logs
app.conf.update(
    task_track_started=True,
    task_time_limit=300,
)
app.conf.beat_schedule = settings.CELERY_BEAT_SCHEDULE
