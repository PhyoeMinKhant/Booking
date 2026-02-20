from django import forms

from .models import Booking


class BookingCheckoutForm(forms.Form):
    PAYMENT_OPTION_CHOICES = Booking.PaymentOption.choices

    guest_name = forms.CharField(max_length=150)
    guest_email = forms.EmailField()
    guest_phone = forms.CharField(max_length=30, required=False)
    payment_option = forms.ChoiceField(choices=PAYMENT_OPTION_CHOICES)

    def __init__(self, *args, fixed_email: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        if fixed_email:
            normalized_email = fixed_email.strip().lower()
            self.fields["guest_email"].initial = normalized_email
            self.fields["guest_email"].disabled = True

    def clean_guest_phone(self):
        return self.cleaned_data["guest_phone"].strip()

    def clean(self):
        cleaned_data = super().clean()
        payment_option = cleaned_data.get("payment_option")
        guest_phone = cleaned_data.get("guest_phone", "")

        if payment_option == Booking.PaymentOption.PAY_NOW and not guest_phone:
            self.add_error("guest_phone", "Phone number is required to settle payment now.")

        return cleaned_data
