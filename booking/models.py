from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import ForeignKey, Q, F

from room.models import Room


class Booking(models.Model):
    class BookingStatus(models.TextChoices):
        BOOKED = "Booked"
        ACTIVE = "Active"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"
        NO_SHOW = "No show"

    room = ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    user = ForeignKey(get_user_model(), on_delete=models.CASCADE,
                      related_name="bookings")
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    actual_check_out_date = models.DateField(null=True)
    status = models.CharField(choices=BookingStatus, max_length=20)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(check_out_date__gt=F("check_in_date")),
                name = "check_out_after_check_in",
            ),
        ]
