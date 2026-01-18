from datetime import date

from rest_framework import serializers

from booking.models import Booking
from payment.serializers import PaymentSerializer


class BookingReadSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source="room.number", read_only=True)
    room_type = serializers.CharField(source="room.type", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    total_nights = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "room",
            "room_number",
            "room_type",
            "user",
            "user_email",
            "check_in_date",
            "check_out_date",
            "actual_check_out_date",
            "status",
            "price_per_night",
            "total_nights",
            "total_price",
            "payments",
        )

    def get_total_nights(self, obj):
        return (obj.check_out_date - obj.check_in_date).days

    def get_total_price(self, obj):
        nights = (obj.check_out_date - obj.check_in_date).days
        return obj.price_per_night * nights


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings with validation."""

    class Meta:
        model = Booking
        fields = ("room", "check_in_date", "check_out_date")

    def validate_check_in_date(self, value):  # Додано
        """Validate that check-in date is not in the past."""
        if value < date.today():
            raise serializers.ValidationError("Check-in date cannot be in the past.")
        return value

    def validate(self, attrs):
        check_in = attrs["check_in_date"]
        check_out = attrs["check_out_date"]
        room = attrs["room"]

        if check_out <= check_in:
            raise serializers.ValidationError(
                "Check-out date must be after check-in date."
            )

        overlapping = Booking.objects.filter(
            room=room,
            status__in=[
                Booking.BookingStatus.BOOKED,
                Booking.BookingStatus.ACTIVE,
            ],
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
        )

        if overlapping.exists():
            raise serializers.ValidationError(
                "Room is not available for selected dates."
            )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        room = validated_data["room"]

        return Booking.objects.create(
            user=user,
            price_per_night=room.price_per_night,
            status=Booking.BookingStatus.BOOKED,
            **validated_data,
        )
