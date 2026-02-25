from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models


class Profile(models.Model):
    class AccountType(models.TextChoices):
        GUEST = "guest", "Guest"
        HOTEL = "hotel", "Hotel"
        ADMIN = "admin", "Admin"

    class HotelVerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    full_name = models.CharField(max_length=150)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.GUEST
    )
    hotel_verification_status = models.CharField(
        max_length=20,
        choices=HotelVerificationStatus.choices,
        default=HotelVerificationStatus.APPROVED,
    )
    phone_number = models.CharField(max_length=30, blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    profile_image_url = models.URLField(blank=True, default="")
    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )
    hotel_license_image = models.ImageField(
        upload_to="hotel_licenses/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.account_type})"

    @property
    def is_hotel_approved(self) -> bool:
        if self.account_type != self.AccountType.HOTEL:
            return True
        return self.hotel_verification_status == self.HotelVerificationStatus.APPROVED

    @classmethod
    def create_user_with_profile(
        cls,
        *,
        email: str,
        username: str,
        password: str,
        account_type: str,
        hotel_license_image=None,
    ):
        is_hotel_account = account_type == cls.AccountType.HOTEL
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=username,
            is_active=not is_hotel_account,
        )
        cls.objects.update_or_create(
            user=user,
            defaults={
                "full_name": username,
                "account_type": account_type,
                "hotel_verification_status": (
                    cls.HotelVerificationStatus.PENDING
                    if is_hotel_account
                    else cls.HotelVerificationStatus.APPROVED
                ),
                "hotel_license_image": hotel_license_image if is_hotel_account else None,
            },
        )
        return user


class ProfileFacilityImage(models.Model):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="facility_images",
    )
    image = models.ImageField(upload_to="facilities/")
    sort_order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Facility image for {self.profile.full_name}"

    class Meta:
        ordering = ("sort_order", "-uploaded_at")
