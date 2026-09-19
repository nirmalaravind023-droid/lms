from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_userlifecyclerequest"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userlifecyclerequest",
            name="action",
            field=models.CharField(
                choices=[
                    ("registration_approval", "Approve Employee Registration"),
                    ("deactivate", "Deactivate User"),
                    ("reactivate", "Reactivate User"),
                    ("transfer", "Transfer Department"),
                    ("soft_delete", "Soft Delete / Reset"),
                ],
                max_length=30,
            ),
        ),
    ]
