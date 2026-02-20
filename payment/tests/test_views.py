from datetime import date, timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from booking.models import Booking
from payment.models import Payment
from room.models import Room

PAYMENT_LIST_URL = reverse("payments:payment-list")
PAYMENT_SUCCESS_URL = reverse("payments:success")
PAYMENT_CANCEL_URL = reverse("payments:cancel")
STRIPE_WEBHOOK_URL = reverse("payments:stripe-webhook")


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class AuthenticatedPaymentApiTests(APITestCase):
    def setUp(self):
        """Set up a user, room, booking and payment for tests."""
        self.user = create_user(email="test@test.com", password="testpass123")
        self.client.force_authenticate(self.user)

        self.room = Room.objects.create(number="101", capacity=2, price_per_night=100)

        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in_date=date.today(),
            check_out_date=date.today() + timedelta(days=2),
            status=Booking.BookingStatus.BOOKED,
            price_per_night=100,
        )

        self.payment = Payment.objects.create(
            booking=self.booking,
            type=Payment.PaymentType.BOOKING,
            status=Payment.PaymentStatus.PENDING,
            session_id="sess_123",
            session_url="https://stripe.com/checkout/sess_123",
            money_to_pay=200.00,
        )

    def test_payment_success_view_authenticated(self):
        """Test the payment success page for authenticated user."""
        res = self.client.get(
            PAYMENT_SUCCESS_URL, {"session_id": self.payment.session_id}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.data["detail"],
            "Thank you for your payment! Your booking is being processed.",
        )
        self.assertEqual(res.data["payment_status"], Payment.PaymentStatus.PENDING)

    def test_payment_cancel_view_authenticated(self):
        """Test the payment cancel page for authenticated user."""
        res = self.client.get(PAYMENT_CANCEL_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.data["detail"], "Payment was cancelled. You can complete it later."
        )

    @mock.patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_checkout_completed(self, mock_construct_event):
        """Test updating Payment status on successful Stripe checkout."""
        mock_event = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": self.payment.session_id}},
        }
        mock_construct_event.return_value = mock_event

        res = self.client.post(
            STRIPE_WEBHOOK_URL, data={}, content_type="application/json"
        )
        self.payment.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.payment.status, Payment.PaymentStatus.PAID)

    @mock.patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_session_not_found(self, mock_construct_event):
        """Test response when Stripe session_id is not found in Payment."""
        mock_event = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "wrong_session"}},
        }
        mock_construct_event.return_value = mock_event

        res = self.client.post(
            STRIPE_WEBHOOK_URL, data={}, content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
