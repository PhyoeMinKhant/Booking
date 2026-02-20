from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0007_alter_profilefacilityimage_options"),
        ("rooms", "0002_seed_room_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="Booking",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("guest_name", models.CharField(max_length=150)),
                ("guest_email", models.EmailField(max_length=254)),
                ("guest_phone", models.CharField(blank=True, default="", max_length=30)),
                (
                    "payment_option",
                    models.CharField(
                        choices=[("pay_now", "Pay now"), ("pay_later", "Pay later")],
                        default="pay_later",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "guest",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="accounts.profile",
                    ),
                ),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bookings",
                        to="rooms.room",
                    ),
                ),
            ],
        ),
    ]
