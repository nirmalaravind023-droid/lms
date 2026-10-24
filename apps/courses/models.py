"""Course-domain models.

This is the main learning data structure:
- Course -> Module -> Lesson
- Enrollment/LessonProgress track learner movement
- CourseComment/CourseNotification support discussion and alerts
"""
import re
from urllib.parse import parse_qs, urlparse

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import slugify

from apps.common.models import OrderedModel, TimeStampedModel


def merge_time_ranges(ranges: list[list[float]]) -> list[list[float]]:
    # Helper for anti-skip video tracking: merges overlapping watched segments.
    cleaned = []
    for item in ranges or []:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        start, end = float(item[0]), float(item[1])
        if end <= start:
            continue
        cleaned.append([max(0.0, start), max(0.0, end)])
    if not cleaned:
        return []
    cleaned.sort(key=lambda item: item[0])
    merged = [cleaned[0]]
    for start, end in cleaned[1:]:
        previous = merged[-1]
        if start <= previous[1] + 0.75:
            previous[1] = max(previous[1], end)
        else:
            merged.append([start, end])
    return merged


def _apply_inline_formatting(text: str) -> str:
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"__(.+?)__", r"<u>\1</u>", text)
    return text


def _parse_table_meta(line: str) -> dict[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("{{table:") or not stripped.endswith("}}"):
        return None
    payload = stripped[len("{{table:"):-2]
    metadata: dict[str, str] = {}
    for pair in payload.split(";"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata or None


def _table_cell_style(*, metadata: dict[str, str], is_header: bool, is_total: bool) -> str:
    styles: list[str] = []
    if is_header:
        if metadata.get("header_bg"):
            styles.append(f"background:{metadata['header_bg']};")
        if metadata.get("header_text"):
            styles.append(f"color:{metadata['header_text']};")
        styles.append("font-weight:700;")
    elif is_total:
        if metadata.get("total_bg"):
            styles.append(f"background:{metadata['total_bg']};")
        if metadata.get("total_text"):
            styles.append(f"color:{metadata['total_text']};")
        styles.append("font-weight:700;")
    return "".join(styles)


def render_rich_text(content: str) -> str:
    lines = escape(content or "").splitlines()
    rendered: list[str] = []
    paragraph: list[str] = []
    in_bullets = False
    in_numbers = False
    in_table = False
    table_row_index = 0
    pending_table_meta: dict[str, str] = {}

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            rendered.append(f"<p>{'<br>'.join(paragraph)}</p>")
            paragraph = []

    def close_lists() -> None:
        nonlocal in_bullets, in_numbers
        if in_bullets:
            rendered.append("</ul>")
            in_bullets = False
        if in_numbers:
            rendered.append("</ol>")
            in_numbers = False

    def close_table() -> None:
        nonlocal in_table, table_row_index
        if in_table:
            rendered.append("</tbody></table>")
            in_table = False
            table_row_index = 0

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            flush_paragraph()
            close_lists()
            close_table()
            continue

        table_meta = _parse_table_meta(stripped)
        if table_meta is not None:
            flush_paragraph()
            close_lists()
            close_table()
            pending_table_meta = table_meta
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            close_lists()
            close_table()
            rendered.append(f"<h4>{_apply_inline_formatting(stripped[4:])}</h4>")
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            close_lists()
            close_table()
            rendered.append(f"<h3>{_apply_inline_formatting(stripped[3:])}</h3>")
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            close_lists()
            close_table()
            rendered.append(f"<h2>{_apply_inline_formatting(stripped[2:])}</h2>")
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            close_table()
            if not in_bullets:
                close_lists()
                rendered.append("<ul>")
                in_bullets = True
            rendered.append(f"<li>{_apply_inline_formatting(stripped[2:])}</li>")
            continue

        ordered_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ordered_match:
            flush_paragraph()
            close_table()
            if not in_numbers:
                close_lists()
                rendered.append("<ol>")
                in_numbers = True
            rendered.append(f"<li>{_apply_inline_formatting(ordered_match.group(1))}</li>")
            continue

        if "|" in stripped and stripped.count("|") >= 2:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if any(cells):
                flush_paragraph()
                close_lists()
                if not in_table:
                    rendered.append("<table class=\"lesson-rich-table\"><tbody>")
                    in_table = True
                    table_row_index = 0
                is_header_row = table_row_index == 0
                is_total_row = any(cell.lower().startswith("total") for cell in cells)
                cell_tag = "th" if is_header_row else "td"
                row_class = "lesson-rich-table-row-total" if is_total_row else ""
                cell_style = _table_cell_style(
                    metadata=pending_table_meta,
                    is_header=is_header_row,
                    is_total=is_total_row,
                )
                style_attr = f' style="{cell_style}"' if cell_style else ""
                rendered.append(
                    f"<tr class=\"{row_class}\">"
                    + "".join(f"<{cell_tag}{style_attr}>{_apply_inline_formatting(cell)}</{cell_tag}>" for cell in cells)
                    + "</tr>"
                )
                table_row_index += 1
                continue

        close_lists()
        close_table()
        paragraph.append(_apply_inline_formatting(stripped))

    flush_paragraph()
    close_lists()
    close_table()
    return mark_safe("".join(rendered))


def build_unique_course_slug(*, title: str, current_slug: str = "", course_id=None) -> str:
    base_slug = slugify(current_slug or title) or "course"
    slug_candidate = base_slug
    suffix = 2

    while Course.objects.exclude(id=course_id).filter(slug=slug_candidate).exists():
        slug_candidate = f"{base_slug}-{suffix}"
        suffix += 1

    return slug_candidate


class Course(TimeStampedModel):
    # Top-level learning object shown in the course library.
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    company = models.ForeignKey("organizations.Company", related_name="courses", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        "organizations.Department",
        related_name="courses",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey("accounts.User", related_name="authored_courses", on_delete=models.SET_NULL, null=True)
    mandatory = models.BooleanField(default=False)
    estimated_minutes = models.PositiveIntegerField(default=0)
    certificate_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("title",)
        unique_together = ("company", "slug")

    def save(self, *args, **kwargs):
        self.slug = build_unique_course_slug(
            title=self.title,
            current_slug=self.slug,
            course_id=self.id,
        )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class Module(OrderedModel):
    course = models.ForeignKey(Course, related_name="modules", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta(OrderedModel.Meta):
        unique_together = ("course", "order")

    def __str__(self) -> str:
        return f"{self.course.title}: {self.title}"


class Lesson(OrderedModel):
    # One lesson can be a video, article, PDF, reading, or external link.
    class LessonType(models.TextChoices):
        VIDEO = "video", "Video"
        ARTICLE = "article", "Article"
        PDF = "pdf", "PDF"
        READING = "reading", "Mandatory Reading"
        LINK = "link", "External Link"

    module = models.ForeignKey(Module, related_name="lessons", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=20, choices=LessonType.choices, default=LessonType.ARTICLE)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    article_image = models.FileField(upload_to="lessons/articles/", blank=True)
    external_url = models.URLField(blank=True)
    media_file = models.FileField(upload_to="lessons/media/", blank=True)
    subtitle_file = models.FileField(upload_to="lessons/subtitles/", blank=True)
    transcript = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    estimated_minutes = models.PositiveIntegerField(default=0)

    class Meta(OrderedModel.Meta):
        unique_together = ("module", "order")

    def __str__(self) -> str:
        return self.title

    @staticmethod
    def extract_youtube_video_id(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        video_id = ""
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/", 1)[0]
        elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif parsed.path.startswith("/embed/"):
                video_id = parsed.path.split("/embed/", 1)[1].split("/", 1)[0]
            elif parsed.path.startswith("/shorts/"):
                video_id = parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
            elif parsed.path.startswith("/live/"):
                video_id = parsed.path.split("/live/", 1)[1].split("/", 1)[0]
        return video_id.strip()

    @property
    def youtube_embed_url(self) -> str:
        video_id = self.extract_youtube_video_id(self.external_url)
        return f"https://www.youtube.com/embed/{video_id}" if video_id else ""

    @property
    def file_extension(self) -> str:
        file_name = getattr(self.media_file, "name", "") or ""
        if "." not in file_name:
            return ""
        return file_name.rsplit(".", 1)[-1].lower()

    @property
    def pdf_resource_url(self) -> str:
        if self.lesson_type != self.LessonType.PDF:
            return ""
        if self.media_file:
            return self.media_file.url
        return self.external_url

    @property
    def opens_in_new_tab(self) -> bool:
        return self.lesson_type in {self.LessonType.PDF, self.LessonType.LINK}

    @property
    def formatted_content(self):
        return render_rich_text(self.content)


class CourseAssignment(TimeStampedModel):
    company = models.ForeignKey("organizations.Company", related_name="course_assignments", on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name="assignments", on_delete=models.CASCADE)
    department = models.ForeignKey(
        "organizations.Department",
        related_name="course_assignments",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    learner = models.ForeignKey(
        "accounts.User",
        related_name="direct_course_assignments",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        related_name="assigned_courses",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    due_date = models.DateField(blank=True, null=True)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        target = self.learner or self.department
        return f"{self.course} -> {target}"


class Enrollment(TimeStampedModel):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        OVERDUE = "overdue", "Overdue"

    learner = models.ForeignKey("accounts.User", related_name="enrollments", on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name="enrollments", on_delete=models.CASCADE)
    assignment = models.ForeignKey(CourseAssignment, related_name="enrollments", on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    due_date = models.DateField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("learner", "course")

    def __str__(self) -> str:
        return f"{self.learner} - {self.course}"


class LessonProgress(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    learner = models.ForeignKey("accounts.User", related_name="lesson_progress", on_delete=models.CASCADE)
    enrollment = models.ForeignKey(Enrollment, related_name="lesson_progress", on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, related_name="progress_records", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    mandatory_checked = models.BooleanField(default=False)
    last_position_seconds = models.FloatField(default=0)
    max_position_seconds = models.FloatField(default=0)
    video_duration_seconds = models.FloatField(default=0)
    watched_ranges = models.JSONField(default=list, blank=True)
    video_completed = models.BooleanField(default=False)
    skip_detected = models.BooleanField(default=False)
    tab_switch_count = models.PositiveIntegerField(default=0)
    window_blur_count = models.PositiveIntegerField(default=0)
    fullscreen_entry_count = models.PositiveIntegerField(default=0)
    suspicious_event_count = models.PositiveIntegerField(default=0)
    attention_events = models.JSONField(default=list, blank=True)
    reading_speed_wpm = models.FloatField(default=0)
    reading_speed_flag = models.CharField(max_length=20, default="normal")

    class Meta:
        unique_together = ("learner", "lesson")

    def __str__(self) -> str:
        return f"{self.learner} - {self.lesson}"

    @property
    def normalized_watched_ranges(self) -> list[list[float]]:
        return merge_time_ranges(self.watched_ranges)

    @property
    def watched_seconds(self) -> float:
        return round(sum(end - start for start, end in self.normalized_watched_ranges), 2)

    def coverage_ratio(self, duration: float | None = None) -> float:
        target = float(duration or self.video_duration_seconds or 0)
        if target <= 0:
            return 0.0
        return min(1.0, self.watched_seconds / target)

    @property
    def can_advance(self) -> bool:
        if self.lesson.lesson_type != Lesson.LessonType.VIDEO or not self.lesson.media_file:
            return self.status == self.Status.COMPLETED
        return self.video_completed

    def mark_video_complete(self) -> None:
        now = timezone.now()
        self.video_completed = True
        self.status = self.Status.COMPLETED
        self.mandatory_checked = True
        self.completed_at = now
        self.started_at = self.started_at or now

    @property
    def attention_risk_level(self) -> str:
        if self.suspicious_event_count >= 5 or self.tab_switch_count >= 3:
            return "high"
        if self.suspicious_event_count >= 2 or self.window_blur_count >= 2:
            return "medium"
        return "low"


class CalendarEvent(TimeStampedModel):
    class EventType(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        ASSIGNMENT = "assignment", "Assignment"
        MODULE = "module", "Module"
        MEETING = "meeting", "Meeting"

    class MeetingType(models.TextChoices):
        CALL = "call", "Call"
        VIDEO = "video", "Video Call"

    company = models.ForeignKey("organizations.Company", related_name="calendar_events", on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name="calendar_events", on_delete=models.SET_NULL, blank=True, null=True)
    department = models.ForeignKey(
        "organizations.Department",
        related_name="calendar_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=255)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.MODULE)
    meeting_type = models.CharField(max_length=20, choices=MeetingType.choices, blank=True)
    meeting_url = models.URLField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(blank=True, null=True)
    color = models.CharField(max_length=20, default="#2563eb")

    class Meta:
        ordering = ("start_at",)

    def __str__(self) -> str:
        return self.title


class CourseComment(TimeStampedModel):
    course = models.ForeignKey(Course, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey("accounts.User", related_name="course_comments", on_delete=models.CASCADE)
    body = models.TextField()
    image = models.FileField(upload_to="course_comments/images/", blank=True)
    parent = models.ForeignKey("self", related_name="replies", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.author} on {self.course}"

    @property
    def formatted_body(self):
        text = escape(self.body or "")
        lines = text.splitlines()
        rendered = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                if not in_list:
                    rendered.append("<ul>")
                    in_list = True
                rendered.append(f"<li>{stripped[2:]}</li>")
            else:
                if in_list:
                    rendered.append("</ul>")
                    in_list = False
                rendered.append(stripped)
        if in_list:
            rendered.append("</ul>")
        html = "<br>".join(rendered)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"__(.+?)__", r"<u>\1</u>", html)
        return mark_safe(html)


class CourseNotification(TimeStampedModel):
    recipient = models.ForeignKey("accounts.User", related_name="received_course_notifications", on_delete=models.CASCADE)
    actor = models.ForeignKey(
        "accounts.User",
        related_name="triggered_course_notifications",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    course = models.ForeignKey(Course, related_name="notifications", on_delete=models.CASCADE)
    comment = models.ForeignKey(CourseComment, related_name="notifications", on_delete=models.CASCADE, blank=True, null=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    @property
    def notification_kind(self) -> str:
        if self.comment_id:
            return "course_comment"
        message = (self.message or "").lower()
        if "video lesson" in message or "lesson" in message:
            return "learning_update"
        if "course updated" in message or "updated" in message:
            return "course_updated"
        if "new course added" in message or "new course" in message or "new section added" in message:
            return "course_added"
        if "congratulations" in message or "approved" in message:
            return "approval_update"
        if "message" in message or "chat" in message:
            return "direct_message"
        if "quiz" in message or "test" in message:
            return "assessment_update"
        return "learning_update"

    @property
    def badge_label(self) -> str:
        return {
            "course_comment": "Course Comment",
            "course_added": "New Course Added",
            "course_updated": "Course Updated",
            "approval_update": "Approval Update",
            "direct_message": "Direct Message",
            "assessment_update": "Assessment Update",
            "learning_update": "Learning Update",
        }.get(self.notification_kind, "Learning Update")

    @property
    def action_label(self) -> str:
        return {
            "course_comment": "Open Comment",
            "course_added": "Open New Course",
            "course_updated": "View Update",
            "approval_update": "Open Course",
            "direct_message": "Open Inbox",
            "assessment_update": "Open Assessment",
            "learning_update": "Open Course",
        }.get(self.notification_kind, "Open Course")

    @property
    def icon_text(self) -> str:
        return {
            "course_comment": "CM",
            "course_added": "NC",
            "course_updated": "UP",
            "approval_update": "OK",
            "direct_message": "DM",
            "assessment_update": "QZ",
            "learning_update": "CR",
        }.get(self.notification_kind, "NT")

    @property
    def accent_class(self) -> str:
        return f"notification-accent-{self.notification_kind}"

    def get_destination_url(self) -> str:
        if self.notification_kind == "direct_message":
            return reverse("conversation-list")
        destination = reverse("course-detail", kwargs={"slug": self.course.slug})
        if self.comment_id:
            destination = f"{destination}#comment-{self.comment_id}"
        return destination

    def __str__(self) -> str:
        return self.message
