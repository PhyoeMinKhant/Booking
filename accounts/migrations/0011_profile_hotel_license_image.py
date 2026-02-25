from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_profile_hotel_verification_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="hotel_license_image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="hotel_licenses/",
            ),
        ),
    ]
