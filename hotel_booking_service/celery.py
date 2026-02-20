import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hotel_booking_service.settings")

app = Celery("hotel_booking_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
