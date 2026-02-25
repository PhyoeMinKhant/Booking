from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

from .models import Profile

User = get_user_model()


class SignupForm(forms.Form):
    ACCOUNT_TYPE_CHOICES = [
        (Profile.AccountType.GUEST, "Guest"),
        (Profile.AccountType.HOTEL, "Hotel"),
    ]

    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES)
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    hotel_license_image = forms.ImageField(required=False)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("An account with this username already exists.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        account_type = cleaned_data.get("account_type")
        hotel_license_image = cleaned_data.get("hotel_license_image")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        if account_type == Profile.AccountType.HOTEL and not hotel_license_image:
            self.add_error(
                "hotel_license_image",
                "Hotel license image is required for hotel account registration.",
            )
        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["profile_image"]


class ProfileUpdateForm(forms.Form):
    username = forms.CharField(max_length=150)
    phone_number = forms.CharField(max_length=30, required=False)
    location = forms.CharField(max_length=200, required=False)
    description = forms.CharField(max_length=2000, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username:
            raise ValidationError("Username is required.")

        if User.objects.filter(username__iexact=username).exclude(pk=self.user.pk).exists():
            raise ValidationError("An account with this username already exists.")
        return username
