from rest_framework import serializers
from room.models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("id", "number", "type", "price_per_night", "capacity")


class RoomCalendarSerializer(serializers.Serializer):
    date = serializers.DateField()
    available = serializers.BooleanField()
