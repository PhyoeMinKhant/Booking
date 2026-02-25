from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Profile

User = get_user_model()

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "account_type",
        "hotel_verification_status",
        "user",
        "created_at",
    )
    list_filter = ("account_type", "hotel_verification_status")
    search_fields = ("full_name", "user__email", "user__username")
    autocomplete_fields = ("user",)


def _get_profile_value(user, attr, default=""):
    profile = getattr(user, "profile", None)
    return getattr(profile, attr, default) if profile else default


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "account_type",
        "is_staff",
    )
    search_fields = ("username", "email", "first_name", "last_name")

    @admin.display(description="Account Type")
    def account_type(self, user):
        return _get_profile_value(user, "account_type")


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)
