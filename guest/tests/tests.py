from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

CREATE_USER_URL = reverse("guest:create")
ME_URL = reverse("guest:manage")
LOGIN_URL = reverse("guest:token_obtain_pair")

def create_user(**params):
    return get_user_model().objects.create_user(**params)


class UnauthenticatedUserApiTests(APITestCase):
    """Tests for unauthenticated user API"""

    def test_create_user_success(self):
        payload = {
            "email": "user@test.com",
            "password": "testpass123",
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_create_user_with_wrong_email(self):
        payload = {
            "email": "user",
            "password": "testpass123",
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            get_user_model().objects.filter(email=payload["email"]).exists()
        )

    def test_password_too_short(self):
        payload = {
            "email": "user@test.com",
            "password": "123",
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            get_user_model().objects.filter(email=payload["email"]).exists()
        )
    def test_cannot_set_is_staff_on_register(self):
        payload = {
            "email": "user@test.com",
            "password": "testpass123",
            "is_staff": True,
        }
        self.client.post(CREATE_USER_URL, payload)

        user = get_user_model().objects.get(email=payload["email"])
        self.assertFalse(user.is_staff)

    def test_auth_required_for_me(self):
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_login(self):
        payload = {
            "email": "user@test.com",
            "password": "testpass123",
        }
        create_user(**payload)
        res = self.client.post(LOGIN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["refresh"])
        self.assertTrue(res.data["access"])

    def test_user_with_wrong_credentials(self):
        payload = {
            "email": "user@test.com",
            "password": "testpass123",
        }
        create_user(**payload)
        payload["email"] = "wrong@email.com"
        res = self.client.post(LOGIN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthenticatedUserApiTests(APITestCase):
    """Tests for authenticated user API"""

    def setUp(self):
        self.user = create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_profile_success(self):
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.user.email)
        self.assertEqual(res.data["is_staff"], self.user.is_staff)

    def test_partial_update_user_profile(self):
        payload = {
            "email": "newemail@test.com",
            "password": "testpass123",
        }
        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, payload["email"])
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_user_profile(self):
        payload = {
            "email": "newemail@test.com",
            "password": "newpassword123",
        }
        res = self.client.put(ME_URL, payload)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, payload["email"])
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
