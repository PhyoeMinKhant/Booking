from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0003_alter_booking_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="rooms_count",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
