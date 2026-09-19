from __future__ import annotations

"""Section app views.

This file was restored after being accidentally overwritten with only one view.
The goal of this module is to keep the existing LMS flows working:
- learner section library, detail, lesson, completion
- HR/admin section authoring and builder actions
- notifications and calendar pages
- small JSON endpoints for drag/drop and lesson telemetry
"""

import calendar
import json
from datetime import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, TemplateView, UpdateView

from apps.accounts.models import User, UserLifecycleRequest
from apps.assessments.models import Quiz
from apps.common.holidays import get_holiday_calendars, get_india_holiday_map, group_holidays_by_day
from apps.common.pagination import paginate_items
from apps.common.services import create_admin_audit_log, create_learning_audit_event, snapshot_model
from apps.organizations.models import Department
from apps.certificates.models import Certificate
from apps.certificates.services import ensure_module_certificates, issue_certificate

from .forms import CalendarEventForm, CourseCommentForm, CourseForm, LessonForm, ModuleForm
from .models import CalendarEvent, Course, CourseComment, CourseNotification, Enrollment, Lesson, LessonProgress, Module
from .services import parse_json_request, record_lesson_attention, record_video_playback, reorder_lessons, reorder_modules
from .video import normalize_subtitle_file


def _notification_recipients_for_course(course: Course, *, actor: User | None = None):
    recipients = User.objects.filter(
        company=course.company,
        role=User.Role.LEARNER,
        is_active=True,
    )
    if course.department_id:
        recipients = recipients.filter(department=course.department)
    if actor:
        recipients = recipients.exclude(id=actor.id)
    return recipients.distinct()


def _broadcast_course_notification(*, course: Course, actor: User | None, message: str) -> None:
    for recipient in _notification_recipients_for_course(course, actor=actor):
        CourseNotification.objects.create(
            recipient=recipient,
            actor=actor,
            course=course,
            message=message,
        )


def manageable_departments_for_user(user: User):
    if not user.company_id:
        return Department.objects.none()
    departments = user.company.departments.order_by("name")
    if user.is_manager_like or user.is_admin_like:
        return departments
    if user.department_id:
        return departments.filter(id=user.department_id)
    return Department.objects.none()


class CompanyScopedMixin:
    def company_queryset(self, queryset, *, lookup: str = "company"):
        user = self.request.user
        if not getattr(user, "is_authenticated", False):
            return queryset.none()
        if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
            return queryset
        if not user.company_id:
            return queryset.none()
        return queryset.filter(**{lookup: user.company})


class CourseAuthorMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_manager_like or user.is_admin_like


class CourseListView(LoginRequiredMixin, CompanyScopedMixin, TemplateView):
    template_name = "courses/course_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        published_courses = self.company_queryset(
            Course.objects.select_related("department", "created_by").filter(status=Course.Status.PUBLISHED)
        )

        if user.is_admin_like or user.is_manager_like:
            courses = list(published_courses.order_by("title"))
        else:
            enrollments = list(
                Enrollment.objects.filter(learner=user)
                .select_related("course", "course__department")
                .order_by("course__title")
            )
            enrolled_course_ids = {enrollment.course_id for enrollment in enrollments}
            available_courses = list(
                published_courses.filter(Q(department_id=user.department_id) | Q(department__isnull=True))
                .exclude(id__in=enrolled_course_ids)
                .order_by("title")
            )
            courses = [*enrollments, *available_courses]

        context["courses"] = courses
        return context


class CourseDetailView(LoginRequiredMixin, CompanyScopedMixin, DetailView):
    template_name = "courses/course_detail.html"
    context_object_name = "course"
    model = Course
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        queryset = self.company_queryset(
            Course.objects.select_related("department", "created_by").prefetch_related("modules__lessons", "modules__quizzes", "quizzes")
        )
        user = self.request.user
        if user.is_admin_like or user.is_manager_like:
            return queryset
        return queryset.filter(status=Course.Status.PUBLISHED)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = context["course"]
        user = self.request.user
        comments = course.comments.filter(parent__isnull=True).select_related("author").prefetch_related("replies__author")
        first_module = course.modules.order_by("order", "created_at").first()
        first_lesson = first_module.lessons.order_by("order", "created_at").first() if first_module else None
        learner_enrollment = Enrollment.objects.filter(learner=user, course=course).first() if user.role == User.Role.LEARNER else None
        module_level_quiz_ids = course.modules.values_list("quizzes__id", flat=True)
        course_level_quizzes = course.quizzes.exclude(id__in=module_level_quiz_ids).distinct()
        if user.role == User.Role.LEARNER:
            course_level_quizzes = course_level_quizzes.filter(status=Quiz.Status.PUBLISHED)

        context.update(
            {
                "comments": comments,
                "comment_form": CourseCommentForm(),
                "first_lesson": first_lesson,
                "learner_enrollment": learner_enrollment,
                "course_level_quizzes": course_level_quizzes,
            }
        )
        return context


class CourseManageListView(CourseAuthorMixin, CompanyScopedMixin, TemplateView):
    template_name = "courses/course_manage_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.company_queryset(Course.objects.select_related("department").prefetch_related("modules"))
        selected_department = self.request.GET.get("department", "").strip()
        search = self.request.GET.get("q", "").strip()
        if selected_department:
            queryset = queryset.filter(department_id=selected_department)
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

        paginated = paginate_items(self.request, queryset.order_by("title"), per_page=9, page_param="course_page")
        context.update(
            {
                "courses": paginated["items"],
                "courses_page": paginated["page_obj"],
                "courses_page_numbers": paginated["page_numbers"],
                "courses_pagination_query": paginated["pagination_query"],
                "courses_page_param": paginated["page_param"],
                "departments": manageable_departments_for_user(self.request.user),
                "selected_department": selected_department,
            }
        )
        return context

class CourseCreateView(CourseAuthorMixin, CompanyScopedMixin, CreateView):
    template_name = "courses/course_form.html"
    form_class = CourseForm
    model = Course

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.user.company_id:
            form.fields["department"].queryset = manageable_departments_for_user(self.request.user)
        return form

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        if self.object.status == Course.Status.PUBLISHED:
            _broadcast_course_notification(
                course=self.object,
                actor=self.request.user,
                message=f"New section added: {self.object.title} is now available for you.",
            )
        create_admin_audit_log(
            action="course_created",
            actor=self.request.user,
            department=self.object.department,
            entity_type="course",
            entity_id=str(self.object.id),
            after_json=snapshot_model(
                self.object,
                fields=["id", "title", "slug", "status", "mandatory", "estimated_minutes", "certificate_enabled", "department"],
            ),
        )
        messages.success(self.request, "Section created successfully.")
        return response

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.object.slug})


class CourseUpdateView(CourseAuthorMixin, CompanyScopedMixin, UpdateView):
    template_name = "courses/course_form.html"
    form_class = CourseForm
    model = Course
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return self.company_queryset(Course.objects.select_related("department"))

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.user.company_id:
            form.fields["department"].queryset = manageable_departments_for_user(self.request.user)
        return form

    def form_valid(self, form):
        previous_course = self.get_object()
        before_snapshot = snapshot_model(
            previous_course,
            fields=["id", "title", "slug", "status", "mandatory", "estimated_minutes", "certificate_enabled", "department"],
        )
        response = super().form_valid(form)
        if self.object.status == Course.Status.PUBLISHED:
            if previous_course.status != Course.Status.PUBLISHED:
                message = f"New section added: {self.object.title} is now available for you."
            else:
                message = f"Section updated: {self.object.title} has new changes. Open it to review the latest content."
            _broadcast_course_notification(
                course=self.object,
                actor=self.request.user,
                message=message,
            )
        create_admin_audit_log(
            action="course_updated",
            actor=self.request.user,
            department=self.object.department,
            entity_type="course",
            entity_id=str(self.object.id),
            before_json=before_snapshot,
            after_json=snapshot_model(
                self.object,
                fields=["id", "title", "slug", "status", "mandatory", "estimated_minutes", "certificate_enabled", "department"],
            ),
        )
        messages.success(self.request, "Section updated successfully.")
        return response

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.object.slug})


class CourseDeleteView(CourseAuthorMixin, CompanyScopedMixin, DeleteView):
    template_name = "courses/course_confirm_delete.html"
    model = Course
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return self.company_queryset(Course.objects.select_related("department"))

    def get_object(self, queryset=None):
        if self.kwargs.get(self.slug_url_kwarg):
            return super().get_object(queryset)
        if self.kwargs.get("pk"):
            self.pk_url_kwarg = "pk"
            return super().get_object(queryset)
        raise Http404("No section identifier (slug or pk) provided in the URL.")

    def form_valid(self, form):
        before_snapshot = snapshot_model(
            self.object,
            fields=["id", "title", "slug", "status", "mandatory", "estimated_minutes", "certificate_enabled", "department"],
        )
        messages.success(self.request, "Section deleted successfully.")
        create_admin_audit_log(
            action="course_deleted",
            actor=self.request.user,
            department=self.object.department,
            entity_type="course",
            entity_id=str(self.object.id),
            before_json=before_snapshot,
        )
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("course-manage-list").url


class CourseBuilderView(CourseAuthorMixin, CompanyScopedMixin, DetailView):
    template_name = "courses/course_builder.html"
    context_object_name = "course"
    model = Course
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return self.company_queryset(
            Course.objects.select_related("department").prefetch_related("modules__lessons")
        )


class ModuleCreateView(CourseAuthorMixin, CompanyScopedMixin, CreateView):
    template_name = "courses/module_form.html"
    form_class = ModuleForm
    model = Module

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            self.company_queryset(Course.objects.select_related("department")),
            slug=kwargs["slug"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context

    def form_valid(self, form):
        form.instance.course = self.course
        form.instance.order = self.course.modules.count() + 1
        response = super().form_valid(form)
        messages.success(self.request, "Module created successfully.")
        return response

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.course.slug})


class ModuleUpdateView(CourseAuthorMixin, CompanyScopedMixin, UpdateView):
    template_name = "courses/module_form.html"
    form_class = ModuleForm
    model = Module
    pk_url_kwarg = "module_id"

    def get_queryset(self):
        return self.company_queryset(Module.objects.select_related("course", "course__department"), lookup="course__company")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object.course
        return context

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.object.course.slug})


class ModuleDeleteView(CourseAuthorMixin, CompanyScopedMixin, DeleteView):
    template_name = "courses/module_confirm_delete.html"
    model = Module
    pk_url_kwarg = "module_id"

    def get_queryset(self):
        return self.company_queryset(Module.objects.select_related("course"), lookup="course__company")

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.object.course.slug})


class LessonCreateView(CourseAuthorMixin, CompanyScopedMixin, CreateView):
    template_name = "courses/lesson_form.html"
    form_class = LessonForm
    model = Lesson

    def dispatch(self, request, *args, **kwargs):
        self.module = get_object_or_404(
            self.company_queryset(Module.objects.select_related("course", "course__department"), lookup="course__company"),
            id=kwargs["module_id"],
        )
        self.course = self.module.course
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["module"] = self.module
        context["course"] = self.course
        return context

    def form_valid(self, form):
        form.instance.module = self.module
        form.instance.order = self.module.lessons.count() + 1
        response = super().form_valid(form)
        normalize_subtitle_file(self.object)
        if self.object.subtitle_file or self.object.transcript:
            self.object.save(update_fields=["subtitle_file", "transcript", "updated_at"])
        messages.success(self.request, "Lesson created successfully.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Lesson Upload Error")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.course.slug})


class LessonUpdateView(CourseAuthorMixin, CompanyScopedMixin, UpdateView):
    template_name = "courses/lesson_form.html"
    form_class = LessonForm
    model = Lesson
    pk_url_kwarg = "lesson_id"

    def get_queryset(self):
        return self.company_queryset(
            Lesson.objects.select_related("module", "module__course", "module__course__department"),
            lookup="module__course__company",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["module"] = self.object.module
        context["course"] = self.object.module.course
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        normalize_subtitle_file(self.object)
        if self.object.subtitle_file or self.object.transcript:
            self.object.save(update_fields=["subtitle_file", "transcript", "updated_at"])
        messages.success(self.request, "Lesson updated successfully.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Lesson Upload Error")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.object.module.course.slug})


class LessonDeleteView(CourseAuthorMixin, CompanyScopedMixin, DeleteView):
    template_name = "courses/lesson_confirm_delete.html"
    model = Lesson
    pk_url_kwarg = "lesson_id"

    def get_queryset(self):
        return self.company_queryset(Lesson.objects.select_related("module", "module__course"), lookup="module__course__company")

    def get_success_url(self):
        return reverse("course-builder", kwargs={"slug": self.object.module.course.slug})


class CourseCompletionView(LoginRequiredMixin, CompanyScopedMixin, DetailView):
    template_name = "courses/course_complete.html"
    context_object_name = "course"
    model = Course
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return self.company_queryset(Course.objects.select_related("department"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        enrollment, _created = Enrollment.objects.get_or_create(
            learner=self.request.user,
            course=course,
            defaults={"status": Enrollment.Status.IN_PROGRESS},
        )
        if enrollment.status != Enrollment.Status.COMPLETED:
            enrollment.status = Enrollment.Status.COMPLETED
            enrollment.completion_percentage = 100
            enrollment.completed_at = enrollment.completed_at or datetime.now().astimezone()
            enrollment.save(update_fields=["status", "completion_percentage", "completed_at", "updated_at"])

        next_quiz = (
            Quiz.objects.filter(
                Q(course=course, status=Quiz.Status.PUBLISHED)
                | Q(module__course=course, status=Quiz.Status.PUBLISHED)
                | Q(assignments__learner=self.request.user, course=course)
            )
            .distinct()
            .first()
        )
        next_item = (
            Enrollment.objects.filter(learner=self.request.user)
            .exclude(course=course)
            .exclude(status=Enrollment.Status.COMPLETED)
            .select_related("course")
            .first()
        )
        if not next_item:
            next_item = (
                self.company_queryset(Course.objects.filter(status=Course.Status.PUBLISHED))
                .exclude(id=course.id)
                .filter(Q(department=self.request.user.department) | Q(department__isnull=True))
                .first()
            )

        certificate = None
        module_certificates = []
        if course.certificate_enabled:
            module_certificates = ensure_module_certificates(enrollment)
        if course.certificate_enabled and enrollment.status == Enrollment.Status.COMPLETED:
            certificate = Certificate.objects.filter(learner=self.request.user, course=course, module__isnull=True).order_by("-issued_at").first()
            if certificate is None:
                certificate = issue_certificate(enrollment)

        context.update({
            "enrollment": enrollment,
            "next_quiz": next_quiz,
            "next_item": next_item,
            "certificate": certificate,
            "module_certificates": module_certificates,
        })
        return context


class CourseCommentCreateView(LoginRequiredMixin, CompanyScopedMixin, View):
    def post(self, request, slug):
        course = get_object_or_404(self.company_queryset(Course.objects.select_related("department", "created_by")), slug=slug)
        form = CourseCommentForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Could not post comment. Please check the fields and try again.")
            return redirect("course-detail", slug=slug)

        comment = form.save(commit=False)
        comment.course = course
        comment.author = request.user
        parent_id = request.POST.get("parent")
        if parent_id:
            comment.parent = CourseComment.objects.filter(course=course, id=parent_id).first()
        comment.save()

        recipients = []
        if course.created_by_id and course.created_by_id != request.user.id:
            recipients.append(course.created_by)
        manager_recipients = User.objects.filter(
            company=course.company,
            role__in=[User.Role.COMPANY_ADMIN, User.Role.HR_MANAGER],
        ).exclude(id=request.user.id)
        recipients.extend(manager_recipients)

        seen_user_ids = set()
        for recipient in recipients:
            if not recipient or recipient.id in seen_user_ids:
                continue
            seen_user_ids.add(recipient.id)
            CourseNotification.objects.create(
                recipient=recipient,
                actor=request.user,
                course=course,
                comment=comment,
                message=f"New comment on {course.title}.",
            )

        create_learning_audit_event(
            event_type="course_comment_created",
            actor=request.user,
            learner=request.user if request.user.role == User.Role.LEARNER else None,
            course=course,
            department=course.department,
            entity_type="course_comment",
            entity_id=str(comment.id),
            metadata={"course_slug": course.slug},
        )
        messages.success(request, "Comment posted.")
        return redirect("course-detail", slug=slug)


class NotificationListView(LoginRequiredMixin, CompanyScopedMixin, TemplateView):
    template_name = "courses/notification_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notifications_qs = (
            CourseNotification.objects.filter(recipient=self.request.user)
            .select_related("course", "comment", "actor")
            .order_by("-created_at")
        )
        notifications_qs.filter(is_read=False).update(is_read=True)
        paginated = paginate_items(self.request, notifications_qs, per_page=12, page_param="notification_page")

        pending_requests = UserLifecycleRequest.objects.select_related("target_user", "requested_department").filter(
            status=UserLifecycleRequest.Status.PENDING
        )
        if self.request.user.company_id:
            pending_requests = pending_requests.filter(target_user__company=self.request.user.company)

        context.update(
            {
                "notifications": paginated["items"],
                "notifications_page": paginated["page_obj"],
                "notifications_page_numbers": paginated["page_numbers"],
                "notifications_pagination_query": paginated["pagination_query"],
                "notifications_page_param": paginated["page_param"],
                "pending_lifecycle_requests": list(pending_requests[:20]),
                "company_departments": manageable_departments_for_user(self.request.user),
            }
        )
        return context


class NotificationOpenView(LoginRequiredMixin, View):
    def get(self, request, notification_id):
        notification = get_object_or_404(
            CourseNotification.objects.select_related("course"),
            id=notification_id,
            recipient=request.user,
        )
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read", "updated_at"])
        return redirect(notification.get_destination_url())


class CalendarBoardView(LoginRequiredMixin, TemplateView):
    template_name = "courses/calendar_board.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_month = int(self.request.GET.get("month") or datetime.now().month)
        current_year = int(self.request.GET.get("year") or datetime.now().year)
        context.update(
            {
                "current_month": current_month,
                "display_year": current_year,
                "selected_department": self.request.GET.get("department", "").strip(),
            }
        )
        return context


class CalendarBoardDataView(LoginRequiredMixin, CompanyScopedMixin, View):
    def get(self, request):
        today = datetime.now().date()
        month = int(request.GET.get("month") or today.month)
        year = int(request.GET.get("year") or today.year)
        can_manage = request.user.is_manager_like or request.user.is_admin_like
        selected_department = request.GET.get("department", "").strip()
        if not can_manage and request.user.department_id:
            selected_department = str(request.user.department_id)
        month_cal = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
        event_qs = self.company_queryset(CalendarEvent.objects.select_related("course", "department"))
        if selected_department:
            event_qs = event_qs.filter(Q(department_id=selected_department) | Q(department__isnull=True))
        event_qs = event_qs.filter(start_at__year=year, start_at__month=month)
        total_event_count = event_qs.count()
        quiz_count = event_qs.filter(event_type=CalendarEvent.EventType.QUIZ).count()
        assignment_count = event_qs.filter(event_type=CalendarEvent.EventType.ASSIGNMENT).count()
        task_count = event_qs.exclude(event_type__in=[CalendarEvent.EventType.QUIZ, CalendarEvent.EventType.ASSIGNMENT]).count()
        department_list = manageable_departments_for_user(request.user)
        if not can_manage and request.user.department_id:
            department_list = department_list.filter(id=request.user.department_id)
        events_by_day: dict[str, list[dict]] = {}
        for event in event_qs:
            edit_url = reverse("calendar-event-edit", kwargs={"event_id": event.id}) if can_manage else ""
            if event.meeting_url:
                open_url = event.meeting_url
            elif event.course_id:
                open_url = reverse("course-detail", kwargs={"slug": event.course.slug})
            else:
                open_url = ""
            subtitle_parts = []
            if event.department:
                subtitle_parts.append(event.department.name)
            subtitle_parts.append(event.start_at.strftime("%d %b, %I:%M %p"))
            section_title = event.course.title if event.course_id else ""
            event_scope = []
            if section_title:
                event_scope.append(f"Section: {section_title}")
            if event.event_type == CalendarEvent.EventType.MODULE:
                event_scope.append("Module milestone")
            elif event.event_type == CalendarEvent.EventType.QUIZ:
                event_scope.append("Assessment deadline")
            elif event.event_type == CalendarEvent.EventType.ASSIGNMENT:
                event_scope.append("Assignment task")
            elif event.event_type == CalendarEvent.EventType.MEETING:
                event_scope.append("Meeting task")
            events_by_day.setdefault(event.start_at.date().isoformat(), []).append(
                {
                    "kind": "task",
                    "id": str(event.id),
                    "title": event.title,
                    "type": event.event_type,
                    "type_label": event.get_event_type_display(),
                    "subtitle": " | ".join(subtitle_parts),
                    "url": open_url,
                    "open_url": open_url,
                    "edit_url": edit_url,
                    "color": event.color,
                    "department": str(event.department) if event.department else "",
                    "department_color": getattr(event.department, "color", event.color),
                    "section_title": section_title,
                    "overview_lines": event_scope,
                    "start_label": event.start_at.strftime("%A, %d %B %Y"),
                    "start_time_label": event.start_at.strftime("%I:%M %p"),
                    "end_time_label": event.end_at.strftime("%I:%M %p") if event.end_at else "",
                    "meeting_type_label": event.get_meeting_type_display() if event.meeting_type else "",
                }
            )

        holidays_by_day = group_holidays_by_day(year)
        holiday_item_count = sum(len(items) for items in holidays_by_day.values())
        holiday_counts: dict[str, int] = {}
        for holiday_items in holidays_by_day.values():
            for holiday in holiday_items:
                key = holiday["calendar_key"]
                holiday_counts[key] = holiday_counts.get(key, 0) + 1
        weeks = []
        for week in month_cal:
            week_cells = []
            for day in week:
                iso_date = day.isoformat()
                create_url = ""
                if can_manage:
                    query = {"next": reverse("calendar-board")}
                    if selected_department:
                        query["department"] = selected_department
                    create_url = f"{reverse('calendar-event-create')}?{urlencode(query)}"
                holiday_items = [
                    {
                        "kind": "holiday",
                        "id": f"holiday-{holiday['calendar_key']}-{iso_date}",
                        "title": holiday["label"],
                        "type_label": holiday["calendar_label"],
                        "subtitle": holiday["scope"],
                        "url": "",
                        "color": holiday["color"],
                        "holiday_calendar_key": holiday["calendar_key"],
                        "holiday_calendar_label": holiday["calendar_label"],
                    }
                    for holiday in holidays_by_day.get(iso_date, [])
                ]
                week_cells.append(
                    {
                        "iso_date": iso_date,
                        "day": day.day,
                        "in_month": day.month == month,
                        "is_today": day == today,
                        "create_url": create_url,
                        "events": [*holiday_items, *events_by_day.get(iso_date, [])],
                    }
                )
            weeks.append(week_cells)

        previous_month = 12 if month == 1 else month - 1
        previous_year = year - 1 if month == 1 else year
        next_month = 1 if month == 12 else month + 1
        next_year = year + 1 if month == 12 else year
        detail_rows = [
            {
                "label": "Visible Department",
                "value": next(
                    (department.name for department in department_list if str(department.id) == selected_department),
                    "All Teams" if can_manage else (request.user.department.name if request.user.department_id else "My Team"),
                ),
                "hint": "The board reflects the currently selected department scope.",
            },
            {
                "label": "Holiday Items",
                "value": holiday_item_count,
                "hint": "National and cultural holidays mixed into the board.",
            },
            {
                "label": "Manage Access",
                "value": "Enabled" if can_manage else "Learner View",
                "hint": "Managers can add and edit tasks directly from the calendar.",
            },
        ]

        return JsonResponse(
            {
                "current_month": month,
                "month": month,
                "year": year,
                "display_month": calendar.month_name[month],
                "display_year": year,
                "selected_department": selected_department,
                "departments": [
                    {
                        "id": str(department.id),
                        "name": department.name,
                        "color": getattr(department, "color", "#2563eb"),
                    }
                    for department in department_list
                ],
                "holiday_filters": [
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "color": item["color"],
                        "count": holiday_counts.get(item["key"], 0),
                    }
                    for item in get_holiday_calendars()
                ],
                "is_learner": not can_manage,
                "can_manage": can_manage,
                "create_task_url": reverse("calendar-event-create") if can_manage else "",
                "previous_month": previous_month,
                "previous_year": previous_year,
                "next_month": next_month,
                "next_year": next_year,
                "calendar_summary": {
                    "total_items": total_event_count,
                    "quiz_items": quiz_count,
                    "assignment_items": assignment_count,
                    "task_items": task_count,
                    "holiday_items": holiday_item_count,
                },
                "calendar_detail_rows": detail_rows,
                "weeks": weeks,
            }
        )


class CalendarManageListView(CourseAuthorMixin, CompanyScopedMixin, TemplateView):
    template_name = "courses/calendar_manage_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.company_queryset(CalendarEvent.objects.select_related("course", "department"))
        selected_department = self.request.GET.get("department", "").strip()
        if selected_department:
            queryset = queryset.filter(department_id=selected_department)
        paginated = paginate_items(self.request, queryset.order_by("start_at"), per_page=12, page_param="event_page")
        context.update(
            {
                "events": paginated["items"],
                "events_page": paginated["page_obj"],
                "events_page_numbers": paginated["page_numbers"],
                "events_pagination_query": paginated["pagination_query"],
                "events_page_param": paginated["page_param"],
                "departments": manageable_departments_for_user(self.request.user),
                "selected_department": selected_department,
            }
        )
        return context


class CalendarEventCreateView(CourseAuthorMixin, CompanyScopedMixin, CreateView):
    template_name = "courses/calendar_event_form.html"
    form_class = CalendarEventForm
    model = CalendarEvent

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        departments = manageable_departments_for_user(self.request.user)
        form.fields["department"].queryset = departments
        course_queryset = self.company_queryset(Course.objects.select_related("department"))
        if self.request.GET.get("department"):
            course_queryset = course_queryset.filter(department_id=self.request.GET["department"])
        form.fields["course"].queryset = course_queryset
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["return_to"] = self.request.GET.get("next", "").strip()
        context["india_holiday_map_json"] = get_india_holiday_map([datetime.now().year, datetime.now().year + 1])
        courses = list(
            self.company_queryset(Course.objects.select_related("department").order_by("title")).values(
                "id", "title", "slug", "department_id"
            )
        )
        context["calendar_task_course_options"] = courses
        context["quiz_create_url"] = reverse("quiz-create")
        return context

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        if form.instance.department and not form.instance.color:
            form.instance.color = form.instance.department.color
        messages.success(self.request, "Calendar task created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.POST.get("next") or reverse("calendar-manage-list")


class CalendarEventUpdateView(CourseAuthorMixin, CompanyScopedMixin, UpdateView):
    template_name = "courses/calendar_event_form.html"
    form_class = CalendarEventForm
    model = CalendarEvent
    pk_url_kwarg = "event_id"

    def get_queryset(self):
        return self.company_queryset(CalendarEvent.objects.select_related("course", "department"))

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        departments = manageable_departments_for_user(self.request.user)
        form.fields["department"].queryset = departments
        form.fields["course"].queryset = self.company_queryset(Course.objects.select_related("department"))
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["return_to"] = self.request.GET.get("next", "").strip()
        context["india_holiday_map_json"] = get_india_holiday_map([datetime.now().year, datetime.now().year + 1])
        courses = list(
            self.company_queryset(Course.objects.select_related("department").order_by("title")).values(
                "id", "title", "slug", "department_id"
            )
        )
        context["calendar_task_course_options"] = courses
        context["quiz_create_url"] = reverse("quiz-create")
        return context

    def form_valid(self, form):
        messages.success(self.request, "Calendar task updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.POST.get("next") or reverse("calendar-manage-list")


class CalendarEventDeleteView(CourseAuthorMixin, CompanyScopedMixin, DeleteView):
    template_name = "courses/calendar_event_confirm_delete.html"
    model = CalendarEvent
    pk_url_kwarg = "event_id"

    def get_queryset(self):
        return self.company_queryset(CalendarEvent.objects.select_related("course", "department"))

    def get_success_url(self):
        messages.success(self.request, "Calendar task deleted successfully.")
        return reverse("calendar-manage-list")


class ModuleReorderView(CourseAuthorMixin, View):
    def post(self, request):
        try:
            payload = parse_json_request(request.body)
            reorder_modules(payload)
            return JsonResponse({"ok": True})
        except Exception as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)


class LessonReorderView(CourseAuthorMixin, View):
    def post(self, request):
        try:
            payload = parse_json_request(request.body)
            reorder_lessons(payload)
            return JsonResponse({"ok": True})
        except Exception as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)


class LessonDetailView(LoginRequiredMixin, CompanyScopedMixin, DetailView):
    template_name = "courses/lesson_detail.html"
    context_object_name = "lesson"
    model = Lesson
    pk_url_kwarg = "lesson_id"

    def get_queryset(self):
        return self.company_queryset(
            Lesson.objects.select_related("module", "module__course", "module__course__department"),
            lookup="module__course__company",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object
        module = lesson.module
        course = module.course
        ordered_lessons = list(module.lessons.order_by("order", "created_at"))
        lesson_index = ordered_lessons.index(lesson)
        previous_lesson = ordered_lessons[lesson_index - 1] if lesson_index > 0 else None
        next_lesson = ordered_lessons[lesson_index + 1] if lesson_index + 1 < len(ordered_lessons) else None
        next_quiz = module.quizzes.filter(status=Quiz.Status.PUBLISHED).first()

        enrollment = None
        progress = None
        can_advance = True
        article_reading_required_seconds = 0
        article_reading_remaining_seconds = 0
        article_can_complete = True
        attention_warning = ""

        if self.request.user.role == User.Role.LEARNER:
            enrollment, _created = Enrollment.objects.get_or_create(
                learner=self.request.user,
                course=course,
                defaults={"status": Enrollment.Status.IN_PROGRESS},
            )
            progress, _created = LessonProgress.objects.get_or_create(
                learner=self.request.user,
                enrollment=enrollment,
                lesson=lesson,
            )
            if progress.status == LessonProgress.Status.NOT_STARTED:
                progress.status = LessonProgress.Status.IN_PROGRESS
                progress.started_at = progress.started_at or datetime.now().astimezone()
                progress.save(update_fields=["status", "started_at", "updated_at"])

            if lesson.lesson_type == Lesson.LessonType.VIDEO and lesson.media_file:
                can_advance = progress.can_advance
            if lesson.lesson_type in {Lesson.LessonType.ARTICLE, Lesson.LessonType.PDF, Lesson.LessonType.LINK}:
                article_reading_required_seconds = 30 if lesson.content else 0
                article_reading_remaining_seconds = max(0, article_reading_required_seconds - progress.time_spent_seconds)
                article_can_complete = article_reading_remaining_seconds <= 0
            if progress.suspicious_event_count >= 2:
                attention_warning = "Attention warning: tab switching, leaving the lesson window, or reading too fast is being tracked for this lesson."

        primary_video_lesson = lesson if lesson.lesson_type == Lesson.LessonType.VIDEO else module.lessons.filter(
            lesson_type=Lesson.LessonType.VIDEO
        ).order_by("order", "created_at").first()

        video_coverage_percent = 0
        if progress and progress.video_duration_seconds:
            video_coverage_percent = round(progress.coverage_ratio() * 100)

        context.update(
            {
                "course": course,
                "module": module,
                "enrollment": enrollment,
                "progress": progress,
                "previous_lesson": previous_lesson,
                "next_lesson": next_lesson,
                "next_quiz": next_quiz if lesson_index == len(ordered_lessons) - 1 else None,
                "next_label": "Module Quiz" if lesson_index == len(ordered_lessons) - 1 and next_quiz else "Next Lesson",
                "can_advance": can_advance,
                "primary_video_lesson": primary_video_lesson,
                "video_coverage_percent": video_coverage_percent,
                "article_reading_required_seconds": article_reading_required_seconds,
                "article_reading_remaining_seconds": article_reading_remaining_seconds,
                "article_can_complete": article_can_complete,
                "attention_warning": attention_warning,
            }
        )
        return context


class LessonPlaybackEventView(LoginRequiredMixin, CompanyScopedMixin, View):
    def post(self, request, lesson_id):
        lesson = get_object_or_404(
            self.company_queryset(Lesson.objects.select_related("module", "module__course"), lookup="module__course__company"),
            id=lesson_id,
        )
        enrollment, _created = Enrollment.objects.get_or_create(
            learner=request.user,
            course=lesson.module.course,
            defaults={"status": Enrollment.Status.IN_PROGRESS},
        )
        progress, _created = LessonProgress.objects.get_or_create(
            learner=request.user,
            enrollment=enrollment,
            lesson=lesson,
        )
        payload = json.loads(request.body.decode("utf-8") or "{}")
        result = record_video_playback(
            progress,
            event=payload.get("event", ""),
            position=payload.get("position", 0),
            duration=payload.get("duration", 0),
        )
        create_learning_audit_event(
            event_type="lesson_playback_event",
            actor=request.user,
            learner=request.user,
            course=lesson.module.course,
            module=lesson.module,
            lesson=lesson,
            entity_type="lesson",
            entity_id=str(lesson.id),
            metadata={"event": payload.get("event", ""), "position": payload.get("position", 0)},
        )
        return JsonResponse(result)


class LessonAttentionEventView(LoginRequiredMixin, CompanyScopedMixin, View):
    def post(self, request, lesson_id):
        lesson = get_object_or_404(
            self.company_queryset(Lesson.objects.select_related("module", "module__course"), lookup="module__course__company"),
            id=lesson_id,
        )
        enrollment, _created = Enrollment.objects.get_or_create(
            learner=request.user,
            course=lesson.module.course,
            defaults={"status": Enrollment.Status.IN_PROGRESS},
        )
        progress, _created = LessonProgress.objects.get_or_create(
            learner=request.user,
            enrollment=enrollment,
            lesson=lesson,
        )
        payload = json.loads(request.body.decode("utf-8") or "{}")
        result = record_lesson_attention(progress, event=payload.get("event", ""), payload=payload)
        create_learning_audit_event(
            event_type="lesson_attention_event",
            actor=request.user,
            learner=request.user,
            course=lesson.module.course,
            module=lesson.module,
            lesson=lesson,
            entity_type="lesson",
            entity_id=str(lesson.id),
            metadata={"event": payload.get("event", ""), "risk_level": result.get("risk_level", "low")},
        )
        return JsonResponse(result)
