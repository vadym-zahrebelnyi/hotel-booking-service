from rest_framework.routers import DefaultRouter
from room.views import RoomViewSet

app_name = "room"

router = DefaultRouter()
router.register("rooms", RoomViewSet, basename="rooms")

urlpatterns = router.urls
