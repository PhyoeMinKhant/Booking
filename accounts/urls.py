from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("signup/hotel-pending/", views.hotel_signup_pending_view, name="hotel_signup_pending"),
    path("home/", views.home_view, name="home"),
    path("hotels/<int:hotel_id>/", views.guest_hotel_profile_view, name="guest_hotel_profile"),
    path("profile/", views.guest_profile_view, name="guest_profile"),
    path("profile/image/", views.profile_image_update_view, name="profile_image_update"),
    path("profile/update/", views.profile_update_view, name="profile_update"),
    path("hotel-home/", views.hotel_home_view, name="hotel_home"),
    path("hotel-profile/", views.hotel_profile_view, name="hotel_profile"),
    path("hotel-reviews/", views.hotel_reviews_view, name="hotel_reviews"),
    path(
        "hotel-profile/facilities/",
        views.facility_image_upload_view,
        name="facility_image_upload",
    ),
    path(
        "hotel-profile/facilities/<int:image_id>/delete/",
        views.facility_image_delete_view,
        name="facility_image_delete",
    ),
    path(
        "hotel-profile/facilities/<int:image_id>/replace/",
        views.facility_image_replace_view,
        name="facility_image_replace",
    ),
    path(
        "hotel-profile/facilities/<int:image_id>/move/<str:direction>/",
        views.facility_image_move_view,
        name="facility_image_move",
    ),
    path("logout/", views.logout_view, name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("account_password_reset_done"),
        ),
        name="account_password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="account_password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("account_password_reset_complete"),
        ),
        name="account_password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="account_password_reset_complete",
    ),
]
