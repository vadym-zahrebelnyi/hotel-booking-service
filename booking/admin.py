from django.contrib import admin

from booking.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "user",
        "check_in_date",
        "check_out_date",
        "actual_check_out_date",
        "status",
        "price_per_night",
    )

    list_filter = (
        "status",
        "check_in_date",
        "check_out_date",
        "room",
    )

    search_fields = (
        "user__email",
        "room__number",
    )

    ordering = ("-check_in_date",)
