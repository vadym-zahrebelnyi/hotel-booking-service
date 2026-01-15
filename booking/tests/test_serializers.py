from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model

from booking.serializers import BookingCreateSerializer
from booking.models import Booking
from room.models import Room


class BookingCreateSerializerTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password123"
        )
        self.room = Room.objects.create(
            number="101",
            type="DOUBLE",
            price_per_night=100,
            capacity=2
        )

    def test_check_in_date_in_past_fails(self):
        serializer = BookingCreateSerializer(
            data={
                "room": self.room.id,
                "check_in_date": date.today() - timedelta(days=1),
                "check_out_date": date.today() + timedelta(days=1),
            },
            context={"request": type("obj", (), {"user": self.user})()},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("check_in_date", serializer.errors)

    def test_check_out_before_check_in_fails(self):
        serializer = BookingCreateSerializer(
            data={
                "room": self.room.id,
                "check_in_date": date.today() + timedelta(days=2),
                "check_out_date": date.today() + timedelta(days=1),
            },
            context={"request": type("obj", (), {"user": self.user})()},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_booking_overlap_fails(self):
        Booking.objects.create(
            room=self.room,
            user=self.user,
            check_in_date=date.today() + timedelta(days=5),
            check_out_date=date.today() + timedelta(days=7),
            price_per_night=100,
            status=Booking.BookingStatus.BOOKED,
        )

        serializer = BookingCreateSerializer(
            data={
                "room": self.room.id,
                "check_in_date": date.today() + timedelta(days=6),
                "check_out_date": date.today() + timedelta(days=8),
            },
            context={"request": type("obj", (), {"user": self.user})()},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("Room is not available", str(serializer.errors))

    def test_valid_booking_creates_booking(self):
        serializer = BookingCreateSerializer(
            data={
                "room": self.room.id,
                "check_in_date": date.today() + timedelta(days=1),
                "check_out_date": date.today() + timedelta(days=3),
            },
            context={"request": type("obj", (), {"user": self.user})()},
        )

        self.assertTrue(serializer.is_valid())
        booking = serializer.save()

        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.price_per_night, self.room.price_per_night)
        self.assertEqual(booking.status, Booking.BookingStatus.BOOKED)
