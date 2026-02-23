import datetime

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Max, Q
from django.shortcuts import redirect, render
from django.urls import reverse

from bookings.forms import BookingReviewForm
from bookings.models import Booking, BookingReview

from .forms import LoginForm, ProfileImageForm, ProfileUpdateForm, SignupForm
from .models import Profile, ProfileFacilityImage
from rooms.forms import RoomCreateForm
from rooms.models import Room


def get_or_create_profile(user):
    return Profile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": user.get_full_name() or user.username,
            "account_type": Profile.AccountType.GUEST,
        },
    )


def get_home_redirect(account_type):
    if account_type == Profile.AccountType.GUEST:
        return "home"
    if account_type == Profile.AccountType.HOTEL:
        return "hotel_home"
    if account_type == Profile.AccountType.ADMIN:
        return "panel_dashboard"
    return "home"


def get_login_redirect(user, account_type):
    if user.is_staff or user.is_superuser:
        return "panel_dashboard"
    return get_home_redirect(account_type)


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        user_model = get_user_model()
        matched_user = user_model.objects.filter(email__iexact=email).first()
        user = None
        if matched_user:
            user = authenticate(request, username=matched_user.username, password=password)

        if user is None:
            form.add_error(None, "Invalid email or password.")
        else:
            profile, _ = get_or_create_profile(user)
            login(request, user)
            return redirect(get_login_redirect(user, profile.account_type))

    return render(request, "accounts/login.html", {"form": form})


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        account_type = form.cleaned_data["account_type"]

        user = Profile.create_user_with_profile(
            email=email,
            username=username,
            password=password,
            account_type=account_type,
        )
        login(request, user)
        return redirect(get_home_redirect(account_type))

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def home_view(request):
    profile, _ = get_or_create_profile(request.user)
    search_params = {
        "location": request.GET.get("location", "").strip(),
        "hotel_name": request.GET.get("hotel_name", "").strip(),
        "checkin": request.GET.get("checkin", "").strip(),
        "checkout": request.GET.get("checkout", "").strip(),
        "guests": request.GET.get("guests", "").strip(),
    }

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    search_performed = any(search_params.values())
    rooms = []
    search_error = None

    if search_performed:
        checkin_date = parse_date(search_params["checkin"])
        checkout_date = parse_date(search_params["checkout"])
        guests_value = None
        if search_params["guests"]:
            try:
                guests_value = max(1, int(search_params["guests"]))
            except ValueError:
                guests_value = None

        if checkin_date and checkout_date and checkout_date < checkin_date:
            search_error = "Checkout date must be on or after check-in date."
        else:
            query = (
                Room.objects.select_related("room_type", "hotel")
                .prefetch_related("hotel__facility_images")
                .filter(available_rooms__gt=0)
                .filter(hotel__account_type=Profile.AccountType.HOTEL)
            )
            if search_params["location"]:
                query = query.filter(
                    Q(hotel__location__icontains=search_params["location"])
                    | Q(hotel__full_name__icontains=search_params["location"])
                )
            if search_params["hotel_name"]:
                query = query.filter(hotel__full_name__icontains=search_params["hotel_name"])
            if guests_value:
                query = query.filter(capacity__gte=guests_value)
            if checkin_date:
                query = query.filter(checkin_date__lte=checkin_date)
            if checkout_date:
                query = query.filter(checkout_date__gte=checkout_date)

            rooms = list(query.order_by("rate_per_night", "hotel__full_name"))

            if rooms:
                hotel_ids = {room.hotel_id for room in rooms}
                review_stats_qs = (
                    BookingReview.objects.filter(
                        booking__room__hotel_id__in=hotel_ids,
                        booking__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
                    )
                    .values("booking__room__hotel_id")
                    .annotate(avg_rating=Avg("rating"), review_count=Count("id"))
                )
                rating_stats_by_hotel = {
                    row["booking__room__hotel_id"]: row
                    for row in review_stats_qs
                }

                reviews_qs = (
                    BookingReview.objects.select_related("booking", "booking__guest")
                    .filter(
                        booking__room__hotel_id__in=hotel_ids,
                        booking__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
                    )
                    .order_by("-created_at")
                )
                recent_reviews_by_hotel: dict[int, list[BookingReview]] = {
                    hotel_id: [] for hotel_id in hotel_ids
                }
                for review in reviews_qs:
                    hotel_id = review.booking.room.hotel_id
                    if len(recent_reviews_by_hotel[hotel_id]) < 2:
                        recent_reviews_by_hotel[hotel_id].append(review)

                for room in rooms:
                    stats = rating_stats_by_hotel.get(room.hotel_id)
                    room.hotel_avg_rating = (
                        round(float(stats["avg_rating"]), 1)
                        if stats and stats["avg_rating"] is not None
                        else None
                    )
                    room.hotel_review_count = (
                        int(stats["review_count"])
                        if stats and stats["review_count"] is not None
                        else 0
                    )
                    room.hotel_recent_reviews = recent_reviews_by_hotel.get(room.hotel_id, [])

    return render(
        request,
        "accounts/guest_home.html",
        {
            "profile": profile,
            "rooms": rooms,
            "search_params": search_params,
            "search_performed": search_performed,
            "search_error": search_error,
        },
    )


@login_required
def guest_hotel_profile_view(request, hotel_id: int):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.GUEST:
        return redirect("hotel_home")

    hotel = Profile.objects.filter(
        id=hotel_id,
        account_type=Profile.AccountType.HOTEL,
    ).first()
    if hotel is None:
        return redirect("home")

    listed_rooms = (
        Room.objects.filter(hotel=hotel, available_rooms__gt=0)
        .select_related("room_type")
        .order_by("rate_per_night", "room_type__name")
    )

    eligible_booking = (
        Booking.objects.filter(
            guest=profile,
            room__hotel=hotel,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
        )
        .select_related("room")
        .order_by("-created_at")
        .first()
    )

    existing_review = (
        BookingReview.objects.filter(
            booking__guest=profile,
            booking__room__hotel=hotel,
        )
        .select_related("booking")
        .first()
    )

    can_submit_review = eligible_booking is not None and existing_review is None
    review_form = BookingReviewForm(request.POST or None, prefix=f"hotel-review-{hotel.id}")
    review_error = ""

    if request.method == "POST":
        if not can_submit_review:
            if existing_review is not None:
                review_error = "You have already reviewed this hotel from your account."
            else:
                review_error = "You can review only after you have a confirmed or completed booking."
        elif review_form.is_valid():
            review = review_form.save(commit=False)
            review.booking = eligible_booking
            review.save()
            return redirect("guest_hotel_profile", hotel_id=hotel.id)

    reviews = (
        BookingReview.objects.select_related("booking", "booking__guest")
        .filter(
            booking__room__hotel=hotel,
            booking__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
        )
        .order_by("-created_at")
    )
    review_stats = reviews.aggregate(avg_rating=Avg("rating"), review_count=Count("id"))
    avg_rating = review_stats["avg_rating"]

    return render(
        request,
        "accounts/hotel_public_profile.html",
        {
            "profile": profile,
            "hotel": hotel,
            "facility_images": hotel.facility_images.all(),
            "listed_rooms": listed_rooms,
            "reviews": reviews,
            "avg_rating": round(float(avg_rating), 1) if avg_rating is not None else None,
            "review_count": int(review_stats["review_count"] or 0),
            "review_form": review_form,
            "can_submit_review": can_submit_review,
            "existing_review": existing_review,
            "review_error": review_error,
        },
    )


@login_required
def hotel_home_view(request):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.HOTEL:
        return redirect("home")

    if request.method == "POST":
        room_id = request.POST.get("room_id")
        room_instance = None
        if room_id:
            room_instance = Room.objects.filter(id=room_id, hotel=profile).first()
            if room_instance is None:
                return redirect("hotel_home")

        form = RoomCreateForm(request.POST, instance=room_instance)
        if form.is_valid():
            available_rooms = form.cleaned_data["available_rooms"]
            if available_rooms == 0:
                if room_instance:
                    room_instance.delete()
            else:
                room = form.save(commit=False)
                room.hotel = profile
                room.save()
            return redirect("hotel_home")
    else:
        form = RoomCreateForm()

    rooms = Room.objects.filter(hotel=profile).select_related("room_type").order_by("-created_at")
    return render(
        request,
        "accounts/hotel_home.html",
        {
            "profile": profile,
            "room_form": form,
            "rooms": rooms,
        },
    )


@login_required
def hotel_profile_view(request):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.HOTEL:
        return redirect("home")

    review_stats = BookingReview.objects.filter(
        booking__room__hotel=profile,
        booking__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
    ).aggregate(avg_rating=Avg("rating"), review_count=Count("id"))

    avg_rating = review_stats["avg_rating"]
    review_count = int(review_stats["review_count"] or 0)

    facility_images = profile.facility_images.all()
    facility_limit = 6
    facility_remaining = max(facility_limit - facility_images.count(), 0)
    return render(
        request,
        "accounts/hotel_profile.html",
        {
            "profile": profile,
            "facility_images": facility_images,
            "facility_limit": facility_limit,
            "facility_remaining": facility_remaining,
            "avg_rating": round(float(avg_rating), 1) if avg_rating is not None else None,
            "review_count": review_count,
        },
    )


@login_required
def facility_image_upload_view(request):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.HOTEL:
        return redirect("home")

    if request.method != "POST":
        return redirect("hotel_profile")

    facility_limit = 6
    existing_count = profile.facility_images.count()
    remaining = facility_limit - existing_count
    if remaining <= 0:
        return redirect("hotel_profile")

    images = request.FILES.getlist("facility_images")
    next_order = (
        profile.facility_images.aggregate(max_order=Max("sort_order")).get("max_order")
        or 0
    )
    for index, image in enumerate(images[:remaining], start=1):
        ProfileFacilityImage.objects.create(
            profile=profile,
            image=image,
            sort_order=next_order + index,
        )

    return redirect("hotel_profile")


@login_required
def facility_image_delete_view(request, image_id: int):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.HOTEL:
        return redirect("home")

    if request.method != "POST":
        return redirect("hotel_profile")

    image = ProfileFacilityImage.objects.filter(id=image_id, profile=profile).first()
    if image:
        image.delete()

    return redirect("hotel_profile")


@login_required
def facility_image_replace_view(request, image_id: int):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.HOTEL:
        return redirect("home")

    if request.method != "POST":
        return redirect("hotel_profile")

    image = ProfileFacilityImage.objects.filter(id=image_id, profile=profile).first()
    if image and request.FILES.get("facility_image"):
        image.image = request.FILES["facility_image"]
        image.save(update_fields=["image"])

    return redirect("hotel_profile")


@login_required
def facility_image_move_view(request, image_id: int, direction: str):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.HOTEL:
        return redirect("home")

    if request.method != "POST":
        return redirect("hotel_profile")

    images = list(profile.facility_images.all())
    current_index = next((i for i, img in enumerate(images) if img.id == image_id), None)
    if current_index is None:
        return redirect("hotel_profile")

    if direction == "prev" and current_index > 0:
        swap_index = current_index - 1
    elif direction == "next" and current_index < len(images) - 1:
        swap_index = current_index + 1
    else:
        return redirect("hotel_profile")

    current = images[current_index]
    swap = images[swap_index]
    current.sort_order, swap.sort_order = swap.sort_order, current.sort_order
    current.save(update_fields=["sort_order"])
    swap.save(update_fields=["sort_order"])

    return redirect("hotel_profile")


@login_required
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


@login_required
def guest_profile_view(request):
    profile, _ = get_or_create_profile(request.user)
    if profile.account_type != Profile.AccountType.GUEST:
        return redirect("hotel_home")
    return render(request, "accounts/guest_profile.html", {"profile": profile})


@login_required
def profile_image_update_view(request):
    profile, _ = get_or_create_profile(request.user)
    if request.method != "POST":
        return redirect(get_home_redirect(profile.account_type))

    form = ProfileImageForm(request.POST, request.FILES, instance=profile)
    if form.is_valid():
        form.save()

    if profile.account_type == Profile.AccountType.GUEST:
        return redirect(f"{reverse('home')}?profile=open")
    return redirect("hotel_home")


@login_required
def profile_update_view(request):
    profile, _ = get_or_create_profile(request.user)
    if request.method != "POST":
        return redirect(get_home_redirect(profile.account_type))

    form = ProfileUpdateForm(request.POST, user=request.user)
    if form.is_valid():
        username = form.cleaned_data["username"]
        phone_number = form.cleaned_data["phone_number"].strip()
        location = form.cleaned_data["location"].strip()
        description = form.cleaned_data["description"].strip()

        request.user.username = username
        request.user.first_name = username
        request.user.save(update_fields=["username", "first_name"])

        profile.full_name = username
        profile.phone_number = phone_number
        profile.location = location
        update_fields = ["full_name", "phone_number", "location"]
        if profile.account_type == Profile.AccountType.HOTEL:
            profile.description = description
            update_fields.append("description")
        profile.save(update_fields=update_fields)

    if profile.account_type == Profile.AccountType.GUEST:
        return redirect(f"{reverse('home')}?profile=open")
    return redirect("hotel_home")
