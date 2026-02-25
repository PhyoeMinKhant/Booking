from django import forms
from django.contrib.auth import get_user_model

from bookings.models import Booking
from rooms.models import Room

from .models import Profile


class AdminRoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = [
            "hotel",
            "room_type",
            "capacity",
            "rate_per_night",
            "available_rooms",
            "checkin_date",
            "checkout_date",
        ]


class AdminBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            "guest",
            "room",
            "guest_name",
            "guest_email",
            "guest_phone",
            "rooms_count",
            "payment_option",
            "status",
        ]


class AdminAccountForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    is_staff = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)
    full_name = forms.CharField(max_length=150)
    account_type = forms.ChoiceField(choices=Profile.AccountType.choices)
    hotel_verification_status = forms.ChoiceField(
        choices=Profile.HotelVerificationStatus.choices,
        required=False,
    )
    phone_number = forms.CharField(max_length=30, required=False)
    location = forms.CharField(max_length=200, required=False)

    def __init__(self, *args, user_instance=None, profile_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_instance = user_instance
        self.profile_instance = profile_instance
        self.is_create = user_instance is None

        if self.is_create:
            self.fields["password"].required = True

        if user_instance and profile_instance and not self.is_bound:
            self.initial.update(
                {
                    "username": user_instance.username,
                    "email": user_instance.email,
                    "is_staff": user_instance.is_staff,
                    "is_active": user_instance.is_active,
                    "full_name": profile_instance.full_name,
                    "account_type": profile_instance.account_type,
                    "hotel_verification_status": profile_instance.hotel_verification_status,
                    "phone_number": profile_instance.phone_number,
                    "location": profile_instance.location,
                }
            )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        user_model = get_user_model()
        query = user_model.objects.filter(username__iexact=username)
        if self.user_instance:
            query = query.exclude(id=self.user_instance.id)
        if query.exists():
            raise forms.ValidationError("Username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_model = get_user_model()
        query = user_model.objects.filter(email__iexact=email)
        if self.user_instance:
            query = query.exclude(id=self.user_instance.id)
        if query.exists():
            raise forms.ValidationError("Email is already in use.")
        return email

    def save(self):
        user_model = get_user_model()

        username = self.cleaned_data["username"]
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password"]
        is_staff = self.cleaned_data["is_staff"]
        is_active = self.cleaned_data["is_active"]
        full_name = self.cleaned_data["full_name"]
        account_type = self.cleaned_data["account_type"]
        hotel_verification_status = self.cleaned_data["hotel_verification_status"]
        phone_number = self.cleaned_data["phone_number"].strip()
        location = self.cleaned_data["location"].strip()

        if account_type == Profile.AccountType.HOTEL:
            effective_hotel_status = (
                hotel_verification_status or Profile.HotelVerificationStatus.PENDING
            )
            effective_is_active = (
                is_active and effective_hotel_status == Profile.HotelVerificationStatus.APPROVED
            )
        else:
            effective_hotel_status = Profile.HotelVerificationStatus.APPROVED
            effective_is_active = is_active

        if self.is_create:
            user = user_model.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name,
                is_staff=is_staff,
                is_active=effective_is_active,
            )
            profile = user.profile
        else:
            user = self.user_instance
            profile = self.profile_instance
            user.username = username
            user.email = email
            user.first_name = full_name
            user.is_staff = is_staff
            user.is_active = effective_is_active
            if password:
                user.set_password(password)
            user.save()

        profile.full_name = full_name
        profile.account_type = account_type
        profile.hotel_verification_status = effective_hotel_status
        profile.phone_number = phone_number
        profile.location = location
        profile.save(
            update_fields=[
                "full_name",
                "account_type",
                "hotel_verification_status",
                "phone_number",
                "location",
            ]
        )

        return user