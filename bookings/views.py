import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile
from rooms.models import Room

from .forms import BookingCheckoutForm
from .models import Booking


BOOKING_STATE_LABELS = {
	"all": "All",
	Booking.Status.PENDING: "Pending",
	Booking.Status.CONFIRMED: "Confirmed",
	Booking.Status.COMPLETED: "Completed",
	Booking.Status.CANCELED: "Canceled",
	"expired": "Expired",
}


def resolve_booking_state(booking: Booking, *, today: datetime.date) -> str:
	if booking.status in (Booking.Status.CANCELED, Booking.Status.COMPLETED):
		return booking.status
	if booking.room.checkout_date < today:
		return "expired"
	return booking.status


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
		available_rooms__gt=0,
	)
	account_email = (request.user.email or "").strip().lower()

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
	)

	if request.method == "POST" and form.is_valid():
		guest_name = form.cleaned_data["guest_name"].strip()
		guest_phone = form.cleaned_data["guest_phone"]
		payment_option = form.cleaned_data["payment_option"]

		Booking.objects.create(
			guest=profile,
			room=room,
			guest_name=guest_name,
			guest_email=account_email,
			guest_phone=guest_phone,
			payment_option=payment_option,
		)

		if guest_name:
			profile.full_name = guest_name
		profile.phone_number = guest_phone
		profile.save(update_fields=["full_name", "phone_number"])

		return redirect("home")

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

	today = datetime.date.today()
	bookings = list(
		Booking.objects.select_related("room", "room__hotel", "room__room_type")
		.filter(guest=profile)
		.order_by("-created_at")
	)

	state_counts = {state: 0 for state in available_states}
	filtered_bookings = []

	for booking in bookings:
		computed_state = resolve_booking_state(booking, today=today)
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

	today = datetime.date.today()
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
		computed_state = resolve_booking_state(booking, today=today)
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
