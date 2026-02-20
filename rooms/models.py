from django.db import models

from accounts.models import Profile


class RoomType(models.Model):
	name = models.CharField(max_length=100, unique=True)

	def __str__(self) -> str:
		return self.name


class Room(models.Model):
	hotel = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="rooms")
	room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT)
	capacity = models.PositiveIntegerField()
	rate_per_night = models.DecimalField(max_digits=8, decimal_places=2)
	available_rooms = models.PositiveIntegerField()
	checkin_date = models.DateField()
	checkout_date = models.DateField()
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return f"{self.room_type} ({self.capacity} guests)"
