"""Unified search service for the LMS shell search bar."""

from __future__ import annotations

import os
from dataclasses import dataclass

from django.db.models import Q
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.models import Quiz
from apps.certificates.models import Certificate
from apps.courses.models import CalendarEvent, Course, Lesson, Module
from apps.messaging.models import Conversation, Message

try:
    from elasticsearch import Elasticsearch
except Exception:  # pragma: no cover - optional dependency
    Elasticsearch = None


@dataclass
class SearchResult:
    category: str
    title: str
    subtitle: str
    url: str
    meta: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "category": self.category,
            "title": self.title,
            "subtitle": self.subtitle,
            "url": self.url,
            "meta": self.meta,
        }


def _user_queryset_for_search(user: User):
    queryset = User.objects.select_related("department", "company")
    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        return queryset
    if user.role == User.Role.LEARNER:
        return queryset.filter(id=user.id)
    if user.company_id:
        queryset = queryset.filter(company=user.company)
    if not user.is_manager_like and user.department_id:
        queryset = queryset.filter(department=user.department)
    return queryset


def _course_queryset_for_search(user: User):
    queryset = Course.objects.select_related("department", "company")
    if user.company_id:
        queryset = queryset.filter(company=user.company)
    if user.role == User.Role.LEARNER and user.department_id:
        queryset = queryset.filter(Q(department=user.department) | Q(department__isnull=True))
    return queryset


def _quiz_queryset_for_search(user: User):
    queryset = Quiz.objects.select_related("course", "module", "course__department", "module__course")
    if user.company_id:
        queryset = queryset.filter(company=user.company)
    if user.role == User.Role.LEARNER:
        queryset = queryset.filter(status=Quiz.Status.PUBLISHED)
        if user.department_id:
            queryset = queryset.filter(
                Q(course__department=user.department)
                | Q(course__department__isnull=True)
                | Q(module__course__department=user.department)
                | Q(module__course__department__isnull=True)
                | Q(course__isnull=True, module__isnull=True)
            ).distinct()
    return queryset


def _certificate_queryset_for_search(user: User):
    queryset = Certificate.objects.select_related("course", "learner", "template")
    if user.is_admin_like:
        if user.company_id:
            queryset = queryset.filter(company=user.company)
        return queryset
    return queryset.filter(learner=user)


def _calendar_queryset_for_search(user: User):
    queryset = CalendarEvent.objects.select_related("department", "course")
    if user.company_id:
        queryset = queryset.filter(company=user.company)
    if user.role == User.Role.LEARNER and user.department_id:
        queryset = queryset.filter(Q(department=user.department) | Q(department__isnull=True))
    elif user.role == User.Role.LEARNER:
        queryset = queryset.filter(department__isnull=True)
    return queryset


def _conversation_queryset_for_search(user: User):
    return (
        Conversation.objects.filter(participants__user=user)
        .select_related("company")
        .prefetch_related("participants__user")
        .distinct()
    )


def _db_search(user: User, query: str, limit: int = 4) -> list[SearchResult]:
    results: list[SearchResult] = []

    people = _user_queryset_for_search(user).filter(
        Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(username__icontains=query)
        | Q(email__icontains=query)
        | Q(employee_code__icontains=query)
    )[:limit]
    for person in people:
        results.append(
            SearchResult(
                category="People",
                title=person.get_full_name() or person.email,
                subtitle=person.department.name if person.department else person.get_role_display(),
                url=reverse("user-detail", kwargs={"user_id": person.id}),
                meta=person.email,
            )
        )

    courses = _course_queryset_for_search(user).filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )[:limit]
    for course in courses:
        results.append(
            SearchResult(
                category="Courses",
                title=course.title,
                subtitle=course.department.name if course.department else "All Departments",
                url=reverse("course-detail", kwargs={"slug": course.slug}),
                meta="Course",
            )
        )

    modules = Module.objects.select_related("course", "course__department").filter(
        course__in=_course_queryset_for_search(user),
    ).filter(Q(title__icontains=query) | Q(description__icontains=query))[:limit]
    for module in modules:
        results.append(
            SearchResult(
                category="Modules",
                title=module.title,
                subtitle=module.course.title,
                url=reverse("course-detail", kwargs={"slug": module.course.slug}),
                meta="Module",
            )
        )

    lessons = Lesson.objects.select_related("module", "module__course").filter(
        module__course__in=_course_queryset_for_search(user),
    ).filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(content__icontains=query))[:limit]
    for lesson in lessons:
        results.append(
            SearchResult(
                category="Lessons",
                title=lesson.title,
                subtitle=lesson.module.course.title,
                url=reverse("lesson-detail", kwargs={"lesson_id": lesson.id}),
                meta=lesson.get_lesson_type_display(),
            )
        )

    quizzes = _quiz_queryset_for_search(user).filter(
        Q(title__icontains=query) | Q(description__icontains=query) | Q(instructions__icontains=query)
    )[:limit]
    for quiz in quizzes:
        subtitle = getattr(quiz.course, "title", "") or getattr(getattr(quiz.module, "course", None), "title", "") or "Assessment"
        results.append(
            SearchResult(
                category="Assessments",
                title=quiz.title,
                subtitle=subtitle,
                url=reverse("quiz-detail", kwargs={"quiz_id": quiz.id}),
                meta=quiz.get_assessment_type_display(),
            )
        )

    conversations = _conversation_queryset_for_search(user).filter(title__icontains=query)[:limit]
    for conversation in conversations:
        results.append(
            SearchResult(
                category="Messages",
                title=conversation.title or "Conversation",
                subtitle="Conversation title match",
                url=reverse("conversation-detail", kwargs={"conversation_id": conversation.id}),
                meta="Thread",
            )
        )

    message_hits = (
        Message.objects.select_related("conversation", "sender")
        .filter(conversation__in=_conversation_queryset_for_search(user))
        .filter(body__icontains=query)
        .order_by("-created_at")[:limit]
    )
    for message in message_hits:
        results.append(
            SearchResult(
                category="Messages",
                title=message.sender.get_full_name() or message.sender.email,
                subtitle=message.body[:90],
                url=reverse("conversation-detail", kwargs={"conversation_id": message.conversation_id}),
                meta="Message",
            )
        )

    certificates = _certificate_queryset_for_search(user).filter(
        Q(certificate_number__icontains=query)
        | Q(course__title__icontains=query)
        | Q(learner__first_name__icontains=query)
        | Q(learner__last_name__icontains=query)
    )[:limit]
    for certificate in certificates:
        results.append(
            SearchResult(
                category="Certificates",
                title=certificate.certificate_number,
                subtitle=certificate.course.title,
                url=reverse("certificate-list"),
                meta=certificate.learner.get_full_name() or certificate.learner.email,
            )
        )

    tasks = _calendar_queryset_for_search(user).filter(
        Q(title__icontains=query)
        | Q(course__title__icontains=query)
        | Q(department__name__icontains=query)
    )[:limit]
    for task in tasks:
        task_url = reverse("calendar-event-edit", kwargs={"event_id": task.id}) if user.is_manager_like or user.is_admin_like else reverse("calendar-board")
        results.append(
            SearchResult(
                category="Calendar",
                title=task.title,
                subtitle=task.department.name if task.department else "All Departments",
                url=task_url,
                meta=task.get_event_type_display(),
            )
        )

    return results[:24]


def _try_elasticsearch(user: User, query: str) -> list[SearchResult] | None:
    elastic_url = os.getenv("ELASTICSEARCH_URL", "").strip()
    if not elastic_url or Elasticsearch is None:
        return None

    try:
        client = Elasticsearch(elastic_url)
        response = client.search(
            index=os.getenv("ELASTICSEARCH_INDEX", "lms-global-search"),
            query={
                "multi_match": {
                    "query": query,
                    "fields": ["title^4", "subtitle^2", "body", "meta"],
                    "fuzziness": "AUTO",
                }
            },
            size=12,
        )
    except Exception:
        return None

    items = []
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        if source.get("company_id") and str(source.get("company_id")) != str(user.company_id):
            continue
        items.append(
            SearchResult(
                category=source.get("category", "Search"),
                title=source.get("title", ""),
                subtitle=source.get("subtitle", ""),
                url=source.get("url", "#"),
                meta=source.get("meta", "Elasticsearch"),
            )
        )
    return items


def unified_search(user: User, query: str) -> tuple[list[dict[str, str]], str]:
    cleaned_query = (query or "").strip()
    if len(cleaned_query) < 2:
        return [], "none"

    elastic_results = _try_elasticsearch(user, cleaned_query)
    if elastic_results is not None:
        return [item.to_dict() for item in elastic_results], "elasticsearch"

    return [item.to_dict() for item in _db_search(user, cleaned_query)], "database"
