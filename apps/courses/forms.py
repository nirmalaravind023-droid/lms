"""Section-facing forms.

Flow examples:
- CourseForm -> create/edit a section shell
- ModuleForm -> create/edit one module inside a section
- LessonForm -> create/edit one lesson inside a module
- CourseCommentForm -> post learner/HR/admin discussion under a section
"""
from django import forms

from .models import CalendarEvent, Course, CourseComment, Lesson, Module


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "department",
            "status",
            "mandatory",
            "certificate_enabled",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "department": "Sector / Department",
            "title": "Section Name",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["status"].initial = Course.Status.PUBLISHED


class CalendarEventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].label = "Sector / Department"
        self.fields["title"].widget.attrs.update(
            {
                "class": "calendar-input calendar-input-title",
                "placeholder": "Quarterly investment review, compliance training, onboarding session...",
            }
        )
        self.fields["event_type"].widget.attrs.update({"class": "calendar-input calendar-select"})
        self.fields["meeting_type"].widget.attrs.update({"class": "calendar-input calendar-select"})
        self.fields["meeting_url"].widget.attrs.update(
            {"class": "calendar-input", "placeholder": "https://meet.google.com/... or https://zoom.us/..."}
        )
        self.fields["course"].widget.attrs.update({"class": "calendar-input calendar-select"})
        self.fields["department"].widget.attrs.update({"class": "calendar-input calendar-select"})
        self.fields["start_at"].widget.attrs.update({"class": "calendar-input", "data-holiday-date-input": "true"})
        self.fields["end_at"].widget.attrs.update({"class": "calendar-input", "data-holiday-date-input": "true"})
        self.fields["color"].widget.attrs.update({"class": "calendar-color-input"})
        selected_department_id = ""
        if self.is_bound:
            selected_department_id = (self.data.get("department") or "").strip()
        elif getattr(self.instance, "department_id", None):
            selected_department_id = str(self.instance.department_id)
        elif self.initial.get("department"):
            selected_department_id = str(self.initial["department"])
        if selected_department_id:
            self.fields["course"].queryset = self.fields["course"].queryset.filter(department_id=selected_department_id)

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        course = cleaned_data.get("course")
        if department:
            # Keep calendar tasks visually aligned with the department color unless HR/admin overrides later.
            cleaned_data["color"] = department.color
        if department and course and course.department_id != department.id:
            self.add_error("course", "Choose a section from the selected department only.")
        if cleaned_data.get("event_type") == CalendarEvent.EventType.MEETING:
            if not cleaned_data.get("meeting_type"):
                self.add_error("meeting_type", "Choose whether this meeting is a call or a video call.")
            if not cleaned_data.get("meeting_url"):
                self.add_error("meeting_url", "Add the meeting link for this calendar meeting.")
        else:
            cleaned_data["meeting_type"] = ""
            cleaned_data["meeting_url"] = ""
        return cleaned_data

    class Meta:
        model = CalendarEvent
        fields = [
            "title",
            "event_type",
            "meeting_type",
            "meeting_url",
            "course",
            "department",
            "start_at",
            "end_at",
            "color",
        ]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["title", "description", "is_mandatory"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class LessonForm(forms.ModelForm):
    AUTHORING_LESSON_TYPES = [
        (Lesson.LessonType.ARTICLE, "Article"),
        (Lesson.LessonType.PDF, "PDF"),
        (Lesson.LessonType.VIDEO, "Video"),
        (Lesson.LessonType.LINK, "External Link"),
    ]
    VIDEO_FILE_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mpeg", ".mpg"}
    SUBTITLE_FILE_EXTENSIONS = {".srt", ".vtt"}
    IMAGE_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = list(self.AUTHORING_LESSON_TYPES)
        current_type = getattr(self.instance, "lesson_type", "")
        if current_type and current_type not in {value for value, _label in choices}:
            choices.append((current_type, self.instance.get_lesson_type_display()))
        self.fields["lesson_type"].choices = choices
        self.fields["summary"].help_text = "Use this for quick context, recommended books, notes, or material guidance."
        self.fields["external_url"].label = "External / Resource URL"
        self.fields["external_url"].widget.attrs.update(
            {"placeholder": "https://example.com/book.pdf or https://www.youtube.com/watch?v=..."}
        )
        self.fields["media_file"].label = "Upload Video or PDF File"
        self.fields["media_file"].widget.attrs.update({"accept": ".mp4,.webm,.mov,.m4v,.avi,.mpeg,.mpg,.pdf"})
        self.fields["subtitle_file"].widget.attrs.update({"accept": ".srt,.vtt"})
        self.fields["article_image"].widget.attrs.update({"accept": ".jpg,.jpeg,.png,.webp,.gif"})
        self.fields["subtitle_file"].help_text = "Use only .srt or .vtt subtitle files for uploaded video lessons."
        self.fields["content"].help_text = "Best for article-style lessons with notes, guides, and written explanations."

    def clean_external_url(self):
        url = (self.cleaned_data.get("external_url") or "").strip()
        if not url:
            return url
        if self.cleaned_data.get("lesson_type") != Lesson.LessonType.VIDEO:
            return url
        # HR/admin can paste a normal YouTube URL; we normalize it to an embed URL here.
        video_id = Lesson.extract_youtube_video_id(url)
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return url

    def clean(self):
        cleaned_data = super().clean()
        lesson_type = cleaned_data.get("lesson_type")
        content = (cleaned_data.get("content") or "").strip()
        external_url = (cleaned_data.get("external_url") or "").strip()
        article_image = cleaned_data.get("article_image") or getattr(self.instance, "article_image", None)
        media_file = cleaned_data.get("media_file") or getattr(self.instance, "media_file", None)
        subtitle_file = cleaned_data.get("subtitle_file") or getattr(self.instance, "subtitle_file", None)
        article_image_name = (getattr(article_image, "name", "") or "").lower()
        media_name = (getattr(media_file, "name", "") or "").lower()
        subtitle_name = (getattr(subtitle_file, "name", "") or "").lower()

        def file_has_allowed_extension(file_name: str, allowed_extensions: set[str]) -> bool:
            return any(file_name.endswith(extension) for extension in allowed_extensions)

        if lesson_type == Lesson.LessonType.ARTICLE and not content:
            self.add_error("content", "Write the article or learning notes for this lesson.")
        if article_image_name and not file_has_allowed_extension(article_image_name, self.IMAGE_FILE_EXTENSIONS):
            self.add_error("article_image", "Article cover image should be JPG, PNG, WEBP, or GIF.")
        if lesson_type == Lesson.LessonType.LINK and not external_url:
            self.add_error("external_url", "Add the recommended external link, book, or study material URL.")
        if lesson_type == Lesson.LessonType.VIDEO and not (external_url or media_file):
            self.add_error("external_url", "Add a YouTube URL or upload a video file for this lesson.")
            self.add_error("media_file", "Upload a video file if you do not want to use a YouTube URL.")
        if lesson_type == Lesson.LessonType.VIDEO and media_name and not file_has_allowed_extension(media_name, self.VIDEO_FILE_EXTENSIONS):
            self.add_error("media_file", "Video lessons should use MP4, WEBM, MOV, M4V, AVI, MPEG, or MPG files.")
        if lesson_type == Lesson.LessonType.PDF:
            if not (external_url or media_file):
                self.add_error("media_file", "Upload a PDF file or paste a PDF URL for this lesson.")
                self.add_error("external_url", "Paste a PDF URL if you do not want to upload the file.")
            if media_name and not media_name.endswith(".pdf"):
                self.add_error("media_file", "PDF lessons should use a .pdf file.")
        if lesson_type in {Lesson.LessonType.ARTICLE, Lesson.LessonType.LINK} and subtitle_name:
            self.add_error("subtitle_file", "Subtitle files are only supported for uploaded video lessons.")
        if subtitle_name and not file_has_allowed_extension(subtitle_name, self.SUBTITLE_FILE_EXTENSIONS):
            self.add_error("subtitle_file", "Subtitle file should use .srt or .vtt format.")
        if subtitle_name and lesson_type == Lesson.LessonType.VIDEO and not media_file:
            self.add_error("subtitle_file", "Upload a local video file before adding subtitles.")
        if lesson_type != Lesson.LessonType.VIDEO and media_name and any(media_name.endswith(extension) for extension in self.VIDEO_FILE_EXTENSIONS):
            self.add_error("media_file", "Uploaded video files are only valid for Video lessons.")
        return cleaned_data

    class Meta:
        model = Lesson
        fields = [
            "title",
            "lesson_type",
            "summary",
            "article_image",
            "content",
            "external_url",
            "media_file",
            "subtitle_file",
            "transcript",
            "is_mandatory",
        ]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 3}),
            "content": forms.Textarea(attrs={"rows": 6}),
            "transcript": forms.Textarea(attrs={"rows": 4}),
            "external_url": forms.URLInput(attrs={"placeholder": "https://www.youtube.com/watch?v=..."}),
        }
        labels = {
            "article_image": "Article Cover Image",
            "external_url": "External / Resource URL",
            "media_file": "Upload Video or PDF File",
        }


class CourseCommentForm(forms.ModelForm):
    class Meta:
        model = CourseComment
        fields = ["body", "image"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Write a comment, use **bold**, *italic*, __underline__, or list items like - point",
                }
            ),
        }
        labels = {
            "image": "Attach image",
        }
