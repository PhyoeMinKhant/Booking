from django.urls import path

from . import admin_panel_views as views

urlpatterns = [
    path("", views.panel_dashboard_view, name="panel_dashboard"),
    path("rooms/", views.panel_rooms_view, name="panel_rooms"),
    path("rooms/new/", views.panel_room_create_view, name="panel_room_create"),
    path("rooms/<int:room_id>/edit/", views.panel_room_edit_view, name="panel_room_edit"),
    path("rooms/<int:room_id>/delete/", views.panel_room_delete_view, name="panel_room_delete"),
    path("bookings/", views.panel_bookings_view, name="panel_bookings"),
    path("bookings/new/", views.panel_booking_create_view, name="panel_booking_create"),
    path("bookings/<int:booking_id>/edit/", views.panel_booking_edit_view, name="panel_booking_edit"),
    path("bookings/<int:booking_id>/delete/", views.panel_booking_delete_view, name="panel_booking_delete"),
    path("accounts/", views.panel_accounts_view, name="panel_accounts"),
    path("accounts/new/", views.panel_account_create_view, name="panel_account_create"),
    path("accounts/<int:user_id>/edit/", views.panel_account_edit_view, name="panel_account_edit"),
    path(
        "accounts/<int:user_id>/approve-hotel/",
        views.panel_account_approve_hotel_view,
        name="panel_account_approve_hotel",
    ),
    path(
        "accounts/<int:user_id>/reject-hotel/",
        views.panel_account_reject_hotel_view,
        name="panel_account_reject_hotel",
    ),
    path("accounts/<int:user_id>/delete/", views.panel_account_delete_view, name="panel_account_delete"),
]
