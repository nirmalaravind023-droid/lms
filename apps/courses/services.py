from __future__ import annotations
"""Course utility functions.

This file is used by views when they need helper logic that should stay out of templates:
- reorder module/lesson items
- parse AJAX/JSON payloads
- calculate anti-skip video progress
"""

import json
from pathlib import Path

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from .models import Lesson, LessonProgress, Module, merge_time_ranges


def reorder_modules(payload: list[dict], *, queryset=None) -> None:
    # Called by the drag-and-drop builder API endpoint.
    queryset = queryset or Module.objects.all()
    with transaction.atomic():
        for item in payload:
            updated = queryset.filter(pk=item["id"]).update(order=item["order"])
            if not updated:
                raise ValueError("Module is not available for reorder.")


def reorder_lessons(payload: list[dict], *, queryset=None) -> None:
    queryset = queryset or Lesson.objects.all()
    with transaction.atomic():
        for item in payload:
            updated = queryset.filter(pk=item["id"]).update(order=item["order"])
            if not updated:
                raise ValueError("Lesson is not available for reorder.")


def parse_json_request(body: bytes) -> list[dict]:
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected a list payload.")
    return data


def media_manifest_path(lesson: Lesson) -> str:
    return f"videos/hls/{lesson.id}/master.m3u8"


def lesson_media_exists(lesson: Lesson) -> bool:
    return default_storage.exists(media_manifest_path(lesson))


def ensure_media_dir(relative_path: str) -> Path:
    full_path = Path(default_storage.path(relative_path))
    full_path.parent.mkdir(parents=True, exist_ok=True)
    return full_path


def record_video_playback(
    progress: LessonProgress,
    *,
    event: str,
    position: float,
    duration: float,
) -> dict:
    # This is the backend rule engine for the locked video player.
    # Frontend sends play/pause/time/seek events, and this function decides
    # whether the learner has truly earned completion.
    position = max(0.0, float(position or 0))
    duration = max(0.0, float(duration or 0))
    previous_position = max(0.0, float(progress.last_position_seconds or 0))
    max_position = max(0.0, float(progress.max_position_seconds or 0))
    now = timezone.now()

    progress.started_at = progress.started_at or now
    if progress.status == LessonProgress.Status.NOT_STARTED:
        progress.status = LessonProgress.Status.IN_PROGRESS

    if duration:
        progress.video_duration_seconds = max(progress.video_duration_seconds or 0, duration)

    allowed_forward_position = max_position + 3
    payload = {
        "ok": True,
        "video_completed": progress.video_completed,
        "can_advance": progress.can_advance,
        "coverage_ratio": round(progress.coverage_ratio(progress.video_duration_seconds), 4),
        "allowed_position": round(max_position, 2),
        "rewind_only": False,
        "message": "",
    }

    if event == "seeked" and position > allowed_forward_position:
        progress.skip_detected = True
        progress.save(update_fields=["skip_detected", "updated_at"])
        payload.update(
            {
                "ok": False,
                "rewind_only": True,
                "allowed_position": round(max_position, 2),
                "message": "Fast-forwarding is blocked for this lesson.",
            }
        )
        return payload

    if event in {"timeupdate", "pause", "ended"}:
        if position > allowed_forward_position:
            progress.skip_detected = True
            progress.save(update_fields=["skip_detected", "updated_at"])
            payload.update(
                {
                    "ok": False,
                    "rewind_only": True,
                    "allowed_position": round(max_position, 2),
                    "message": "Please watch the lesson in order. Skipping ahead will not unlock the next step.",
                }
            )
            return payload

        if event == "ended" and duration:
            position = max(position, duration)

        if position >= previous_position:
            start = previous_position
            end = position
            if end > start:
                progress.watched_ranges = merge_time_ranges([*progress.watched_ranges, [start, end]])
                progress.max_position_seconds = max(progress.max_position_seconds, end)
                progress.time_spent_seconds = int(round(progress.watched_seconds))
        progress.last_position_seconds = position

    elif event == "play":
        progress.last_position_seconds = position

    elif event == "rewind":
        progress.last_position_seconds = position

    coverage_ratio = progress.coverage_ratio(progress.video_duration_seconds)

    if event == "ended":
        near_end = not progress.video_duration_seconds or position >= max(progress.video_duration_seconds - 3, 0)
        if coverage_ratio >= 0.9 and near_end:
            progress.mark_video_complete()

    progress.save()

    payload.update(
        {
            "video_completed": progress.video_completed,
            "can_advance": progress.can_advance,
            "coverage_ratio": round(progress.coverage_ratio(progress.video_duration_seconds), 4),
            "allowed_position": round(progress.max_position_seconds, 2),
        }
    )
    return payload


def record_lesson_attention(progress: LessonProgress, *, event: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    event = str(event or "").strip().lower()
    now = timezone.now()
    progress.started_at = progress.started_at or now
    if progress.status == LessonProgress.Status.NOT_STARTED:
        progress.status = LessonProgress.Status.IN_PROGRESS

    tracked = list(progress.attention_events or [])
    tracked.append(
        {
            "event": event,
            "at": now.isoformat(),
            "detail": payload,
        }
    )
    progress.attention_events = tracked[-50:]

    if event == "tab_hidden":
        progress.tab_switch_count += 1
        progress.suspicious_event_count += 1
    elif event == "window_blur":
        progress.window_blur_count += 1
        progress.suspicious_event_count += 1
    elif event == "fullscreen_enter":
        progress.fullscreen_entry_count += 1
    elif event == "reading_speed":
        progress.reading_speed_wpm = float(payload.get("wpm") or 0)
        progress.reading_speed_flag = str(payload.get("flag") or "normal")
        if progress.reading_speed_flag == "fast":
            progress.suspicious_event_count += 1

    progress.save(
        update_fields=[
            "status",
            "started_at",
            "tab_switch_count",
            "window_blur_count",
            "fullscreen_entry_count",
            "suspicious_event_count",
            "attention_events",
            "reading_speed_wpm",
            "reading_speed_flag",
            "updated_at",
        ]
    )
    return {
        "ok": True,
        "risk_level": progress.attention_risk_level,
        "tab_switch_count": progress.tab_switch_count,
        "window_blur_count": progress.window_blur_count,
        "fullscreen_entry_count": progress.fullscreen_entry_count,
        "suspicious_event_count": progress.suspicious_event_count,
        "reading_speed_wpm": round(progress.reading_speed_wpm or 0, 1),
        "reading_speed_flag": progress.reading_speed_flag,
    }
