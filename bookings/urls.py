from django.urls import path

from . import views

urlpatterns = [
    path("checkout/<int:room_id>/", views.checkout_view, name="booking_checkout"),
    path("history/", views.history_view, name="booking_history"),
    path("hotel-history/", views.hotel_history_view, name="hotel_booking_history"),
]
