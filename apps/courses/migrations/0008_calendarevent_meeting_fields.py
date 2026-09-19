from django.db import migrations, models


def migrate_live_events_to_meeting(apps, schema_editor):
    CalendarEvent = apps.get_model("courses", "CalendarEvent")
    CalendarEvent.objects.filter(event_type="live").update(event_type="meeting", meeting_type="video")


def revert_meeting_events_to_live(apps, schema_editor):
    CalendarEvent = apps.get_model("courses", "CalendarEvent")
    CalendarEvent.objects.filter(event_type="meeting").update(event_type="live")


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0007_lessonprogress_attention_events_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="calendarevent",
            name="meeting_type",
            field=models.CharField(blank=True, choices=[("call", "Call"), ("video", "Video Call")], max_length=20),
        ),
        migrations.AddField(
            model_name="calendarevent",
            name="meeting_url",
            field=models.URLField(blank=True),
        ),
        migrations.RunPython(migrate_live_events_to_meeting, revert_meeting_events_to_live),
        migrations.AlterField(
            model_name="calendarevent",
            name="event_type",
            field=models.CharField(
                choices=[("quiz", "Quiz"), ("assignment", "Assignment"), ("module", "Module"), ("meeting", "Meeting")],
                default="module",
                max_length=20,
            ),
        ),
    ]
