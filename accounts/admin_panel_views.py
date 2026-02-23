from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from bookings.models import Booking
from rooms.models import Room

from .admin_panel_forms import AdminAccountForm, AdminBookingForm, AdminRoomForm
from .models import Profile


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped


@admin_required
def panel_dashboard_view(request):
    context = {
        "bookings_count": Booking.objects.count(),
        "rooms_count": Room.objects.count(),
        "accounts_count": get_user_model().objects.count(),
    }
    return render(request, "accounts/admin_panel/dashboard.html", context)


@admin_required
def panel_rooms_view(request):
    rooms = Room.objects.select_related("hotel", "room_type").order_by("-created_at")
    return render(request, "accounts/admin_panel/rooms_list.html", {"rooms": rooms})


@admin_required
def panel_room_create_view(request):
    form = AdminRoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel_rooms")
    return render(request, "accounts/admin_panel/room_form.html", {"form": form, "mode": "create"})


@admin_required
def panel_room_edit_view(request, room_id: int):
    room = get_object_or_404(Room, id=room_id)
    form = AdminRoomForm(request.POST or None, instance=room)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel_rooms")
    return render(request, "accounts/admin_panel/room_form.html", {"form": form, "mode": "edit", "room": room})


@admin_required
def panel_room_delete_view(request, room_id: int):
    if request.method != "POST":
        return redirect("panel_rooms")
    room = get_object_or_404(Room, id=room_id)
    room.delete()
    return redirect("panel_rooms")


@admin_required
def panel_bookings_view(request):
    bookings = Booking.objects.select_related("guest", "room", "room__hotel", "room__room_type").order_by("-created_at")
    return render(request, "accounts/admin_panel/bookings_list.html", {"bookings": bookings})


@admin_required
def panel_booking_create_view(request):
    form = AdminBookingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel_bookings")
    return render(request, "accounts/admin_panel/booking_form.html", {"form": form, "mode": "create"})


@admin_required
def panel_booking_edit_view(request, booking_id: int):
    booking = get_object_or_404(Booking, id=booking_id)
    form = AdminBookingForm(request.POST or None, instance=booking)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel_bookings")
    return render(
        request,
        "accounts/admin_panel/booking_form.html",
        {"form": form, "mode": "edit", "booking": booking},
    )


@admin_required
def panel_booking_delete_view(request, booking_id: int):
    if request.method != "POST":
        return redirect("panel_bookings")
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    return redirect("panel_bookings")


@admin_required
def panel_accounts_view(request):
    users = get_user_model().objects.select_related("profile").order_by("-date_joined")
    return render(request, "accounts/admin_panel/accounts_list.html", {"users": users})


@admin_required
def panel_account_create_view(request):
    form = AdminAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel_accounts")
    return render(request, "accounts/admin_panel/account_form.html", {"form": form, "mode": "create"})


@admin_required
def panel_account_edit_view(request, user_id: int):
    user_model = get_user_model()
    user = get_object_or_404(user_model.objects.select_related("profile"), id=user_id)
    form = AdminAccountForm(
        request.POST or None,
        user_instance=user,
        profile_instance=user.profile,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("panel_accounts")
    return render(
        request,
        "accounts/admin_panel/account_form.html",
        {"form": form, "mode": "edit", "target_user": user},
    )


@admin_required
def panel_account_delete_view(request, user_id: int):
    if request.method != "POST":
        return redirect("panel_accounts")

    user_model = get_user_model()
    target_user = get_object_or_404(user_model, id=user_id)
    if target_user.id == request.user.id:
        return redirect("panel_accounts")

    target_user.delete()
    return redirect("panel_accounts")