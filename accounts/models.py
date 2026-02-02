from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models


class Profile(models.Model):
    class AccountType(models.TextChoices):
        GUEST = "guest", "Guest"
        HOTEL = "hotel", "Hotel"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    full_name = models.CharField(max_length=150)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.GUEST
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.account_type})"

    @staticmethod
    def create_user_with_profile(
        *, email: str, password: str, full_name: str, account_type: str
    ):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name,
        )
        Profile.objects.create(
            user=user,
            full_name=full_name,
            account_type=account_type,
        )
        return user
