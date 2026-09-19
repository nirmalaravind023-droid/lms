from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.courses.models import Lesson
from apps.courses.subtitles import generate_lesson_subtitles


class Command(BaseCommand):
    help = "Generate WebVTT subtitles for an uploaded lesson video."

    def add_arguments(self, parser):
        parser.add_argument("lesson_id", help="Lesson UUID to process.")
        parser.add_argument("--provider", default="whisper", choices=["whisper", "google", "vosk"])
        parser.add_argument("--language", default="en")
        parser.add_argument("--whisper-model", default="base")
        parser.add_argument("--vosk-model-path", default=None)

    def handle(self, *args, **options):
        try:
            lesson = Lesson.objects.get(id=options["lesson_id"])
        except Lesson.DoesNotExist as exc:
            raise CommandError("Lesson not found.") from exc

        if not lesson.media_file:
            raise CommandError("This lesson does not have an uploaded video file.")

        try:
            output_path = generate_lesson_subtitles(
                lesson,
                provider=options["provider"],
                language=options["language"],
                whisper_model=options["whisper_model"],
                vosk_model_path=options["vosk_model_path"],
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Subtitle file generated: {output_path}"))
