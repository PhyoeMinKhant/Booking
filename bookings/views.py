import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from rooms.models import Room

from .forms import BookingCheckoutForm, BookingReviewForm
from .models import Booking, BookingReview


BOOKING_STATE_LABELS = {
	"all": "All",
	Booking.Status.PENDING: "Pending",
	Booking.Status.CONFIRMED: "Confirmed",
	Booking.Status.COMPLETED: "Completed",
	Booking.Status.CANCELED: "Canceled",
	"expired": "Expired",
}


def resolve_booking_state(booking: Booking) -> str:
	booking.refresh_status(now=timezone.now(), save=True)
	return booking.status


def expire_overdue_pending_bookings(queryset):
	expiry_cutoff = timezone.now() - datetime.timedelta(hours=Booking.PENDING_PAYMENT_EXPIRY_HOURS)
	overdue_bookings = list(
		queryset.select_related("room").filter(
		status=Booking.Status.PENDING,
		payment_option=Booking.PaymentOption.PAY_LATER,
		created_at__lte=expiry_cutoff,
		)
	)
	for booking in overdue_bookings:
		booking.status = Booking.Status.EXPIRED
		booking.save(update_fields=["status"])
		Room.objects.filter(id=booking.room_id).update(
			available_rooms=F("available_rooms") + booking.rooms_count
		)


@login_required
def checkout_view(request, room_id: int):
	profile, _ = Profile.objects.get_or_create(
		user=request.user,
		defaults={
			"full_name": request.user.get_full_name() or request.user.username,
			"account_type": Profile.AccountType.GUEST,
		},
	)
	if profile.account_type != Profile.AccountType.GUEST:
		return redirect("hotel_home")

	room = get_object_or_404(
		Room.objects.select_related("hotel", "room_type"),
		id=room_id,
	)
	account_email = (request.user.email or "").strip().lower()
	expire_overdue_pending_bookings(Booking.objects.filter(room=room))
	room.refresh_from_db(fields=["available_rooms"])

	initial_data = {
		"guest_name": profile.full_name or request.user.username,
		"guest_email": account_email,
		"guest_phone": profile.phone_number,
		"payment_option": Booking.PaymentOption.PAY_LATER,
	}
	form = BookingCheckoutForm(
		request.POST or None,
		initial=initial_data,
		fixed_email=account_email,
		max_rooms_available=room.available_rooms,
	)

	if request.method == "POST" and form.is_valid():
		guest_name = form.cleaned_data["guest_name"].strip()
		guest_phone = form.cleaned_data["guest_phone"]
		rooms_count = form.cleaned_data["rooms_count"]
		payment_option = form.cleaned_data["payment_option"]

		expire_overdue_pending_bookings(Booking.objects.filter(guest=profile, room=room))
		room.refresh_from_db(fields=["available_rooms"])

		with transaction.atomic():
			locked_room = (
				Room.objects.select_for_update()
				.select_related("hotel", "room_type")
				.filter(id=room_id)
				.first()
			)
			if locked_room is None or locked_room.available_rooms < rooms_count:
				form.add_error(None, "Requested number of rooms is no longer available.")
			else:
				Booking.objects.create(
					guest=profile,
					room=locked_room,
					guest_name=guest_name,
					guest_email=account_email,
					guest_phone=guest_phone,
					rooms_count=rooms_count,
					payment_option=payment_option,
				)
				Room.objects.filter(id=locked_room.id).update(
					available_rooms=F("available_rooms") - rooms_count
				)

				if guest_name:
					profile.full_name = guest_name
				profile.phone_number = guest_phone
				profile.save(update_fields=["full_name", "phone_number"])

				return redirect("home")
	room.refresh_from_db(fields=["available_rooms"])

	return render(
		request,
		"bookings/checkout.html",
		{
			"room": room,
			"form": form,
		},
	)


@login_required
def history_view(request):
	profile, _ = Profile.objects.get_or_create(
		user=request.user,
		defaults={
			"full_name": request.user.get_full_name() or request.user.username,
			"account_type": Profile.AccountType.GUEST,
		},
	)
	if profile.account_type != Profile.AccountType.GUEST:
		return redirect("hotel_home")

	available_states = ["all", "pending", "confirmed", "completed", "canceled", "expired"]
	selected_state = (request.GET.get("state") or "all").strip().lower()
	if selected_state not in available_states:
		selected_state = "all"

	expire_overdue_pending_bookings(Booking.objects.filter(guest=profile))

	bookings = list(
		Booking.objects.select_related("room", "room__hotel", "room__room_type", "review")
		.filter(guest=profile)
		.order_by("-created_at")
	)

	state_counts = {state: 0 for state in available_states}
	filtered_bookings = []

	for booking in bookings:
		computed_state = resolve_booking_state(booking)
		booking.review_obj = None
		try:
			booking.review_obj = booking.review
		except BookingReview.DoesNotExist:
			booking.review_obj = None
		booking.can_review = computed_state == Booking.Status.COMPLETED
		if booking.can_review:
			booking.review_form = BookingReviewForm(
				prefix=f"review-{booking.id}",
				instance=booking.review_obj,
			)
		booking.payment_expires_at = booking.created_at + datetime.timedelta(
			hours=Booking.PENDING_PAYMENT_EXPIRY_HOURS
		)
		state_counts["all"] += 1
		state_counts[computed_state] += 1
		booking.computed_state = computed_state
		booking.computed_state_label = BOOKING_STATE_LABELS[computed_state]
		if selected_state == "all" or selected_state == computed_state:
			filtered_bookings.append(booking)

	state_tabs = [
		{
			"code": state,
			"label": BOOKING_STATE_LABELS[state],
			"count": state_counts[state],
			"is_active": selected_state == state,
		}
		for state in available_states
	]

	return render(
		request,
		"bookings/history.html",
		{
			"profile": profile,
			"bookings": filtered_bookings,
			"state_tabs": state_tabs,
			"selected_state": selected_state,
		},
	)


@login_required
def booking_review_view(request, booking_id: int):
	if request.method != "POST":
		return redirect("booking_history")

	profile, _ = Profile.objects.get_or_create(
		user=request.user,
		defaults={
			"full_name": request.user.get_full_name() or request.user.username,
			"account_type": Profile.AccountType.GUEST,
		},
	)
	if profile.account_type != Profile.AccountType.GUEST:
		return redirect("hotel_home")

	booking = get_object_or_404(
		Booking.objects.select_related("guest", "review"),
		id=booking_id,
		guest=profile,
	)
	booking.refresh_status(now=timezone.now(), save=True)
	if booking.status != Booking.Status.COMPLETED:
		return redirect(f"{reverse('booking_history')}?state=completed#booking-{booking.id}")

	review_instance = None
	try:
		review_instance = booking.review
	except BookingReview.DoesNotExist:
		review_instance = None

	form = BookingReviewForm(
		request.POST,
		prefix=f"review-{booking.id}",
		instance=review_instance,
	)
	if form.is_valid():
		review = form.save(commit=False)
		review.booking = booking
		review.save()

	return redirect(f"{reverse('booking_history')}?state=completed#booking-{booking.id}")


@login_required
def hotel_history_view(request):
	profile, _ = Profile.objects.get_or_create(
		user=request.user,
		defaults={
			"full_name": request.user.get_full_name() or request.user.username,
			"account_type": Profile.AccountType.GUEST,
		},
	)
	if profile.account_type != Profile.AccountType.HOTEL:
		return redirect("home")

	available_states = ["all", "pending", "confirmed", "completed", "canceled", "expired"]
	selected_state = (request.GET.get("state") or "all").strip().lower()
	if selected_state not in available_states:
		selected_state = "all"

	expire_overdue_pending_bookings(Booking.objects.filter(room__hotel=profile))

	bookings = list(
		Booking.objects.select_related(
			"room",
			"room__hotel",
			"room__room_type",
			"guest",
		)
		.filter(room__hotel=profile)
		.order_by("-created_at")
	)

	state_counts = {state: 0 for state in available_states}
	filtered_bookings = []

	for booking in bookings:
		computed_state = resolve_booking_state(booking)
		booking.payment_expires_at = booking.created_at + datetime.timedelta(
			hours=Booking.PENDING_PAYMENT_EXPIRY_HOURS
		)
		state_counts["all"] += 1
		state_counts[computed_state] += 1
		booking.computed_state = computed_state
		booking.computed_state_label = BOOKING_STATE_LABELS[computed_state]
		if selected_state == "all" or selected_state == computed_state:
			filtered_bookings.append(booking)

	state_tabs = [
		{
			"code": state,
			"label": BOOKING_STATE_LABELS[state],
			"count": state_counts[state],
			"is_active": selected_state == state,
		}
		for state in available_states
	]

	return render(
		request,
		"bookings/hotel_history.html",
		{
			"profile": profile,
			"bookings": filtered_bookings,
			"state_tabs": state_tabs,
			"selected_state": selected_state,
		},
	)


@login_required
def cancel_booking_view(request, booking_id: int):
	if request.method != "POST":
		return redirect("booking_history")

	profile, _ = Profile.objects.get_or_create(
		user=request.user,
		defaults={
			"full_name": request.user.get_full_name() or request.user.username,
			"account_type": Profile.AccountType.GUEST,
		},
	)
	if profile.account_type != Profile.AccountType.GUEST:
		return redirect("hotel_home")

	with transaction.atomic():
		booking = (
			Booking.objects.select_for_update()
			.select_related("room")
			.filter(id=booking_id, guest=profile)
			.first()
		)
		if booking is None:
			return redirect("booking_history")

		booking.refresh_status(now=timezone.now(), save=True)
		if booking.status != Booking.Status.PENDING:
			return redirect("booking_history")

		booking.status = Booking.Status.CANCELED
		booking.save(update_fields=["status"])
		Room.objects.filter(id=booking.room_id).update(
			available_rooms=F("available_rooms") + booking.rooms_count
		)

	return redirect("booking_history")


@login_required
def pay_now_booking_view(request, booking_id: int):
	if request.method != "POST":
		return redirect("booking_history")

	profile, _ = Profile.objects.get_or_create(
		user=request.user,
		defaults={
			"full_name": request.user.get_full_name() or request.user.username,
			"account_type": Profile.AccountType.GUEST,
		},
	)
	if profile.account_type != Profile.AccountType.GUEST:
		return redirect("hotel_home")

	with transaction.atomic():
		booking = (
			Booking.objects.select_for_update()
			.filter(id=booking_id, guest=profile)
			.first()
		)
		if booking is None:
			return redirect("booking_history")

		booking.refresh_status(now=timezone.now(), save=True)
		if booking.status != Booking.Status.PENDING:
			return redirect("booking_history")
		if booking.payment_option != Booking.PaymentOption.PAY_LATER:
			return redirect("booking_history")

		booking.payment_option = Booking.PaymentOption.PAY_NOW
		booking.status = Booking.Status.CONFIRMED
		booking.save(update_fields=["payment_option", "status"])

	return redirect("booking_history")


@login_required
def hotel_cancel_booking_view(request, booking_id: int):
	if request.method != "POST":
		return redirect("hotel_booking_history")

	profile, _ = Profile.objects.get_or_create(
		user=request.user,
		defaults={
			"full_name": request.user.get_full_name() or request.user.username,
			"account_type": Profile.AccountType.GUEST,
		},
	)
	if profile.account_type != Profile.AccountType.HOTEL:
		return redirect("home")

	with transaction.atomic():
		booking = (
			Booking.objects.select_for_update()
			.select_related("room")
			.filter(id=booking_id, room__hotel=profile)
			.first()
		)
		if booking is None:
			return redirect("hotel_booking_history")

		booking.refresh_status(now=timezone.now(), save=True)
		if booking.status != Booking.Status.PENDING:
			return redirect("hotel_booking_history")

		booking.status = Booking.Status.CANCELED
		booking.save(update_fields=["status"])
		Room.objects.filter(id=booking.room_id).update(
			available_rooms=F("available_rooms") + booking.rooms_count
		)

	return redirect("hotel_booking_history")
