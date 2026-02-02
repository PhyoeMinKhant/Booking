from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("home/", views.home_view, name="home"),
    path("hotel-home/", views.hotel_home_view, name="hotel_home"),
]
