from django.contrib import admin

from room.models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "type", "capacity", "price_per_night")
    search_fields = ("number",)
    list_filter = ("type", "capacity")
