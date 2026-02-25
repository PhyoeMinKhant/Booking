from django.urls import reverse

from accounts.models import Profile

from .models import BookingNotification


def booking_notifications(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "booking_notifications": [],
            "booking_notifications_unread_count": 0,
        }

    profile = getattr(user, "profile", None)
    if profile is None:
        return {
            "booking_notifications": [],
            "booking_notifications_unread_count": 0,
        }

    notifications_qs = BookingNotification.objects.filter(
        recipient=profile,
        is_read=False,
    ).select_related("booking")
    history_url_name = (
        "hotel_booking_history"
        if profile.account_type == Profile.AccountType.HOTEL
        else "booking_history"
    )
    notifications = list(notifications_qs[:8])
    for notification in notifications:
        if (
            profile.account_type == Profile.AccountType.HOTEL
            and notification.status
            in {
                BookingNotification.Type.REVIEW_ADDED,
                BookingNotification.Type.REVIEW_UPDATED,
            }
        ):
            notification.history_url = (
                f"{reverse('hotel_reviews')}?notification={notification.id}"
            )
        else:
            notification.history_url = (
                f"{reverse(history_url_name)}?state=all&notification={notification.id}#booking-{notification.booking_id}"
            )

    return {
        "booking_notifications": notifications,
        "booking_notifications_unread_count": notifications_qs.count(),
    }
