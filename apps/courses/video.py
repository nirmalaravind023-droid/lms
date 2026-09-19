from __future__ import annotations

from pathlib import Path
from django.core.files import File

try:
    from ffmpeg_streaming import Bitrate, Formats, Representation, Size, input as ffmpeg_input
except ImportError:  # pragma: no cover - dependency is optional at code generation time
    ffmpeg_input = None
    Formats = Bitrate = Representation = Size = None

try:
    import webvtt
except ImportError:  # pragma: no cover
    webvtt = None

from .models import Lesson
from .services import ensure_media_dir, media_manifest_path


def package_lesson_to_hls(lesson: Lesson) -> str:
    """
    Convert uploaded video into an HLS package.
    This is intentionally a thin integration point around
    python-ffmpeg-video-streaming.
    """

    if ffmpeg_input is None:
        raise RuntimeError("python-ffmpeg-video-streaming is not installed.")
    if not lesson.media_file:
        raise ValueError("Lesson has no media file to package.")

    source_path = Path(lesson.media_file.path)
    manifest_path = ensure_media_dir(media_manifest_path(lesson))
    video = ffmpeg_input(str(source_path))
    hls = video.hls(Formats.h264())
    hls.representations(
        Representation(Size(640, 360), Bitrate(512 * 1024, 128 * 1024)),
        Representation(Size(1280, 720), Bitrate(2_500 * 1024, 192 * 1024)),
    )
    hls.output(str(manifest_path))
    return str(manifest_path)


def normalize_subtitle_file(lesson: Lesson) -> str | None:
    if not lesson.subtitle_file:
        return None

    subtitle_path = Path(lesson.subtitle_file.path)
    if subtitle_path.suffix.lower() == ".vtt":
        return str(subtitle_path)

    vtt_path = subtitle_path.with_suffix(".vtt")
    if subtitle_path.suffix.lower() == ".srt":
        raw_text = subtitle_path.read_text(encoding="utf-8", errors="ignore")
        lines = raw_text.splitlines()
        converted_lines = ["WEBVTT", ""]
        for line in lines:
            if "-->" in line:
                converted_lines.append(line.replace(",", "."))
            else:
                converted_lines.append(line)
        vtt_path.write_text("\n".join(converted_lines), encoding="utf-8")
    elif webvtt is not None:
        captions = webvtt.read(str(subtitle_path))
        captions.save(str(vtt_path))
    else:
        return None

    with vtt_path.open("rb") as generated_file:
        lesson.subtitle_file.save(vtt_path.name, File(generated_file), save=False)
    return str(vtt_path)
