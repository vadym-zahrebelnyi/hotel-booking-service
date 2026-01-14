from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ReadOnlyModelViewSet

from booking.filters import BookingFilter
from booking.models import Booking
from booking.serializers import BookingReadSerializer


class BookingViewSet(ReadOnlyModelViewSet):
    queryset = Booking.objects.select_related("room", "user")
    serializer_class = BookingReadSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilter

    def get_queryset(self):
        queryset = Booking.objects.select_related("room", "user")

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(user=self.request.user)


