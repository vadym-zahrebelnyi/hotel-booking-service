from django.db import models
from django.db.models import ForeignKey

from booking.models import Booking


class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "Pending"
        PAID = "Paid"
        EXPIRED = "Expired"

    class PaymentType(models.TextChoices):
        BOOKING = "Booking"
        CANCELLATION_FEE = "Cancellation fee"
        NO_SHOW_FEE = "No show fee"
        OVERSTAY_FEE = "Overstay fee"

    status = models.CharField(
        choices=PaymentStatus,
        max_length=20,
        default=PaymentStatus.PENDING
    )
    type = models.CharField(choices=PaymentType, max_length=20)
    booking = ForeignKey(Booking, related_name="payments",
                         on_delete=models.CASCADE)
    session_url = models.URLField(max_length=500)
    session_id = models.CharField(max_length=255)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
