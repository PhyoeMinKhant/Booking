from datetime import timedelta

from django.db import models
from django.utils import timezone

from accounts.models import Profile
from rooms.models import Room


class Booking(models.Model):
	PENDING_PAYMENT_EXPIRY_HOURS = 3

	class PaymentOption(models.TextChoices):
		PAY_NOW = "pay_now", "Pay now"
		PAY_LATER = "pay_later", "Pay later"

	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		CONFIRMED = "confirmed", "Confirmed"
		COMPLETED = "completed", "Completed"
		CANCELED = "canceled", "Canceled"
		EXPIRED = "expired", "Expired"

	guest = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="bookings")
	room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
	guest_name = models.CharField(max_length=150)
	guest_email = models.EmailField()
	guest_phone = models.CharField(max_length=30, blank=True, default="")
	rooms_count = models.PositiveIntegerField(default=1)
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

	STATUS_NOTIFICATION_MESSAGES = {
		Status.PENDING: "Booking is pending payment.",
		Status.CONFIRMED: "Booking is confirmed.",
		Status.COMPLETED: "Booking is completed.",
		Status.CANCELED: "Booking is canceled.",
		Status.EXPIRED: "Booking expired due to unpaid balance.",
	}

	def save(self, *args, **kwargs):
		was_adding = self._state.adding
		previous_status = None
		if not was_adding and self.pk:
			previous_status = (
				Booking.objects.filter(id=self.pk).values_list("status", flat=True).first()
			)

		if was_adding:
			if self.payment_option == self.PaymentOption.PAY_NOW:
				self.status = self.Status.CONFIRMED
			else:
				self.status = self.Status.PENDING
		super().save(*args, **kwargs)

		if was_adding or previous_status != self.status:
			self.create_status_notifications()

	def create_status_notifications(self):
		if not self.pk or not self.room_id or not self.guest_id:
			return

		room_hotel_id = Room.objects.filter(id=self.room_id).values_list("hotel_id", flat=True).first()
		if room_hotel_id is None:
			return

		message = self.STATUS_NOTIFICATION_MESSAGES.get(self.status, "Booking status updated.")
		recipient_ids = {self.guest_id, room_hotel_id}

		for recipient_id in recipient_ids:
			BookingNotification.objects.get_or_create(
				recipient_id=recipient_id,
				booking=self,
				status=self.status,
				defaults={
					"message": message,
				},
			)

	def should_expire_pending_payment(self, *, now=None) -> bool:
		now = now or timezone.now()
		if self.status != self.Status.PENDING:
			return False
		if self.payment_option != self.PaymentOption.PAY_LATER:
			return False
		if not self.created_at:
			return False
		expiry_time = self.created_at + timedelta(hours=self.PENDING_PAYMENT_EXPIRY_HOURS)
		return now >= expiry_time

	def should_complete_confirmed_booking(self, *, now=None) -> bool:
		now = now or timezone.now()
		if self.status != self.Status.CONFIRMED:
			return False
		if not self.room_id or not self.room.checkout_date:
			return False
		return now.date() >= self.room.checkout_date

	def refresh_status(self, *, now=None, save=True):
		if self.should_expire_pending_payment(now=now):
			self.status = self.Status.EXPIRED
		elif self.should_complete_confirmed_booking(now=now):
			self.status = self.Status.COMPLETED
		else:
			return self.status
		if save and self.pk:
			self.save(update_fields=["status"])
		return self.status

	def __str__(self) -> str:
		return f"Booking #{self.id} - {self.guest_name}"


class BookingNotification(models.Model):
	recipient = models.ForeignKey(
		Profile,
		on_delete=models.CASCADE,
		related_name="booking_notifications",
	)
	booking = models.ForeignKey(
		Booking,
		on_delete=models.CASCADE,
		related_name="notifications",
	)
	status = models.CharField(max_length=20, choices=Booking.Status.choices)
	message = models.CharField(max_length=255)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ("-created_at",)
		constraints = [
			models.UniqueConstraint(
				fields=["recipient", "booking", "status"],
				name="unique_booking_status_notification_per_recipient",
			)
		]

	def __str__(self) -> str:
		return f"{self.recipient.full_name}: booking #{self.booking_id} {self.status}"


class BookingReview(models.Model):
	class Rating(models.IntegerChoices):
		ONE = 1, "1"
		TWO = 2, "2"
		THREE = 3, "3"
		FOUR = 4, "4"
		FIVE = 5, "5"

	booking = models.OneToOneField(
		Booking,
		on_delete=models.CASCADE,
		related_name="review",
	)
	rating = models.PositiveSmallIntegerField(choices=Rating.choices)
	comment = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("-created_at",)

	def __str__(self) -> str:
		return f"Review for booking #{self.booking_id} ({self.rating}/5)"
