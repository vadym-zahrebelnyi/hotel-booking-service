from django.urls import path

from payment.views import TestStripeSessionView


app_name = "payments"

urlpatterns = [
    path("test-session/", TestStripeSessionView.as_view(), name="test-session"),
]