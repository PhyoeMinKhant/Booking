from django.contrib import admin

from .models import Booking, BookingNotification


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "guest",
        "room",
        "rooms_count",
        "payment_option",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_option")
    search_fields = ("guest_name", "guest_email")


@admin.register(BookingNotification)
class BookingNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "booking", "status", "is_read", "created_at")
    list_filter = ("status", "is_read")
    search_fields = ("message",)
