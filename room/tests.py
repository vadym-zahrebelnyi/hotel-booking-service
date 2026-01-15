from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from booking.models import Booking
from room.models import Room


def rooms_url():
    return reverse("room:rooms-list")


def room_detail_url(room_id: int) -> str:
    return reverse("room:rooms-detail", args=[room_id])

def room_calendar_url(room_id:int) -> str:
    return reverse("room:rooms-get-calendar", args=[room_id])

def create_user(**params):
    defaults = {
        "email": "user@test.com",
        "password": "test12345",
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)


def create_admin(**params):
    defaults = {
        "email": "admin@test.com",
        "password": "test12345",
    }
    defaults.update(params)
    return get_user_model().objects.create_superuser(**defaults)


def create_room(**params):
    defaults = {
        "number": "101",
        "type": Room.RoomType.SINGLE,
        "price_per_night": "50.00",
        "capacity": 2,
    }
    defaults.update(params)
    return Room.objects.create(**defaults)


class PublicRoomApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_rooms_allowed_for_anon(self):
        create_room(number="101")
        create_room(number="102")

        res = self.client.get(rooms_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_create_room_unauthorized_for_anon(self):
        payload = {
            "number": "777",
            "type": Room.RoomType.SINGLE,
            "price_per_night": "99.99",
            "capacity": 1,
        }

        res = self.client.post(rooms_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRoomApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@test.com", password="test12345")
        self.client.force_authenticate(self.user)

    def test_create_room_forbidden_for_non_admin(self):
        payload = {
            "number": "888",
            "type": Room.RoomType.SUITE,
            "price_per_night": "200.00",
            "capacity": 4,
        }

        res = self.client.post(rooms_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_room_forbidden_for_non_admin(self):
        room = create_room(number="150")

        payload = {"capacity": 10}

        res = self.client.patch(room_detail_url(room.id), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_room_forbidden_for_non_admin(self):
        room = create_room(number="151")

        res = self.client.delete(room_detail_url(room.id))

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminRoomApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin(email="admin@test.com", password="test12345")
        self.client.force_authenticate(self.admin)

    def test_create_room_success(self):
        payload = {
            "number": "900",
            "type": Room.RoomType.DOUBLE,
            "price_per_night": "120.00",
            "capacity": 3,
        }

        res = self.client.post(rooms_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Room.objects.filter(number="900").exists())

    def test_patch_room_success(self):
        room = create_room(number="901", capacity=2)

        payload = {"capacity": 5}

        res = self.client.patch(room_detail_url(room.id), payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual(room.capacity, 5)

    def test_put_room_success(self):
        room = create_room(number="902")

        payload = {
            "number": "902",
            "type": Room.RoomType.SUITE,
            "price_per_night": "300.00",
            "capacity": 6,
        }

        res = self.client.put(room_detail_url(room.id), payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual(room.type, Room.RoomType.SUITE)
        self.assertEqual(str(room.price_per_night), "300.00")
        self.assertEqual(room.capacity, 6)

    def test_delete_room_success(self):
        room = create_room(number="903")

        res = self.client.delete(room_detail_url(room.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Room.objects.filter(id=room.id).exists())

    def test_filter_by_type(self):
        create_room(number="1001", type=Room.RoomType.SINGLE)
        create_room(number="1002", type=Room.RoomType.SUITE)

        res = self.client.get(rooms_url(), {"type": Room.RoomType.SUITE})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["number"], "1002")

    def test_filter_by_capacity(self):
        create_room(number="1101", capacity=2)
        create_room(number="1102", capacity=4)

        res = self.client.get(rooms_url(), {"capacity": 4})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["number"], "1102")

class RoomCalendarApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@test.com", password="test12345")
        self.client.force_authenticate(self.user)
        self.room = create_room(number="500")
        self.url = room_calendar_url(room_id=self.room.id)

    def test_get_calendar_success(self):
        check_in = date.today() + timedelta(days=2)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            room=self.room,
            user=self.user,
            status=Booking.BookingStatus.BOOKED,
            price_per_night=50,
            check_in_date=check_in,
            check_out_date=check_out,
        )
        date_from = date.today()
        date_to = date.today() + timedelta(days=4)

        res = self.client.get(self.url, {"date_from": date_from, "date_to": date_to})

        self.assertEqual(res.status_code, 200)
        for day_data in res.data:
            day = date.fromisoformat(day_data["date"])
            if check_in <= day < check_out:
                self.assertFalse(day_data["available"])
            else:
                self.assertTrue(day_data["available"])

    def test_calendar_missing_dates_returns_400(self):
        res = self.client.get(self.url, {"date_from": date.today()})
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.data)

        res = self.client.get(self.url, {"date_to": date.today()})
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.data)

    def test_calendar_invalid_date_range_returns_400(self):
        date_from = date.today()
        date_to = date.today() - timedelta(days=1)
        res = self.client.get(self.url, {"date_from": date_from, "date_to": date_to})
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.data)

class PublicRoomCalendarApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.room = create_room(number="600")
        self.url = room_calendar_url(room_id=self.room.id)

    def test_get_calendar_success_for_anonymous(self):
        date_from = date.today()
        date_to = date.today() + timedelta(days=2)

        res = self.client.get(self.url, {"date_from": date_from, "date_to": date_to})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

        for day_data in res.data:
            self.assertIn("date", day_data)
            self.assertIn("available", day_data)

    def test_get_calendar_with_bookings_for_anonymous(self):
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            room=self.room,
            user=create_user(email="anon@test.com"),
            status=Booking.BookingStatus.ACTIVE,
            price_per_night=50,
            check_in_date=check_in,
            check_out_date=check_out,
        )

        date_from = date.today()
        date_to = date.today() + timedelta(days=3)

        res = self.client.get(self.url, {"date_from": date_from, "date_to": date_to})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        for day_data in res.data:
            day = date.fromisoformat(day_data["date"])
            if check_in <= day < check_out:
                self.assertFalse(day_data["available"])
            else:
                self.assertTrue(day_data["available"])

    def test_calendar_missing_dates_returns_400_for_anonymous(self):
        res = self.client.get(self.url, {"date_from": date.today()})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.get(self.url, {"date_to": date.today()})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calendar_invalid_date_range_returns_400_for_anonymous(self):
        date_from = date.today()
        date_to = date.today() - timedelta(days=1)

        res = self.client.get(self.url, {"date_from": date_from, "date_to": date_to})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
