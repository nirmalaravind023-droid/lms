from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from django.core.files import File

from .models import Lesson
from .services import ensure_media_dir


@dataclass(slots=True)
class TranscriptChunk:
    start_seconds: float
    end_seconds: float
    text: str


def format_vtt_timestamp(total_seconds: float) -> str:
    total_seconds = max(0.0, float(total_seconds or 0))
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int(round((total_seconds - int(total_seconds)) * 1000))
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


def render_webvtt(chunks: list[TranscriptChunk]) -> str:
    lines = ["WEBVTT", ""]
    for chunk in chunks:
        text = (chunk.text or "").strip()
        if not text:
            continue
        lines.append(f"{format_vtt_timestamp(chunk.start_seconds)} --> {format_vtt_timestamp(chunk.end_seconds)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def extract_audio_track(lesson: Lesson, *, output_format: str = "wav") -> Path:
    if not lesson.media_file:
        raise ValueError("Lesson must have an uploaded video file before extracting audio.")

    output_path = ensure_media_dir(f"lessons/audio/{lesson.id}/source.{output_format}")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        lesson.media_file.path,
        "-vn",
        "-acodec",
        "pcm_s16le" if output_format == "wav" else "copy",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return output_path


class BaseSubtitleEngine:
    def __init__(self, *, language: str = "en"):
        self.language = language

    def transcribe(self, audio_path: Path) -> list[TranscriptChunk]:
        raise NotImplementedError


class WhisperSubtitleEngine(BaseSubtitleEngine):
    def __init__(self, *, model_name: str = "base", language: str = "en"):
        super().__init__(language=language)
        self.model_name = model_name

    def transcribe(self, audio_path: Path) -> list[TranscriptChunk]:
        try:
            import whisper
        except ImportError as exc:
            raise RuntimeError("Install openai-whisper to generate subtitles with Whisper.") from exc

        model = whisper.load_model(self.model_name)
        result = model.transcribe(str(audio_path), language=self.language, verbose=False)
        return [
            TranscriptChunk(
                start_seconds=float(segment["start"]),
                end_seconds=float(segment["end"]),
                text=str(segment["text"]).strip(),
            )
            for segment in result.get("segments", [])
        ]


class GoogleSpeechSubtitleEngine(BaseSubtitleEngine):
    def transcribe(self, audio_path: Path) -> list[TranscriptChunk]:
        try:
            from google.cloud import speech_v1p1beta1 as speech
        except ImportError as exc:
            raise RuntimeError("Install google-cloud-speech to generate subtitles with Google Speech-to-Text.") from exc

        client = speech.SpeechClient()
        with audio_path.open("rb") as audio_stream:
            content = audio_stream.read()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=self.language,
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
        )
        audio = speech.RecognitionAudio(content=content)
        response = client.recognize(config=config, audio=audio)
        chunks = []
        for result in response.results:
            alternative = result.alternatives[0]
            words = list(alternative.words)
            if words:
                chunks.append(
                    TranscriptChunk(
                        start_seconds=words[0].start_time.total_seconds(),
                        end_seconds=words[-1].end_time.total_seconds(),
                        text=alternative.transcript.strip(),
                    )
                )
        return chunks


class VoskSubtitleEngine(BaseSubtitleEngine):
    def __init__(self, *, model_path: str, language: str = "en-us"):
        super().__init__(language=language)
        self.model_path = model_path

    def transcribe(self, audio_path: Path) -> list[TranscriptChunk]:
        try:
            from vosk import KaldiRecognizer, Model
        except ImportError as exc:
            raise RuntimeError("Install vosk to generate subtitles with the Vosk engine.") from exc

        model = Model(self.model_path)
        recognizer = KaldiRecognizer(model, 16000)
        recognizer.SetWords(True)
        chunks = []
        with audio_path.open("rb") as audio_stream:
            while True:
                data = audio_stream.read(4000)
                if not data:
                    break
                if recognizer.AcceptWaveform(data):
                    payload = json.loads(recognizer.Result())
                    words = payload.get("result", [])
                    if words:
                        chunks.append(
                            TranscriptChunk(
                                start_seconds=float(words[0]["start"]),
                                end_seconds=float(words[-1]["end"]),
                                text=str(payload.get("text", "")).strip(),
                            )
                        )
        final_payload = json.loads(recognizer.FinalResult())
        words = final_payload.get("result", [])
        if words:
            chunks.append(
                TranscriptChunk(
                    start_seconds=float(words[0]["start"]),
                    end_seconds=float(words[-1]["end"]),
                    text=str(final_payload.get("text", "")).strip(),
                )
            )
        return chunks


def generate_lesson_subtitles(
    lesson: Lesson,
    *,
    provider: str = "whisper",
    language: str = "en",
    whisper_model: str = "base",
    vosk_model_path: str | None = None,
) -> Path:
    if provider == "whisper":
        engine = WhisperSubtitleEngine(model_name=whisper_model, language=language)
    elif provider == "google":
        engine = GoogleSpeechSubtitleEngine(language=language)
    elif provider == "vosk":
        if not vosk_model_path:
            raise ValueError("A Vosk model path is required when provider='vosk'.")
        engine = VoskSubtitleEngine(model_path=vosk_model_path, language=language)
    else:
        raise ValueError(f"Unsupported subtitle provider: {provider}")

    audio_path = extract_audio_track(lesson)
    chunks = engine.transcribe(audio_path)
    if not chunks:
        raise RuntimeError("No transcript chunks were generated for this lesson.")

    vtt_path = ensure_media_dir(f"lessons/subtitles/generated/{lesson.id}.vtt")
    vtt_path.write_text(render_webvtt(chunks), encoding="utf-8")

    with vtt_path.open("rb") as generated_file:
        lesson.subtitle_file.save(vtt_path.name, File(generated_file), save=False)
    lesson.transcript = "\n".join(chunk.text for chunk in chunks if chunk.text)
    lesson.save(update_fields=["subtitle_file", "transcript", "updated_at"])
    return vtt_path
