"""Shared analytics calculations.

Views call this file to keep counting/aggregation logic out of templates.
"""
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.assessments.models import QuizAttempt
from apps.courses.models import Course, Enrollment, LessonProgress


def build_dashboard_metrics(user):
    # Start broad, then scope down by company/department.
    enrollments = Enrollment.objects.all()
    lesson_progress = LessonProgress.objects.all()
    attempts = QuizAttempt.objects.all()

    if getattr(user, "role", None) == user.Role.LEARNER:
        enrollments = enrollments.filter(learner=user)
        lesson_progress = lesson_progress.filter(learner=user)
        attempts = attempts.filter(learner=user)
    elif getattr(user, "company_id", None):
        enrollments = enrollments.filter(course__company=user.company)
        lesson_progress = lesson_progress.filter(learner__company=user.company)
        attempts = attempts.filter(quiz__company=user.company)

    if getattr(user, "department_id", None) and user.role == user.Role.HR_MANAGER:
        enrollments = enrollments.filter(learner__department=user.department)
        lesson_progress = lesson_progress.filter(learner__department=user.department)
        attempts = attempts.filter(learner__department=user.department)

    pass_counts = attempts.aggregate(
        passed=Count("id", filter=Q(is_passed=True)),
        total=Count("id"),
    )

    return {
        "total_enrollments": enrollments.count(),
        "completed_enrollments": enrollments.filter(status=Enrollment.Status.COMPLETED).count(),
        "in_progress_enrollments": enrollments.filter(status=Enrollment.Status.IN_PROGRESS).count(),
        "overdue_enrollments": enrollments.filter(status=Enrollment.Status.OVERDUE).count(),
        "average_completion": enrollments.aggregate(value=Avg("completion_percentage"))["value"] or 0,
        "average_watch_time": lesson_progress.aggregate(value=Avg("time_spent_seconds"))["value"] or 0,
        "average_quiz_score": attempts.aggregate(value=Avg("percentage"))["value"] or 0,
        "not_evaluated": attempts.filter(status=QuizAttempt.Status.PENDING_EVALUATION).count(),
        "not_started": enrollments.filter(status=Enrollment.Status.ASSIGNED).count(),
        "active_learners": enrollments.aggregate(count=Count("learner", distinct=True))["count"] or 0,
        "pass_rate": 0 if not pass_counts["total"] else (pass_counts["passed"] / pass_counts["total"]) * 100,
        "attention_flags": lesson_progress.filter(suspicious_event_count__gt=0).count(),
        "attention_event_total": lesson_progress.aggregate(value=Sum("suspicious_event_count"))["value"] or 0,
        "tab_switch_events": lesson_progress.aggregate(value=Avg("tab_switch_count"))["value"] or 0,
    }


def filter_queryset_by_window(queryset, field_name: str, window_days: int | None):
    if not window_days:
        return queryset
    cutoff = timezone.now() - timedelta(days=window_days)
    return queryset.filter(**{f"{field_name}__gte": cutoff})


def build_department_course_analytics(*, departments, courses, enrollments, attempts, selected_course=None, window_days=7):
    weekly_enrollments = filter_queryset_by_window(enrollments, "updated_at", window_days)
    weekly_attempts = filter_queryset_by_window(attempts, "created_at", window_days)

    department_rows = []
    for department in departments:
        department_enrollments = enrollments.filter(learner__department=department)
        department_attempts = attempts.filter(learner__department=department)
        department_weekly_enrollments = weekly_enrollments.filter(learner__department=department)
        department_weekly_attempts = weekly_attempts.filter(learner__department=department)

        department_courses = courses.filter(Q(department=department) | Q(department__isnull=True)).distinct()
        if selected_course:
            department_courses = department_courses.filter(id=selected_course.id)

        course_rows = []
        for course in department_courses:
            course_enrollments = department_enrollments.filter(course=course)
            course_attempts = department_attempts.filter(Q(quiz__course=course) | Q(quiz__module__course=course)).distinct()
            course_weekly_enrollments = department_weekly_enrollments.filter(course=course)
            course_weekly_attempts = department_weekly_attempts.filter(Q(quiz__course=course) | Q(quiz__module__course=course)).distinct()

            if not selected_course and not course_enrollments.exists() and not course_attempts.exists():
                continue

            course_rows.append(
                {
                    "course": course,
                    "learners": course_enrollments.aggregate(count=Count("learner", distinct=True))["count"] or 0,
                    "completed": course_enrollments.filter(status=Enrollment.Status.COMPLETED).count(),
                    "in_progress": course_enrollments.filter(status=Enrollment.Status.IN_PROGRESS).count(),
                    "not_started": course_enrollments.filter(status=Enrollment.Status.ASSIGNED).count(),
                    "average_completion": course_enrollments.aggregate(value=Avg("completion_percentage"))["value"] or 0,
                    "average_score": course_attempts.aggregate(value=Avg("percentage"))["value"] or 0,
                    "weekly_average_completion": course_weekly_enrollments.aggregate(value=Avg("completion_percentage"))["value"] or 0,
                    "weekly_average_score": course_weekly_attempts.aggregate(value=Avg("percentage"))["value"] or 0,
                }
            )

        if not selected_course and not department_enrollments.exists() and not department_attempts.exists():
            continue

        department_rows.append(
            {
                "department": department,
                "active_learners": department_enrollments.aggregate(count=Count("learner", distinct=True))["count"] or 0,
                "completed": department_enrollments.filter(status=Enrollment.Status.COMPLETED).count(),
                "in_progress": department_enrollments.filter(status=Enrollment.Status.IN_PROGRESS).count(),
                "not_started": department_enrollments.filter(status=Enrollment.Status.ASSIGNED).count(),
                "average_completion": department_enrollments.aggregate(value=Avg("completion_percentage"))["value"] or 0,
                "average_score": department_attempts.aggregate(value=Avg("percentage"))["value"] or 0,
                "weekly_average_completion": department_weekly_enrollments.aggregate(value=Avg("completion_percentage"))["value"] or 0,
                "weekly_average_score": department_weekly_attempts.aggregate(value=Avg("percentage"))["value"] or 0,
                "course_rows": sorted(course_rows, key=lambda item: (item["average_completion"], item["average_score"]), reverse=True),
            }
        )

    department_rows.sort(
        key=lambda item: (
            item["weekly_average_completion"],
            item["average_completion"],
            item["weekly_average_score"],
            item["average_score"],
        ),
        reverse=True,
    )
    best_department = department_rows[0] if department_rows else None
    return {
        "department_rows": department_rows,
        "best_department": best_department,
        "window_days": window_days,
    }
