from django.db import models

from accounts.models import Profile
from rooms.models import Room


class Booking(models.Model):
	class PaymentOption(models.TextChoices):
		PAY_NOW = "pay_now", "Pay now"
		PAY_LATER = "pay_later", "Pay later"

	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		CONFIRMED = "confirmed", "Confirmed"
		COMPLETED = "completed", "Completed"
		CANCELED = "canceled", "Canceled"

	guest = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="bookings")
	room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
	guest_name = models.CharField(max_length=150)
	guest_email = models.EmailField()
	guest_phone = models.CharField(max_length=30, blank=True, default="")
	payment_option = models.CharField(
		max_length=20,
		choices=PaymentOption.choices,
		default=PaymentOption.PAY_LATER,
	)
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.PENDING,
	)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return f"Booking #{self.id} - {self.guest_name}"
