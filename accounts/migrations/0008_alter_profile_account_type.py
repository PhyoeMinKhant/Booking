from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_alter_profilefacilityimage_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="account_type",
            field=models.CharField(
                choices=[
                    ("guest", "Guest"),
                    ("hotel", "Hotel"),
                    ("admin", "Admin"),
                ],
                default="guest",
                max_length=20,
            ),
        ),
    ]
