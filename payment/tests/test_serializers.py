from datetime import date, timedelta
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from booking.models import Booking
from guest.models import Guest
from payment.models import Payment
from room.models import Room


class PaymentAPITestCase(APITestCase):

    def setUp(self):
        self.user = Guest.objects.create_user(
            email="user@test.com",
            password="password123"
        )

        self.client.force_authenticate(user=self.user)

        self.room = Room.objects.create(
            number="101",
            type=Room.RoomType.SINGLE,
            price_per_night=Decimal("100.00"),
            capacity=1,
        )

        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in_date=date.today() + timedelta(days=1),
            check_out_date=date.today() + timedelta(days=3),
            status=Booking.BookingStatus.BOOKED,
            price_per_night=self.room.price_per_night,
        )

    def test_payment_list_serialization(self):
        Payment.objects.create(
            booking=self.booking,
            status=Payment.PaymentStatus.PAID,
            type=Payment.PaymentType.BOOKING,
            session_url="https://example.com/session",
            session_id="sess_123",
            money_to_pay=Decimal("150.00"),
        )

        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payment_create_not_allowed(self):
        response = self.client.post(
            "/api/payments/",
            {"booking": self.booking.id}
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_payment_create_invalid_booking(self):
        response = self.client.post("/api/payments/", {"booking": 999999})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
