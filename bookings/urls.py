from django.urls import path

from . import views

urlpatterns = [
    path("checkout/<int:room_id>/", views.checkout_view, name="booking_checkout"),
    path(
        "mock-digital-payment/<int:booking_id>/",
        views.mock_digital_payment_view,
        name="booking_mock_digital_payment",
    ),
    path("history/", views.history_view, name="booking_history"),
    path("history/<int:booking_id>/review/", views.booking_review_view, name="booking_review"),
    path("history/<int:booking_id>/cancel/", views.cancel_booking_view, name="booking_cancel"),
    path("history/<int:booking_id>/pay-now/", views.pay_now_booking_view, name="booking_pay_now"),
    path("hotel-history/", views.hotel_history_view, name="hotel_booking_history"),
    path(
        "hotel-history/<int:booking_id>/cancel/",
        views.hotel_cancel_booking_view,
        name="hotel_booking_cancel",
    ),
]
