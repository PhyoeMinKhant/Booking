from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

from .models import Profile


def ensure_profile_exists(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                "full_name": instance.get_full_name() or instance.username,
                "account_type": Profile.AccountType.GUEST,
            },
        )


def connect_signals():
    user_model = get_user_model()
    post_save.connect(ensure_profile_exists, sender=user_model)
