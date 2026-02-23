from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_alter_profile_account_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
