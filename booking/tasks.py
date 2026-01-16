from celery import shared_task
from booking.services import mark_no_show_bookings


@shared_task
def mark_no_show_bookings_task():
    return mark_no_show_bookings()
