from django.db import models


class Room(models.Model):
    class RoomType(models.TextChoices):
        SINGLE = "Single"
        DOUBLE = "Double"
        SUITE = "Suite"

    number = models.CharField(max_length=255, unique=True)
    type = models.CharField(choices=RoomType.choices, max_length=20)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField()
