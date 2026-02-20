from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/user/", include(("guest.urls", "guest"), namespace="guest")),
    path("api/", include("booking.urls", namespace="bookings")),
    path("api/", include(("room.urls", "room"), namespace="room")),
    path("api/payments/", include("payment.urls"), name="payments"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("__debug__/", include("debug_toolbar.urls")),
]
