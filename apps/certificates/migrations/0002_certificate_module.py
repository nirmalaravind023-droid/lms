from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0005_lessonprogress_last_position_seconds_and_more"),
        ("certificates", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="certificate",
            name="module",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="certificates",
                to="courses.module",
            ),
        ),
    ]
