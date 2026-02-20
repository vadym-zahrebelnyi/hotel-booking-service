from rest_framework import serializers

from room.models import Room


class RoomSerializer(serializers.ModelSerializer):
    """Serializer for Room model."""

    class Meta:
        model = Room
        fields = ("id", "number", "type", "price_per_night", "capacity")


class RoomCalendarSerializer(serializers.Serializer):
    """Serializer for room availability calendar response."""

    date = serializers.DateField()
    available = serializers.BooleanField()
