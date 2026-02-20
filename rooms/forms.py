from django import forms
from django.core.exceptions import ValidationError

from .models import Room


class RoomCreateForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = [
            "room_type",
            "capacity",
            "rate_per_night",
            "available_rooms",
            "checkin_date",
            "checkout_date",
        ]

    def clean(self):
        cleaned_data = super().clean()
        checkin_date = cleaned_data.get("checkin_date")
        checkout_date = cleaned_data.get("checkout_date")

        if checkin_date and checkout_date and checkout_date < checkin_date:
            raise ValidationError("Checkout date must be on or after check-in date.")

        return cleaned_data
