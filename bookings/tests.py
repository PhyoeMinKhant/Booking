import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from rooms.models import Room, RoomType

from .models import Booking, BookingNotification, BookingReview


class BookingStatusRulesTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		guest_user = user_model.objects.create_user(
			username="guest_user",
			email="guest@example.com",
			password="pass1234",
		)
		hotel_user = user_model.objects.create_user(
			username="hotel_user",
			email="hotel@example.com",
			password="pass1234",
		)

		self.guest_profile = guest_user.profile
		self.guest_profile.full_name = "Guest User"
		self.guest_profile.account_type = Profile.AccountType.GUEST
		self.guest_profile.save(update_fields=["full_name", "account_type"])

		self.hotel_profile = hotel_user.profile
		self.hotel_profile.full_name = "Hotel User"
		self.hotel_profile.account_type = Profile.AccountType.HOTEL
		self.hotel_profile.save(update_fields=["full_name", "account_type"])

		self.room_type = RoomType.objects.create(name="Deluxe")
		today = datetime.date.today()
		self.room = Room.objects.create(
			hotel=self.hotel_profile,
			room_type=self.room_type,
			capacity=2,
			rate_per_night="150.00",
			available_rooms=2,
			checkin_date=today + datetime.timedelta(days=1),
			checkout_date=today + datetime.timedelta(days=2),
		)

	def test_pay_later_booking_starts_pending(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)

		self.assertEqual(booking.status, Booking.Status.PENDING)
		self.assertEqual(
			BookingNotification.objects.filter(booking=booking, status=Booking.Status.PENDING).count(),
			2,
		)

	def test_pay_now_booking_starts_confirmed(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)

		self.assertEqual(booking.status, Booking.Status.CONFIRMED)

	def test_pending_pay_later_expires_after_twelve_hours(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)

		old_created_at = timezone.now() - datetime.timedelta(
			hours=Booking.PENDING_PAYMENT_EXPIRY_HOURS,
			minutes=1,
		)
		Booking.objects.filter(id=booking.id).update(created_at=old_created_at)
		booking.refresh_from_db()

		booking.refresh_status(now=timezone.now(), save=True)
		booking.refresh_from_db()

		self.assertEqual(booking.status, Booking.Status.EXPIRED)

	def test_pending_pay_later_remains_pending_before_twelve_hours(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)

		recent_created_at = timezone.now() - datetime.timedelta(
			hours=Booking.PENDING_PAYMENT_EXPIRY_HOURS - 1,
			minutes=59,
		)
		Booking.objects.filter(id=booking.id).update(created_at=recent_created_at)
		booking.refresh_from_db()

		booking.refresh_status(now=timezone.now(), save=True)
		booking.refresh_from_db()

		self.assertEqual(booking.status, Booking.Status.PENDING)

	def test_confirmed_booking_becomes_completed_after_checkout_date(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)

		now_after_checkout = timezone.make_aware(
			datetime.datetime.combine(
				self.room.checkout_date,
				datetime.time(hour=12, minute=0),
			)
		)

		booking.refresh_status(now=now_after_checkout, save=True)
		booking.refresh_from_db()

		self.assertEqual(booking.status, Booking.Status.COMPLETED)

	def test_confirmed_booking_stays_confirmed_before_checkout_date(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)

		now_before_checkout = timezone.make_aware(
			datetime.datetime.combine(
			self.room.checkout_date - datetime.timedelta(days=1),
			datetime.time(hour=12, minute=0),
			)
		)

		booking.refresh_status(now=now_before_checkout, save=True)
		booking.refresh_from_db()

		self.assertEqual(booking.status, Booking.Status.CONFIRMED)

	def test_checkout_decrements_available_rooms(self):
		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(
			reverse("booking_checkout", kwargs={"room_id": self.room.id}),
			{
				"guest_name": "Guest User",
				"guest_email": "guest@example.com",
				"guest_phone": "1234567890",
				"rooms_count": 2,
				"payment_option": Booking.PaymentOption.PAY_LATER,
			},
		)

		self.assertEqual(response.status_code, 302)
		self.room.refresh_from_db()
		self.assertEqual(self.room.available_rooms, 0)
		self.assertEqual(Booking.objects.filter(room=self.room).count(), 1)
		booking = Booking.objects.get(room=self.room)
		self.assertEqual(booking.rooms_count, 2)

	def test_checkout_rejects_when_requested_rooms_exceed_availability(self):
		self.client.login(username="guest_user", password="pass1234")
		url = reverse("booking_checkout", kwargs={"room_id": self.room.id})

		response = self.client.post(
			url,
			{
				"guest_name": "Guest User",
				"guest_email": "guest@example.com",
				"guest_phone": "1234567890",
				"rooms_count": 3,
				"payment_option": Booking.PaymentOption.PAY_LATER,
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "more than 2 room(s)")
		self.assertEqual(Booking.objects.filter(room=self.room).count(), 0)

	def test_checkout_allows_multiple_active_bookings_for_same_room(self):
		self.client.login(username="guest_user", password="pass1234")
		url = reverse("booking_checkout", kwargs={"room_id": self.room.id})

		first_response = self.client.post(
			url,
			{
				"guest_name": "Guest User",
				"guest_email": "guest@example.com",
				"guest_phone": "1234567890",
				"rooms_count": 1,
				"payment_option": Booking.PaymentOption.PAY_LATER,
			},
		)
		self.assertEqual(first_response.status_code, 302)

		second_response = self.client.post(
			url,
			{
				"guest_name": "Guest User",
				"guest_email": "guest@example.com",
				"guest_phone": "1234567890",
				"rooms_count": 1,
				"payment_option": Booking.PaymentOption.PAY_LATER,
			},
		)

		self.assertEqual(second_response.status_code, 302)
		self.assertEqual(Booking.objects.filter(room=self.room).count(), 2)
		self.room.refresh_from_db()
		self.assertEqual(self.room.available_rooms, 0)

	def test_expired_pending_booking_releases_room_inventory(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			rooms_count=2,
			payment_option=Booking.PaymentOption.PAY_LATER,
		)
		self.room.available_rooms = 0
		self.room.save(update_fields=["available_rooms"])

		old_created_at = timezone.now() - datetime.timedelta(
			hours=Booking.PENDING_PAYMENT_EXPIRY_HOURS,
			minutes=1,
		)
		Booking.objects.filter(id=booking.id).update(created_at=old_created_at)

		self.client.login(username="guest_user", password="pass1234")
		self.client.get(reverse("booking_history"))

		booking.refresh_from_db()
		self.room.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.EXPIRED)
		self.assertEqual(self.room.available_rooms, 2)

	def test_guest_can_cancel_own_pending_booking(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			rooms_count=2,
			payment_option=Booking.PaymentOption.PAY_LATER,
		)
		self.room.available_rooms = 0
		self.room.save(update_fields=["available_rooms"])

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(reverse("booking_cancel", kwargs={"booking_id": booking.id}))

		self.assertEqual(response.status_code, 302)
		booking.refresh_from_db()
		self.room.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.CANCELED)
		self.assertEqual(self.room.available_rooms, 2)

	def test_hotel_can_cancel_pending_booking_for_own_room(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			rooms_count=2,
			payment_option=Booking.PaymentOption.PAY_LATER,
		)
		self.room.available_rooms = 0
		self.room.save(update_fields=["available_rooms"])

		self.client.login(username="hotel_user", password="pass1234")
		response = self.client.post(reverse("hotel_booking_cancel", kwargs={"booking_id": booking.id}))

		self.assertEqual(response.status_code, 302)
		booking.refresh_from_db()
		self.room.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.CANCELED)
		self.assertEqual(self.room.available_rooms, 2)

	def test_cancel_action_ignores_non_pending_booking(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)
		self.room.available_rooms = 0
		self.room.save(update_fields=["available_rooms"])

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(reverse("booking_cancel", kwargs={"booking_id": booking.id}))

		self.assertEqual(response.status_code, 302)
		booking.refresh_from_db()
		self.room.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.CONFIRMED)
		self.assertEqual(self.room.available_rooms, 0)

	def test_guest_can_pay_now_for_pending_pay_later_booking(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(reverse("booking_pay_now", kwargs={"booking_id": booking.id}))

		self.assertEqual(response.status_code, 302)
		booking.refresh_from_db()
		self.assertEqual(booking.payment_option, Booking.PaymentOption.PAY_NOW)
		self.assertEqual(booking.status, Booking.Status.CONFIRMED)

	def test_status_change_creates_notifications_for_guest_and_hotel(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)

		booking.payment_option = Booking.PaymentOption.PAY_NOW
		booking.status = Booking.Status.CONFIRMED
		booking.save(update_fields=["payment_option", "status"])

		self.assertEqual(
			BookingNotification.objects.filter(
				booking=booking,
				status=Booking.Status.CONFIRMED,
			).count(),
			2,
		)

	def test_pay_now_action_ignores_non_pending_booking(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(reverse("booking_pay_now", kwargs={"booking_id": booking.id}))

		self.assertEqual(response.status_code, 302)
		booking.refresh_from_db()
		self.assertEqual(booking.payment_option, Booking.PaymentOption.PAY_NOW)
		self.assertEqual(booking.status, Booking.Status.CONFIRMED)

	def test_guest_history_marks_notification_as_read(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)
		notification = BookingNotification.objects.get(
			recipient=self.guest_profile,
			booking=booking,
			status=Booking.Status.PENDING,
		)

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.get(
			f"{reverse('booking_history')}?state=all&notification={notification.id}"
		)

		self.assertEqual(response.status_code, 200)
		notification.refresh_from_db()
		self.assertTrue(notification.is_read)

	def test_hotel_history_marks_notification_as_read(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)
		notification = BookingNotification.objects.get(
			recipient=self.hotel_profile,
			booking=booking,
			status=Booking.Status.PENDING,
		)

		self.client.login(username="hotel_user", password="pass1234")
		response = self.client.get(
			f"{reverse('hotel_booking_history')}?state=all&notification={notification.id}"
		)

		self.assertEqual(response.status_code, 200)
		notification.refresh_from_db()
		self.assertTrue(notification.is_read)

	def test_checkout_pay_now_credit_card_confirms_booking(self):
		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(
			reverse("booking_checkout", kwargs={"room_id": self.room.id}),
			{
				"guest_name": "Guest User",
				"guest_email": "guest@example.com",
				"guest_phone": "1234567890",
				"rooms_count": 1,
				"payment_option": Booking.PaymentOption.PAY_NOW,
				"payment_method": "credit_card",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("home"))
		booking = Booking.objects.latest("id")
		self.assertEqual(booking.payment_option, Booking.PaymentOption.PAY_NOW)
		self.assertEqual(booking.status, Booking.Status.CONFIRMED)

	def test_checkout_pay_now_digital_redirects_to_mock_payment(self):
		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(
			reverse("booking_checkout", kwargs={"room_id": self.room.id}),
			{
				"guest_name": "Guest User",
				"guest_email": "guest@example.com",
				"guest_phone": "1234567890",
				"rooms_count": 1,
				"payment_option": Booking.PaymentOption.PAY_NOW,
				"payment_method": "digital_payment",
			},
		)

		booking = Booking.objects.latest("id")
		self.assertEqual(response.status_code, 302)
		self.assertEqual(
			response.url,
			reverse("booking_mock_digital_payment", kwargs={"booking_id": booking.id}),
		)
		self.assertEqual(booking.status, Booking.Status.PENDING)

	def test_mock_digital_payment_confirms_booking(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_LATER,
		)

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(
			reverse("booking_mock_digital_payment", kwargs={"booking_id": booking.id})
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse("booking_history"))
		booking.refresh_from_db()
		self.assertEqual(booking.payment_option, Booking.PaymentOption.PAY_NOW)
		self.assertEqual(booking.status, Booking.Status.CONFIRMED)

	def test_guest_can_edit_existing_hotel_review(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)
		review = BookingReview.objects.create(
			booking=booking,
			rating=2,
			comment="Old review",
		)

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(
			reverse("guest_hotel_profile", kwargs={"hotel_id": self.hotel_profile.id}),
			{
				f"hotel-review-{self.hotel_profile.id}-rating": 5,
				f"hotel-review-{self.hotel_profile.id}-comment": "Updated review",
			},
		)

		self.assertEqual(response.status_code, 302)
		review.refresh_from_db()
		self.assertEqual(review.rating, 5)
		self.assertEqual(review.comment, "Updated review")
		self.assertEqual(BookingReview.objects.filter(booking__room__hotel=self.hotel_profile).count(), 1)
		notification = BookingNotification.objects.get(
			recipient=self.hotel_profile,
			booking=booking,
			status=BookingNotification.Type.REVIEW_UPDATED,
		)
		self.assertFalse(notification.is_read)

	def test_guest_rating_submission_notifies_hotel_immediately(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)

		self.client.login(username="guest_user", password="pass1234")
		response = self.client.post(
			reverse("guest_hotel_profile", kwargs={"hotel_id": self.hotel_profile.id}),
			{
				f"hotel-review-{self.hotel_profile.id}-rating": 4,
				f"hotel-review-{self.hotel_profile.id}-comment": "Great stay",
			},
		)

		self.assertEqual(response.status_code, 302)
		notification = BookingNotification.objects.get(
			recipient=self.hotel_profile,
			booking=booking,
			status=BookingNotification.Type.REVIEW_ADDED,
		)
		self.assertFalse(notification.is_read)
		self.assertEqual(notification.message, "A guest submitted a new rating and review.")

	def test_hotel_review_notification_link_targets_reviews_page(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)
		notification = BookingNotification.objects.create(
			recipient=self.hotel_profile,
			booking=booking,
			status=BookingNotification.Type.REVIEW_ADDED,
			message="A guest submitted a new rating and review.",
		)

		self.client.login(username="hotel_user", password="pass1234")
		response = self.client.get(reverse("hotel_home"))

		self.assertEqual(response.status_code, 200)
		links = [item.history_url for item in response.context["booking_notifications"]]
		self.assertIn(
			f"{reverse('hotel_reviews')}?notification={notification.id}",
			links,
		)

	def test_hotel_reviews_page_marks_review_notification_as_read(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)
		notification = BookingNotification.objects.create(
			recipient=self.hotel_profile,
			booking=booking,
			status=BookingNotification.Type.REVIEW_UPDATED,
			message="A guest updated their rating and review.",
		)

		self.client.login(username="hotel_user", password="pass1234")
		response = self.client.get(
			f"{reverse('hotel_reviews')}?notification={notification.id}"
		)

		self.assertEqual(response.status_code, 200)
		notification.refresh_from_db()
		self.assertTrue(notification.is_read)

	def test_hotel_reviews_page_lists_guest_reviews(self):
		booking = Booking.objects.create(
			guest=self.guest_profile,
			room=self.room,
			guest_name="Guest User",
			guest_email="guest@example.com",
			guest_phone="1234567890",
			payment_option=Booking.PaymentOption.PAY_NOW,
		)
		BookingReview.objects.create(
			booking=booking,
			rating=4,
			comment="Great stay",
		)

		self.client.login(username="hotel_user", password="pass1234")
		response = self.client.get(reverse("hotel_reviews"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Ratings &amp; Reviews")
		self.assertContains(response, "Great stay")
