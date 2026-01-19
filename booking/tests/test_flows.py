from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from booking.models import Booking
from room.models import Room


class BookingFlowsTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

        self.room = Room.objects.create(
            number="101",
            type="Single",
            price_per_night=100,
            capacity=2,
        )

    def create_booking(
        self, booking_status=Booking.BookingStatus.BOOKED, check_in_offset_days=5
    ):
        today = timezone.localdate()
        booking = Booking.objects.create(
            room=self.room,
            user=self.user,
            check_in_date=today + timedelta(days=check_in_offset_days),
            check_out_date=today + timedelta(days=check_in_offset_days + 2),
            status=booking_status,
            price_per_night=100,
        )
        return booking

    def test_cancel_booking_ok(self):
        booking = self.create_booking(booking_status=Booking.BookingStatus.BOOKED)

        url = reverse("booking:booking-cancel", args=[booking.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.BookingStatus.CANCELLED)

    def test_cancel_booking_not_booked(self):
        booking = self.create_booking(booking_status=Booking.BookingStatus.ACTIVE)

        url = reverse("booking:booking-cancel", args=[booking.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("booking.views.create_checkout_session")
    def test_check_in_ok(self, mock_create_session):
        mock_create_session.return_value = {
            "id": "cs_test_mocked",
            "url": "https://stripe.test/session",
        }

        booking = self.create_booking(
            booking_status=Booking.BookingStatus.BOOKED,
            check_in_offset_days=0,
        )
        url = reverse("booking:booking-check-in", args=[booking.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.BookingStatus.BOOKED)
        mock_create_session.assert_called_once()

    def test_check_out_ok(self):
        booking = self.create_booking(booking_status=Booking.BookingStatus.ACTIVE)

        url = reverse("booking:booking-check-out", args=[booking.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.BookingStatus.COMPLETED)
