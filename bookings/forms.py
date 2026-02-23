from django import forms

from .models import Booking, BookingReview


class BookingCheckoutForm(forms.Form):
    PAYMENT_OPTION_CHOICES = Booking.PaymentOption.choices

    guest_name = forms.CharField(max_length=150)
    guest_email = forms.EmailField()
    guest_phone = forms.CharField(max_length=30, required=False)
    rooms_count = forms.IntegerField(min_value=1, initial=1)
    payment_option = forms.ChoiceField(choices=PAYMENT_OPTION_CHOICES)

    def __init__(self, *args, fixed_email: str = "", max_rooms_available: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_rooms_available = max_rooms_available if (max_rooms_available or 0) > 0 else None

        if fixed_email:
            normalized_email = fixed_email.strip().lower()
            self.fields["guest_email"].initial = normalized_email
            self.fields["guest_email"].disabled = True

        if self.max_rooms_available is not None:
            self.fields["rooms_count"].widget.attrs["max"] = self.max_rooms_available

    def clean_guest_phone(self):
        return self.cleaned_data["guest_phone"].strip()

    def clean_rooms_count(self):
        rooms_count = self.cleaned_data["rooms_count"]
        if self.max_rooms_available is not None and rooms_count > self.max_rooms_available:
            raise forms.ValidationError(
                f"You can't book more than {self.max_rooms_available} room(s)."
            )
        return rooms_count

    def clean(self):
        cleaned_data = super().clean()
        payment_option = cleaned_data.get("payment_option")
        guest_phone = cleaned_data.get("guest_phone", "")

        if payment_option == Booking.PaymentOption.PAY_NOW and not guest_phone:
            self.add_error("guest_phone", "Phone number is required to settle payment now.")

        return cleaned_data


class BookingReviewForm(forms.ModelForm):
    class Meta:
        model = BookingReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(),
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Share your experience..."}),
        }

    def clean_comment(self):
        return self.cleaned_data["comment"].strip()
