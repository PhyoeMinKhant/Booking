from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Profile

User = get_user_model()


class SignupForm(forms.Form):
    ACCOUNT_TYPE_CHOICES = (
        (Profile.AccountType.GUEST, "Guest"),
        (Profile.AccountType.HOTEL, "Hotel"),
    )

    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES)
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data


class LoginForm(forms.Form):
    ACCOUNT_TYPE_CHOICES = (
        (Profile.AccountType.GUEST, "Guest"),
        (Profile.AccountType.HOTEL, "Hotel"),
    )

    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
