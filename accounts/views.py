from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LoginForm, SignupForm
from .models import Profile


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        account_type = form.cleaned_data["account_type"]
        user = authenticate(request, username=email, password=password)

        if user is None:
            form.add_error(None, "Invalid email or password.")
        else:
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": user.get_full_name() or user.username,
                    "account_type": Profile.AccountType.GUEST,
                },
            )
            if profile.account_type != account_type:
                form.add_error(None, "Account type does not match this user.")
            else:
                login(request, user)
                return redirect("home" if account_type == "guest" else "hotel_home")

    return render(request, "accounts/login.html", {"form": form})


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        full_name = form.cleaned_data["full_name"].strip()
        account_type = form.cleaned_data["account_type"]

        user = Profile.create_user_with_profile(
            email=email,
            password=password,
            full_name=full_name,
            account_type=account_type,
        )
        login(request, user)
        return redirect("home" if account_type == "guest" else "hotel_home")

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def home_view(request):
    return render(request, "accounts/guest_home.html")


@login_required
def hotel_home_view(request):
    return render(request, "accounts/hotel_home.html")
