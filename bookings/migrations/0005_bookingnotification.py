from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_alter_profile_account_type"),
        ("bookings", "0004_booking_rooms_count"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookingNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("completed", "Completed"), ("canceled", "Canceled"), ("expired", "Expired")], max_length=20)),
                ("message", models.CharField(max_length=255)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="bookings.booking")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="booking_notifications", to="accounts.profile")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="bookingnotification",
            constraint=models.UniqueConstraint(fields=("recipient", "booking", "status"), name="unique_booking_status_notification_per_recipient"),
        ),
    ]
