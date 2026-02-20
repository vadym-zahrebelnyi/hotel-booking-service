from django.urls import include, path
from rest_framework.routers import DefaultRouter

from booking.views import BookingViewSet

router = DefaultRouter()
router.register("booking", BookingViewSet, basename="booking")

urlpatterns = [path("", include(router.urls))]

app_name = "booking"
