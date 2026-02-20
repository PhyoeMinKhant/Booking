from django.contrib import admin

from .models import Room, RoomType


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	list_display = (
		"hotel",
		"room_type",
		"capacity",
		"rate_per_night",
		"available_rooms",
		"checkin_date",
		"checkout_date",
	)
	list_filter = ("room_type", "checkin_date", "checkout_date")
	search_fields = ("hotel__full_name",)
