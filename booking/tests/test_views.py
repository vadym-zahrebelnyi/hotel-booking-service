from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from booking.models import Booking
from payment.models import Payment
from room.models import Room


class BookingViewSetTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )

        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com", password="adminpass123"
        )

        self.room = Room.objects.create(
            number="101", type="DOUBLE", price_per_night=100, capacity=2
        )

        self.user_booking = Booking.objects.create(
            room=self.room,
            user=self.user,
            check_in_date=date.today() + timedelta(days=1),
            check_out_date=date.today() + timedelta(days=3),
            price_per_night=100,
            status=Booking.BookingStatus.BOOKED,
        )

        self.list_url = "/api/booking/"

    def test_authentication_required(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_bookings(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.user_booking.id)

    def test_admin_sees_all_bookings(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Booking.objects.count(),
            len(response.data),
        )

    def test_filter_by_status(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url, {"status": "BOOKED"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(b["status"] == "BOOKED" for b in response.data))

    def test_filter_by_user_id(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url, {"user": self.user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"], self.user.id)

    # @patch("booking.views.create_checkout_session")
    # def test_create_booking_success(self, mock_create_checkout_session):
    #     self.client.force_authenticate(user=self.user)
    #
    #     mock_create_checkout_session.return_value = {
    #         "id": "cs_test_123",
    #         "url": "https://checkout.stripe.com/test",
    #     }
    #
    #     payload = {
    #         "room": self.room.id,
    #         "check_in_date": str(date.today() + timedelta(days=10)),
    #         "check_out_date": str(date.today() + timedelta(days=12)),
    #     }
    #
    #     response = self.client.post(self.list_url, payload, format="json")
    #
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(response.data["user"], self.user.id)
    #     self.assertEqual(response.data["price_per_night"], "100.00")
    #     self.assertEqual(response.data["status"], Booking.BookingStatus.BOOKED)
    #
    #     mock_create_checkout_session.assert_called_once()

    def test_create_booking_overlap_fails(self):
        self.client.force_authenticate(user=self.user)

        payload = {
            "room": self.room.id,
            "check_in_date": str(date.today() + timedelta(days=2)),
            "check_out_date": str(date.today() + timedelta(days=4)),
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Room is not available", str(response.data))

    def test_create_booking_in_past_fails(self):
        self.client.force_authenticate(user=self.user)

        payload = {
            "room": self.room.id,
            "check_in_date": str(date.today() - timedelta(days=1)),
            "check_out_date": str(date.today() + timedelta(days=1)),
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("check_in_date", response.data)

    def test_create_booking_fails_if_user_has_pending_payment(self):
        self.client.force_authenticate(user=self.user)
        Payment.objects.create(
            booking=self.user_booking,
            status=Payment.PaymentStatus.PENDING,
            money_to_pay=200,
        )
        payload = {
            "room": self.room.id,
            "check_in_date": str(date.today() + timedelta(days=10)),
            "check_out_date": str(date.today() + timedelta(days=12)),
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "You cannot create a new booking while you have a pending payment.",
            str(response.data),
        )
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)

    def test_create_booking_allowed_if_no_pending_payment(self):
        self.client.force_authenticate(user=self.user)
        Payment.objects.create(
            booking=self.user_booking,
            status=Payment.PaymentStatus.PAID,
            money_to_pay=200,
        )
        payload = {
            "room": self.room.id,
            "check_in_date": str(date.today() + timedelta(days=10)),
            "check_out_date": str(date.today() + timedelta(days=12)),
        }
        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 2)
