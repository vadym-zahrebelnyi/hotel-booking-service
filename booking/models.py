from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F, ForeignKey, Q

from room.models import Room


class Booking(models.Model):
    """
    Hotel room booking model.
    Represents a reservation for a hotel room by a guest, including
    check-in/check-out dates, booking status, and pricing information.
    """
    class BookingStatus(models.TextChoices):
        """Enumeration of possible booking statuses."""
        BOOKED = "BOOKED"
        ACTIVE = "ACTIVE"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"
        NO_SHOW = "NO_SHOW"

    room = ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    user = ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="bookings"
    )
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    actual_check_out_date = models.DateField(null=True)
    status = models.CharField(choices=BookingStatus, max_length=20)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        """Meta configuration for Booking model."""
        constraints = [
            models.CheckConstraint(
                check=Q(check_out_date__gt=F("check_in_date")),
                name="check_out_after_check_in",
            ),
        ]
