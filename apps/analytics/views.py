"""Dashboard and analytics views.

This file prepares the numbers shown in the dashboard templates.
Templates stay mostly presentational; the filtering and aggregation happens here.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone
from django.views.generic import TemplateView

from apps.assessments.models import QuizAssignment, QuizAttempt
from apps.courses.models import CalendarEvent, Course, Enrollment, LessonProgress
from apps.organizations.models import Department

from .services import build_dashboard_metrics, build_department_course_analytics, filter_queryset_by_window


def get_next_learning_item(user):
    pending_enrollment = (
        Enrollment.objects.select_related("course", "course__department")
        .filter(learner=user)
        .exclude(status=Enrollment.Status.COMPLETED)
        .order_by("due_date", "created_at")
        .first()
    )
    if pending_enrollment:
        return pending_enrollment

    available_courses = Course.objects.select_related("department").filter(
        company=user.company,
        status=Course.Status.PUBLISHED,
    )
    if user.department_id:
        available_courses = available_courses.filter(models.Q(department=user.department) | models.Q(department__isnull=True))
    completed_ids = Enrollment.objects.filter(learner=user).values_list("course_id", flat=True)
    return available_courses.exclude(id__in=completed_ids).order_by("title").first()


class HomeDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Shared top-line counts are built by a service so they can be reused elsewhere.
        context["metrics"] = build_dashboard_metrics(user)
        context["now"] = timezone.now()
        if user.role == user.Role.LEARNER:
            context["completed_courses"] = Enrollment.objects.filter(learner=user, status=Enrollment.Status.COMPLETED).select_related("course")
            context["pending_courses"] = Enrollment.objects.filter(learner=user).exclude(status=Enrollment.Status.COMPLETED).select_related("course")
            context["next_learning_item"] = get_next_learning_item(user)
            context["upcoming_tasks"] = CalendarEvent.objects.filter(company=user.company).filter(
                department__isnull=True if not user.department_id else False
            )[:5] if user.company_id else []
            if user.department_id:
                context["upcoming_tasks"] = CalendarEvent.objects.filter(company=user.company).filter(
                    department=user.department
                ).order_by("start_at")[:5]
            context["pending_evaluations"] = QuizAttempt.objects.filter(learner=user, status=QuizAttempt.Status.PENDING_EVALUATION)
            context["latest_quiz_attempts"] = QuizAttempt.objects.filter(learner=user).select_related("quiz").order_by("-created_at")[:5]
            learner_quiz_metrics = QuizAttempt.objects.filter(learner=user).aggregate(
                average_score=Avg("percentage"),
                passed=Count("id", filter=models.Q(is_passed=True)),
                total=Count("id"),
            )
            context["learner_average_score"] = learner_quiz_metrics["average_score"] or 0
            context["learner_passed_quizzes"] = learner_quiz_metrics["passed"] or 0
            context["learner_total_quizzes"] = learner_quiz_metrics["total"] or 0
            attention_rows = LessonProgress.objects.filter(learner=user).select_related("lesson", "lesson__module").order_by("-updated_at")[:8]
            context["attention_progress_rows"] = attention_rows
            latest_speed_row = (
                LessonProgress.objects.filter(learner=user, reading_speed_wpm__gt=0)
                .select_related("lesson", "lesson__module")
                .order_by("-updated_at")
                .first()
            )
            reading_speed_value = float(getattr(latest_speed_row, "reading_speed_wpm", 0) or 0)
            context["learner_latest_speed"] = reading_speed_value
            context["learner_latest_speed_lesson"] = latest_speed_row
            context["learner_speed_gauge_value"] = min(100, max(0, round((reading_speed_value / 200) * 100))) if reading_speed_value else 0
            context["learner_attention_event_total"] = context["metrics"]["attention_event_total"]
        else:
            selected_department = self.request.GET.get("department", "").strip()
            selected_course = self.request.GET.get("course", "").strip()
            selected_window = self.request.GET.get("window", "7").strip() or "7"
            try:
                window_days = None if selected_window == "all" else int(selected_window)
            except ValueError:
                selected_window = "7"
                window_days = 7
            scoped_enrollments = Enrollment.objects.select_related("learner", "course")
            progress_queryset = LessonProgress.objects.select_related("learner", "lesson", "lesson__module", "lesson__module__course")
            if user.company_id:
                scoped_enrollments = scoped_enrollments.filter(course__company=user.company)
                progress_queryset = progress_queryset.filter(learner__company=user.company)
            if user.role == user.Role.HR_MANAGER and user.department_id:
                scoped_enrollments = scoped_enrollments.filter(learner__department=user.department)
                progress_queryset = progress_queryset.filter(learner__department=user.department)
            context["incomplete_enrollments"] = scoped_enrollments.exclude(status=Enrollment.Status.COMPLETED)[:10]
            events = CalendarEvent.objects.select_related("department", "course")
            if user.company_id:
                events = events.filter(company=user.company)
            if user.role == user.Role.HR_MANAGER and user.department_id:
                events = events.filter(department=user.department)
            context["upcoming_tasks"] = events.order_by("start_at")[:8]
            assignment_queryset = QuizAssignment.objects.select_related("quiz", "department", "learner", "assigned_by")
            attempts_queryset = QuizAttempt.objects.select_related("quiz", "learner", "learner__department")
            departments = Department.objects.select_related("company")
            courses = Course.objects.select_related("department")
            if user.company_id:
                assignment_queryset = assignment_queryset.filter(quiz__company=user.company)
                attempts_queryset = attempts_queryset.filter(quiz__company=user.company)
                departments = departments.filter(company=user.company)
                courses = courses.filter(company=user.company, status=Course.Status.PUBLISHED)
            if user.role == user.Role.HR_MANAGER and user.department_id:
                assignment_queryset = assignment_queryset.filter(models.Q(department=user.department) | models.Q(learner__department=user.department))
                attempts_queryset = attempts_queryset.filter(learner__department=user.department)
                departments = departments.filter(id=user.department_id)
                courses = courses.filter(models.Q(department=user.department) | models.Q(department__isnull=True)).distinct()

            if selected_department:
                scoped_enrollments = scoped_enrollments.filter(learner__department_id=selected_department)
                progress_queryset = progress_queryset.filter(learner__department_id=selected_department)
                assignment_queryset = assignment_queryset.filter(
                    models.Q(department_id=selected_department) | models.Q(learner__department_id=selected_department)
                )
                attempts_queryset = attempts_queryset.filter(learner__department_id=selected_department)
                courses = courses.filter(models.Q(department_id=selected_department) | models.Q(department__isnull=True)).distinct()
                departments = departments.filter(id=selected_department)

            selected_course_object = None
            if selected_course:
                scoped_enrollments = scoped_enrollments.filter(course_id=selected_course)
                progress_queryset = progress_queryset.filter(lesson__module__course_id=selected_course)
                assignment_queryset = assignment_queryset.filter(
                    models.Q(quiz__course_id=selected_course) | models.Q(quiz__module__course_id=selected_course)
                )
                attempts_queryset = attempts_queryset.filter(
                    models.Q(quiz__course_id=selected_course) | models.Q(quiz__module__course_id=selected_course)
                )
                courses = courses.filter(id=selected_course)
                selected_course_object = courses.first()

            time_filtered_enrollments = filter_queryset_by_window(scoped_enrollments, "updated_at", window_days)
            time_filtered_attempts = filter_queryset_by_window(attempts_queryset, "created_at", window_days)
            time_filtered_assignments = filter_queryset_by_window(assignment_queryset, "created_at", window_days)
            time_filtered_progress = filter_queryset_by_window(progress_queryset, "updated_at", window_days)

            context["recent_quiz_assignments"] = time_filtered_assignments.order_by("-created_at")[:8]
            context["recent_quiz_attempts"] = time_filtered_attempts.order_by("-created_at")[:8]
            context["quiz_assignment_count"] = time_filtered_assignments.count()
            context["quiz_attempt_count"] = time_filtered_attempts.count()
            context["quiz_average_score"] = time_filtered_attempts.aggregate(value=Avg("percentage"))["value"] or 0
            context["attention_rows"] = time_filtered_progress.filter(
                models.Q(suspicious_event_count__gt=0) | models.Q(reading_speed_flag="fast")
            ).order_by("-updated_at")[:12]
            context["weekly_completion_average"] = time_filtered_enrollments.aggregate(value=Avg("completion_percentage"))["value"] or 0
            context["weekly_quiz_average"] = time_filtered_attempts.aggregate(value=Avg("percentage"))["value"] or 0
            context["available_departments"] = list(departments.order_by("name"))
            context["available_courses"] = list(courses.order_by("title"))
            context["selected_department"] = selected_department
            context["selected_course"] = selected_course
            context["selected_window"] = selected_window
            context["window_options"] = [
                ("7", "Last 7 days"),
                ("30", "Last 30 days"),
                ("all", "All time"),
            ]
            analytics = build_department_course_analytics(
                departments=departments.order_by("name"),
                courses=courses.order_by("title"),
                enrollments=time_filtered_enrollments,
                attempts=time_filtered_attempts,
                selected_course=selected_course_object,
                window_days=window_days or 7,
            )
            context["department_quiz_rows"] = [
                {
                    "department": row["department"],
                    "assigned": time_filtered_assignments.filter(
                        models.Q(department=row["department"]) | models.Q(learner__department=row["department"])
                    ).count(),
                    "attempted": time_filtered_attempts.filter(learner__department=row["department"]).count(),
                    "average": row["average_score"],
                }
                for row in analytics["department_rows"]
            ]
            context["department_course_rows"] = analytics["department_rows"]
            context["best_department"] = analytics["best_department"]
        return context


class AdminAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metrics"] = build_dashboard_metrics(self.request.user)
        return context
