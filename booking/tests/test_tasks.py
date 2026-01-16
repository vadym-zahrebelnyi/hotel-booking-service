from django.test import TestCase
from django.utils.timezone import localdate
from datetime import timedelta
from unittest.mock import patch

from booking.models import Booking
from booking.tasks import mark_no_show_bookings, notify_no_show_telegram
from room.models import Room
from guest.models import Guest


class MarkNoShowBookingsTestCase(TestCase):
    """Tests for mark_no_show_bookings task"""

    def setUp(self):
        """Create test data"""
        self.user = Guest.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )

        self.room = Room.objects.create(
            number='101',
            type=Room.RoomType.SINGLE,
            price_per_night=100.00,
            capacity=1
        )

    def test_marks_past_bookings_as_no_show(self):
        """Test that bookings with past check-in dates are marked as NO_SHOW"""
        past_booking = Booking.objects.create(
            room=self.room,
            user=self.user,
            check_in_date=localdate() - timedelta(days=1),
            check_out_date=localdate() + timedelta(days=2),
            status=Booking.BookingStatus.BOOKED,
            price_per_night=100.00
        )

        result = mark_no_show_bookings()

        past_booking.refresh_from_db()
        self.assertEqual(past_booking.status, Booking.BookingStatus.NO_SHOW)
        self.assertIn("Marked 1 bookings", result)

    def test_does_not_mark_today_bookings(self):
        """Test that bookings with today's check-in date are NOT marked"""
        today_booking = Booking.objects.create(
            room=self.room,
            user=self.user,
            check_in_date=localdate(),
            check_out_date=localdate() + timedelta(days=3),
            status=Booking.BookingStatus.BOOKED,
            price_per_night=100.00
        )

        mark_no_show_bookings()

        today_booking.refresh_from_db()
        self.assertEqual(today_booking.status, Booking.BookingStatus.BOOKED)

    def test_does_not_mark_future_bookings(self):
        """Test that future bookings are NOT marked"""
        future_booking = Booking.objects.create(
            room=self.room,
            user=self.user,
            check_in_date=localdate() + timedelta(days=1),
            check_out_date=localdate() + timedelta(days=4),
            status=Booking.BookingStatus.BOOKED,
            price_per_night=100.00
        )

        mark_no_show_bookings()

        future_booking.refresh_from_db()
        self.assertEqual(future_booking.status, Booking.BookingStatus.BOOKED)

    def test_marks_multiple_past_bookings(self):
        """Test that multiple past bookings are all marked"""
        for i in range(3):
            Booking.objects.create(
                room=self.room,
                user=self.user,
                check_in_date=localdate() - timedelta(days=i + 1),
                check_out_date=localdate() + timedelta(days=2),
                status=Booking.BookingStatus.BOOKED,
                price_per_night=100.00
            )

        result = mark_no_show_bookings()

        no_show_count = Booking.objects.filter(
            status=Booking.BookingStatus.NO_SHOW
        ).count()
        self.assertEqual(no_show_count, 3)
        self.assertIn("Marked 3 bookings", result)
