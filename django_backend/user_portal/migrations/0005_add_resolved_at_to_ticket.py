from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user_portal", "0004_add_suggested_tools_and_safety_equipment"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="resolved_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                db_index=True,
                help_text="When ticket was marked resolved",
            ),
        ),
    ]
