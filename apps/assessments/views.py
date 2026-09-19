from __future__ import annotations
"""Assessment page views.

Flow:
- QuizListView decides what quizzes the current user is allowed to see
- QuizDetailView renders the quiz form and handles submission
- QuizResultView shows the graded outcome
- QuizAssignmentCreateView lets HR/admin assign quizzes
- QuizCreateView builds a quiz and its questions in one screen
"""

import json
from datetime import datetime, time as datetime_time
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.models import User
from apps.common.holidays import get_india_holiday_map
from apps.common.services import create_admin_audit_log, create_learning_audit_event, snapshot_model
from apps.courses.models import CalendarEvent, Enrollment
from apps.certificates.models import Certificate

from .forms import QuizAssignmentForm, QuizBuilderForm
from .models import Choice, Question, Quiz, QuizAnswer, QuizAssignment, QuizAttempt
from .services import finalize_manual_review, grade_attempt, record_answers, save_draft_answers, start_attempt


def _format_mark(value):
    numeric = float(value or 0)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.2f}".rstrip("0").rstrip(".")


def _badge_tier(percentage):
    score = float(percentage or 0)
    if score >= 90:
        return {"key": "gold", "label": "Gold Badge"}
    if score >= 75:
        return {"key": "silver", "label": "Silver Badge"}
    return {"key": "bronze", "label": "Bronze Badge"}


def _build_question_sections(quiz: Quiz):
    sections = []
    current_section = None
    ordered_questions = list(quiz.questions.all().order_by("order", "created_at"))

    for global_index, question in enumerate(ordered_questions, start=1):
        raw_title = (question.section_title or "").strip()
        next_label = f"Section {len(sections) + 1}"
        section_title = raw_title or next_label
        if current_section is None or current_section["title"] != section_title:
            current_section = {
                "title": section_title,
                "index": len(sections),
                "label": next_label,
                "questions": [],
            }
            sections.append(current_section)
        current_section["questions"].append(
            {
                "question": question,
                "global_number": global_index,
                "section_question_number": len(current_section["questions"]) + 1,
            }
        )

    for section in sections:
        section["question_count"] = len(section["questions"])
    return sections


def _quiz_attempt_capacity(quiz: Quiz, completed_count: int) -> int:
    if quiz.allow_multiple_attempts:
        return max(max(quiz.max_attempts, 1) - completed_count, 0)
    return 0 if completed_count else 1


def sync_quiz_calendar_event(*, quiz: Quiz, department, due_date):
    if not (quiz.company_id and department and due_date):
        return None
    start_at = timezone.make_aware(datetime.combine(due_date, datetime_time(hour=9, minute=0)))
    defaults = {
        "company": quiz.company,
        "course": quiz.course or getattr(quiz.module, "course", None),
        "title": quiz.title,
        "event_type": CalendarEvent.EventType.QUIZ,
        "start_at": start_at,
        "color": getattr(department, "color", "#7c3aed"),
    }
    calendar_event, _created = CalendarEvent.objects.update_or_create(
        company=quiz.company,
        department=department,
        title=quiz.title,
        event_type=CalendarEvent.EventType.QUIZ,
        defaults=defaults,
    )
    return calendar_event


def _resolve_quiz_company(*, user, department=None, course=None, module=None, assign_department=None, existing_quiz=None):
    if existing_quiz and existing_quiz.company_id:
        return existing_quiz.company
    if module and getattr(module, "course", None) and module.course.company_id:
        return module.course.company
    if course and course.company_id:
        return course.company
    if department and department.company_id:
        return department.company
    if assign_department and assign_department.company_id:
        return assign_department.company
    return getattr(user, "company", None)


def quiz_queryset_for_user(user):
    queryset = Quiz.objects.select_related("category", "course", "module", "module__course").prefetch_related("questions__choices")
    if user.is_admin_like or user.is_manager_like:
        return queryset
    queryset = queryset.filter(status=Quiz.Status.PUBLISHED)
    learner_filter = Q(assignments__learner=user)
    if user.department_id:
        learner_filter |= Q(assignments__department=user.department)
        learner_filter |= Q(course__department=user.department)
        learner_filter |= Q(module__course__department=user.department)
    return queryset.filter(learner_filter).distinct()


class QuizListView(LoginRequiredMixin, ListView):
    template_name = "assessments/quiz_list.html"
    context_object_name = "quizzes"

    @staticmethod
    def _department_match_filter(department_id):
        return (
            Q(course__department_id=department_id)
            | Q(module__course__department_id=department_id)
            | (
                Q(course__isnull=True, module__isnull=True)
                & Q(assignments__department_id=department_id)
            )
        )

    def get_queryset(self):
        user = self.request.user
        selected_department = self.request.GET.get("department", "").strip()
        queryset = Quiz.objects.select_related("category", "course", "module", "module__course").annotate(
            assignment_total=Count("assignments", distinct=True),
            attempt_total=Count("attempts", distinct=True),
            attendee_total=Count(
                "attempts__learner",
                filter=~Q(attempts__status=QuizAttempt.Status.IN_PROGRESS),
                distinct=True,
            ),
            pass_total=Count(
                "attempts",
                filter=Q(attempts__is_passed=True),
                distinct=True,
            ),
            pending_review_total=Count(
                "attempts",
                filter=Q(attempts__status=QuizAttempt.Status.PENDING_EVALUATION),
                distinct=True,
            ),
        )
        if selected_department:
            queryset = queryset.filter(self._department_match_filter(selected_department)).distinct()
        if user.is_admin_like or user.is_manager_like:
            return queryset
        queryset = queryset.filter(status=Quiz.Status.PUBLISHED)

        learner_filter = Q(assignments__learner=user)
        if user.department_id:
            learner_filter |= Q(assignments__department=user.department)
            learner_filter |= Q(course__department=user.department)
            learner_filter |= Q(module__course__department=user.department)
        return queryset.filter(learner_filter).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_assign_quiz"] = self.request.user.is_manager_like or self.request.user.is_admin_like
        context["can_create_quiz"] = self.request.user.is_manager_like or self.request.user.is_admin_like
        context["show_assessment_filters"] = context["can_assign_quiz"]
        quizzes = list(context["quizzes"])
        context["quizzes"] = quizzes
        departments = []
        if context["show_assessment_filters"]:
            department_seen = set()
            for quiz in quizzes:
                quiz_department = getattr(quiz.course, "department", None) or getattr(getattr(quiz.module, "course", None), "department", None)
                if quiz_department and quiz_department.id not in department_seen:
                    department_seen.add(quiz_department.id)
                    departments.append(quiz_department)
            departments.sort(key=lambda department: department.name.lower())
        context["departments"] = departments
        context["selected_department"] = self.request.GET.get("department", "").strip()
        total_assignments = sum(getattr(quiz, "assignment_total", 0) for quiz in quizzes)
        total_attendees = sum(getattr(quiz, "attendee_total", 0) for quiz in quizzes)
        total_attempts = sum(getattr(quiz, "attempt_total", 0) for quiz in quizzes)
        total_passed = sum(getattr(quiz, "pass_total", 0) for quiz in quizzes)
        total_pending_review = sum(getattr(quiz, "pending_review_total", 0) for quiz in quizzes)
        attendance_rate = round((total_attendees / total_assignments) * 100, 1) if total_assignments else 0
        context["assessment_overview"] = {
            "total_quizzes": len(quizzes),
            "total_assignments": total_assignments,
            "total_attendees": total_attendees,
            "total_attempts": total_attempts,
            "total_passed": total_passed,
            "total_pending_review": total_pending_review,
            "attendance_rate": attendance_rate,
        }
        context["assessment_rows"] = []
        for quiz in quizzes:
            section_titles = []
            seen_titles = set()
            for question in quiz.questions.all().order_by("order", "created_at"):
                title = (question.section_title or "").strip() or f"Section {len(section_titles) + 1}"
                if title not in seen_titles:
                    seen_titles.add(title)
                    section_titles.append(title)
            context["assessment_rows"].append(
                {
                    "quiz": quiz,
                    "department": getattr(quiz.course, "department", None) or getattr(getattr(quiz.module, "course", None), "department", None),
                    "course": quiz.course or getattr(quiz.module, "course", None),
                    "module": quiz.module,
                    "section_summary": ", ".join(section_titles[:3]) if section_titles else "Section 1",
                    "section_count": len(section_titles) or 1,
                }
            )
        if not context["can_assign_quiz"]:
            attempts = list(
                QuizAttempt.objects.filter(quiz__in=quizzes, learner=self.request.user)
                .select_related("quiz")
                .order_by("quiz_id", "-created_at")
            )
            latest_attempt_by_quiz = {}
            completed_counts: dict = {}
            for attempt in attempts:
                latest_attempt_by_quiz.setdefault(attempt.quiz_id, attempt)
                if attempt.status != QuizAttempt.Status.IN_PROGRESS:
                    completed_counts[attempt.quiz_id] = completed_counts.get(attempt.quiz_id, 0) + 1

            context["learner_quiz_rows"] = []
            for quiz in quizzes:
                latest_attempt = latest_attempt_by_quiz.get(quiz.id)
                completed_count = completed_counts.get(quiz.id, 0)
                remaining_attempts = _quiz_attempt_capacity(quiz, completed_count)
                has_in_progress = bool(latest_attempt and latest_attempt.status == QuizAttempt.Status.IN_PROGRESS)
                latest_result_url = (
                    reverse("quiz-result", kwargs={"attempt_id": latest_attempt.id})
                    if latest_attempt and latest_attempt.status != QuizAttempt.Status.IN_PROGRESS
                    else ""
                )
                action_url = reverse("quiz-detail", kwargs={"quiz_id": quiz.id})
                action_label = "Open Quiz"
                status_label = "Ready"
                status_tone = "ready"
                helper_text = "Review the instructions first, then begin when you are ready."

                if has_in_progress:
                    action_label = "Resume Attempt"
                    status_label = "In Progress"
                    status_tone = "progress"
                    helper_text = "Your earlier answers are already saved. Continue from where you stopped."
                elif remaining_attempts > 0 and completed_count > 0:
                    action_label = "Retry Quiz"
                    status_label = "Retry Available"
                    status_tone = "retry"
                    helper_text = "You still have another allowed attempt for this assessment."
                elif remaining_attempts == 0 and latest_result_url:
                    action_label = "View Result"
                    action_url = latest_result_url
                    status_label = "Attempts Used"
                    status_tone = "locked"
                    helper_text = "The allowed attempts are finished. Review your latest result here."

                context["learner_quiz_rows"].append(
                    {
                        "quiz": quiz,
                        "department": getattr(quiz.course, "department", None) or getattr(getattr(quiz.module, "course", None), "department", None),
                        "course": quiz.course or getattr(quiz.module, "course", None),
                        "module": quiz.module,
                        "latest_attempt": latest_attempt,
                        "completed_count": completed_count,
                        "remaining_attempts": remaining_attempts,
                        "action_label": action_label,
                        "action_url": action_url,
                        "status_label": status_label,
                        "status_tone": status_tone,
                        "helper_text": helper_text,
                        "latest_result_url": latest_result_url,
                    }
                )
        if context["can_assign_quiz"]:
            assignments = QuizAssignment.objects.select_related("quiz", "department", "learner", "assigned_by")
            if context["selected_department"]:
                assignments = assignments.filter(
                    Q(department_id=context["selected_department"])
                    | Q(learner__department_id=context["selected_department"])
                    | Q(quiz__course__department_id=context["selected_department"])
                    | Q(quiz__module__course__department_id=context["selected_department"])
                ).exclude(
                    Q(quiz__course__isnull=False)
                    & ~Q(quiz__course__department_id=context["selected_department"])
                ).exclude(
                    Q(quiz__module__isnull=False)
                    & ~Q(quiz__module__course__department_id=context["selected_department"])
                )
            context["recent_assignments"] = assignments.order_by("-created_at")[:8]
            context["assignment_rows"] = assignments.select_related(
                "quiz__course__department",
                "quiz__module__course__department",
            ).order_by("-created_at")[:16]
        return context


class QuizDetailView(LoginRequiredMixin, DetailView):
    template_name = "assessments/quiz_detail.html"
    model = Quiz
    context_object_name = "quiz"
    pk_url_kwarg = "quiz_id"

    def get_queryset(self):
        return quiz_queryset_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = context["quiz"]
        attempts = QuizAttempt.objects.filter(quiz=quiz, learner=self.request.user).order_by("-created_at")
        completed_attempts = attempts.exclude(status=QuizAttempt.Status.IN_PROGRESS)
        context["attempt_count"] = completed_attempts.count()
        context["max_attempts"] = max(quiz.max_attempts, 1)
        context["can_start_attempt"] = False
        context["latest_attempt"] = attempts.first()
        context["active_attempt"] = attempts.filter(status=QuizAttempt.Status.IN_PROGRESS).first()
        context["quiz_started"] = self.request.GET.get("started") == "1" or bool(
            context["latest_attempt"] and context["latest_attempt"].status == QuizAttempt.Status.IN_PROGRESS
        )
        if self.request.user.role == User.Role.LEARNER:
            create_learning_audit_event(
                event_type="quiz_opened",
                actor=self.request.user,
                learner=self.request.user,
                course=quiz.course or getattr(quiz.module, "course", None),
                module=quiz.module,
                quiz=quiz,
                department=self.request.user.department,
                entity_type="quiz",
                entity_id=str(quiz.id),
                metadata={
                    "quiz_title": quiz.title,
                    "attempt_count": completed_attempts.count(),
                },
            )
            if quiz.allow_multiple_attempts:
                context["can_start_attempt"] = completed_attempts.count() < max(quiz.max_attempts, 1) or attempts.filter(
                    status=QuizAttempt.Status.IN_PROGRESS
                ).exists()
            else:
                context["can_start_attempt"] = completed_attempts.count() == 0 or attempts.filter(
                    status=QuizAttempt.Status.IN_PROGRESS
                ).exists()
        context["can_view_live_insights"] = self.request.user.is_admin_like or self.request.user.is_manager_like
        remaining_attempts = _quiz_attempt_capacity(quiz, completed_attempts.count())
        context["remaining_attempts"] = remaining_attempts
        if not context["can_view_live_insights"]:
            if context["active_attempt"]:
                context["detail_state"] = {
                    "badge": "Attempt Status",
                    "title": "Resume Attempt",
                    "tone": "progress",
                    "body": "Your quiz is in progress. Continue from where you stopped.",
                }
            elif context["can_start_attempt"] and completed_attempts.exists():
                context["detail_state"] = {
                    "badge": "Attempt Status",
                    "title": "Retry Available",
                    "tone": "retry",
                    "body": f"You have {remaining_attempts} attempt{'s' if remaining_attempts != 1 else ''} remaining for this quiz. Open the instructions and start the next attempt when ready.",
                }
            elif context["can_start_attempt"]:
                context["detail_state"] = {
                    "badge": "Attempt Status",
                    "title": "Ready To Start",
                    "tone": "ready",
                    "body": "Read the instructions, then start the quiz. The timer begins only after you launch the attempt.",
                }
            else:
                context["detail_state"] = {
                    "badge": "Attempt Status",
                    "title": "Attempt Limit Reached",
                    "tone": "locked",
                    "body": "You already used the allowed attempts for this quiz. You can still review the latest result if one is available.",
                }
            context["show_attempt_limit_warning"] = not context["can_start_attempt"] and not context["active_attempt"]
            context["quiz_instruction_points"] = [
                "The exam timer starts only after you press Start Quiz.",
                "Answers autosave while you type or choose an option.",
                "Finish the current section to unlock the next one.",
                "After you move to a later section, earlier sections stay locked.",
                "If the timer ends, the quiz is submitted automatically and opens the result page.",
            ]
        context["learner_sections"] = _build_question_sections(quiz) if not context["can_view_live_insights"] else []
        if context["latest_attempt"] and context["latest_attempt"].status == QuizAttempt.Status.IN_PROGRESS:
            draft_answers = {}
            for answer in context["latest_attempt"].answers.all():
                draft_answers[str(answer.question_id)] = {
                    "selected_choice_ids": answer.selected_choice_ids or [],
                    "answer_text": answer.answer_text or "",
                }
            context["draft_answers_json"] = json.dumps(draft_answers, cls=DjangoJSONEncoder)
        else:
            context["draft_answers_json"] = json.dumps({}, cls=DjangoJSONEncoder)

        if context["can_view_live_insights"]:
            admin_attempts = QuizAttempt.objects.filter(quiz=quiz).select_related("learner", "learner__department")
            context["recent_attempts"] = (
                admin_attempts
                .select_related("learner")
                .order_by("-created_at")[:8]
            )
            summary = admin_attempts.exclude(status=QuizAttempt.Status.IN_PROGRESS).aggregate(
                total_attempts=Count("id"),
                attendees=Count("learner_id", distinct=True),
                avg_score=Avg("percentage"),
                passed=Count("id", filter=Q(is_passed=True)),
                failed=Count("id", filter=Q(is_passed=False)),
                pending=Count("id", filter=Q(status=QuizAttempt.Status.PENDING_EVALUATION)),
            )
            context["admin_quiz_summary"] = {
                "total_attempts": summary["total_attempts"] or 0,
                "attendees": summary["attendees"] or 0,
                "avg_score": round(float(summary["avg_score"] or 0), 1),
                "passed": summary["passed"] or 0,
                "failed": summary["failed"] or 0,
                "pending": summary["pending"] or 0,
            }
            context["header_attempts"] = list(
                admin_attempts.exclude(status=QuizAttempt.Status.IN_PROGRESS).order_by("-created_at")[:12]
            )
            context["top_department_attendance"] = next(
                iter(
                    admin_attempts.exclude(status=QuizAttempt.Status.IN_PROGRESS)
                    .values("learner__department__name")
                    .annotate(total=Count("learner_id", distinct=True))
                    .order_by("-total", "learner__department__name")
                ),
                None,
            )
            context["attendance_by_department"] = (
                admin_attempts.exclude(status=QuizAttempt.Status.IN_PROGRESS)
                .values("learner__department__name")
                .annotate(total=Count("learner_id", distinct=True))
                .order_by("-total", "learner__department__name")
            )
            weak_questions = []
            for question in quiz.questions.all():
                question_answers = question.answers.filter(attempt__quiz=quiz).exclude(attempt__status=QuizAttempt.Status.IN_PROGRESS)
                total_answers = question_answers.count()
                auto_correct = question_answers.filter(
                    requires_manual_review=False,
                    awarded_marks__gte=question.marks,
                ).count()
                accuracy = round((auto_correct / total_answers) * 100, 1) if total_answers else 0
                weak_questions.append(
                    {
                        "prompt": question.prompt[:120],
                        "accuracy": accuracy,
                        "total_answers": total_answers,
                        "missed_count": max(total_answers - auto_correct, 0),
                        "section": question.section_title,
                    }
                )
            weak_questions.sort(key=lambda item: item["accuracy"])
            context["weak_questions"] = weak_questions[:5]
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        quiz = self.get_object()
        attempt = start_attempt(quiz, request.user)
        if attempt is None:
            messages.error(request, "You have reached the allowed number of attempts for this quiz.")
            return redirect("quiz-detail", quiz_id=quiz.id)

        payload: dict[int, dict] = {}
        for question in quiz.questions.all():
            key = f"question_{question.id}"
            if question.question_type == question.QuestionType.MULTIPLE_CHOICE:
                payload[question.id] = {"selected_choice_ids": [str(value) for value in request.POST.getlist(key) if value]}
            elif question.question_type in {
                question.QuestionType.SINGLE_CHOICE,
                question.QuestionType.TRUE_FALSE,
            }:
                choice_id = request.POST.get(key)
                payload[question.id] = {"selected_choice_ids": [str(choice_id)] if choice_id else []}
            else:
                payload[question.id] = {"answer_text": request.POST.get(key, "")}

        record_answers(attempt, payload)
        grade_attempt(attempt)
        answer_summary = []
        for question in quiz.questions.all():
            item = payload.get(question.id, {})
            selected_ids = item.get("selected_choice_ids", [])
            selected_choices = list(question.choices.filter(id__in=selected_ids).values_list("text", flat=True))
            answer_summary.append(
                {
                    "question": question.prompt[:160],
                    "question_type": question.question_type,
                    "selected_choices": selected_choices,
                    "answer_text": item.get("answer_text", ""),
                }
            )
        create_learning_audit_event(
            event_type="quiz_submitted",
            actor=request.user,
            learner=request.user,
            course=quiz.course or getattr(quiz.module, "course", None),
            module=quiz.module,
            quiz=quiz,
            department=request.user.department,
            entity_type="quiz_attempt",
            entity_id=str(attempt.id),
            metadata={
                "score": float(attempt.score),
                "percentage": float(attempt.percentage),
                "status": attempt.status,
                "is_passed": attempt.is_passed,
                "time_limit_minutes": quiz.time_limit_minutes,
                "answers": answer_summary,
            },
        )
        return redirect("quiz-result", attempt_id=attempt.id)


class QuizStartView(LoginRequiredMixin, DetailView):
    model = Quiz
    pk_url_kwarg = "quiz_id"

    def get_queryset(self):
        return quiz_queryset_for_user(self.request.user)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.request = request
        quiz = self.get_object()
        attempt = start_attempt(quiz, request.user)
        if attempt is None:
            messages.error(request, "You have reached the allowed number of attempts for this quiz.")
            return redirect("quiz-detail", quiz_id=quiz.id)
        return redirect(f"{redirect('quiz-detail', quiz_id=quiz.id).url}?started=1")


class QuizDraftSaveView(LoginRequiredMixin, DetailView):
    model = Quiz
    pk_url_kwarg = "quiz_id"

    def get_queryset(self):
        return quiz_queryset_for_user(self.request.user)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.request = request
        quiz = self.get_object()
        attempt = start_attempt(quiz, request.user)
        if attempt is None:
            return JsonResponse({"ok": False, "error": "Attempt limit reached."}, status=400)
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "Invalid draft payload."}, status=400)

        normalized = {}
        for question in quiz.questions.all():
            raw_item = payload.get(str(question.id), {})
            normalized[question.id] = {
                "selected_choice_ids": [str(value) for value in (raw_item.get("selected_choice_ids") or []) if value],
                "answer_text": raw_item.get("answer_text", ""),
            }
        save_draft_answers(attempt, normalized)
        return JsonResponse({"ok": True, "attempt_id": str(attempt.id)})


class QuizResultView(LoginRequiredMixin, DetailView):
    template_name = "assessments/quiz_result.html"
    model = QuizAttempt
    context_object_name = "attempt"
    pk_url_kwarg = "attempt_id"

    def get_queryset(self):
        queryset = QuizAttempt.objects.select_related(
            "quiz",
            "quiz__course",
            "quiz__module",
            "quiz__module__course",
            "learner",
        ).prefetch_related("answers__question", "answers__question__choices")
        if self.request.user.is_admin_like:
            return queryset
        return queryset.filter(learner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = context["attempt"]
        quiz = attempt.quiz
        linked_course = quiz.course or getattr(quiz.module, "course", None)
        total_marks = sum(question.marks for question in quiz.questions.all())
        context["allow_continue_on_fail"] = quiz.allow_continue_on_fail
        if quiz.module_id:
            next_target = redirect("course-detail", slug=quiz.module.course.slug).url
        elif quiz.course_id:
            next_target = redirect("course-detail", slug=quiz.course.slug).url
        else:
            next_target = redirect("quiz-list").url
        related_certificate = None
        if attempt.is_passed and linked_course:
            related_certificate = Certificate.objects.filter(
                learner=attempt.learner,
                course=linked_course,
            ).order_by("-issued_at").first()
        context["continue_target_url"] = next_target
        context["linked_course"] = linked_course
        tier = _badge_tier(attempt.percentage)
        context["quiz_badge"] = {
            "title": f"{quiz.title} Badge",
            "marks_label": f"{_format_mark(attempt.score)} / {_format_mark(total_marks or 0)}",
            "percentage_label": f"{_format_mark(attempt.percentage)}%",
            "tier_key": tier["key"],
            "tier_label": tier["label"],
        }
        context["related_certificate"] = related_certificate
        answer_review_rows = []
        for answer in attempt.answers.all().order_by("question__order", "question__created_at"):
            question = answer.question
            selected_choice_ids = {str(choice_id) for choice_id in (answer.selected_choice_ids or [])}
            selected_choices = [choice.text for choice in question.choices.all() if str(choice.id) in selected_choice_ids]
            correct_choices = [choice.text for choice in question.choices.all() if choice.is_correct]
            learner_response = ", ".join(selected_choices) if selected_choices else (answer.answer_text or "No answer")
            correct_response = ", ".join(correct_choices) if correct_choices else (question.correct_answer_text or "")
            answer_review_rows.append(
                {
                    "question_number": question.order + 1,
                    "prompt": question.prompt,
                    "question_type": question.get_question_type_display(),
                    "section_title": (question.section_title or "").strip(),
                    "learner_response": learner_response,
                    "correct_response": correct_response,
                    "explanation": question.explanation,
                    "awarded_marks": answer.awarded_marks,
                    "requires_manual_review": answer.requires_manual_review,
                }
            )
        context["answer_review_rows"] = answer_review_rows
        return context


class QuizAttemptReviewView(LoginRequiredMixin, DetailView):
    template_name = "assessments/quiz_attempt_review.html"
    model = QuizAttempt
    context_object_name = "attempt"
    pk_url_kwarg = "attempt_id"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin_like or request.user.is_manager_like):
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = QuizAttempt.objects.select_related(
            "quiz",
            "quiz__course",
            "quiz__module",
            "quiz__module__course",
            "learner",
        ).prefetch_related("answers__question", "answers__question__choices")
        if self.request.user.company_id:
            queryset = queryset.filter(quiz__company=self.request.user.company)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = context["attempt"]
        context["manual_answers"] = [answer for answer in attempt.answers.all() if answer.requires_manual_review]
        context["review_summary"] = {
            "learner_name": attempt.learner.get_full_name() or attempt.learner.username,
            "learner_email": attempt.learner.email,
            "department_name": attempt.learner.department.name if attempt.learner.department_id else "No Department",
            "submitted_at": attempt.created_at,
            "question_count": attempt.answers.count(),
            "manual_count": len(context["manual_answers"]),
            "auto_count": attempt.answers.count() - len(context["manual_answers"]),
        }
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        attempt = self.get_object()
        marks_map: dict[int, str] = {}
        try:
            for answer in attempt.answers.filter(requires_manual_review=True):
                field_name = f"answer_{answer.id}_marks"
                if field_name not in request.POST:
                    continue
                value = request.POST.get(field_name, "").strip()
                if value == "":
                    raise ValidationError("Enter marks for every descriptive answer before finalizing.")
                marks_map[answer.id] = value
            finalize_manual_review(attempt, marks_map)
        except (ArithmeticError, ValidationError):
            messages.error(request, "Could not finalize marks. Check the manual review score fields and try again.")
            return redirect("quiz-attempt-review", attempt_id=attempt.id)

        create_admin_audit_log(
            action="quiz_attempt_reviewed",
            actor=request.user,
            department=attempt.learner.department,
            entity_type="quiz_attempt",
            entity_id=str(attempt.id),
            after_json={
                "quiz_title": attempt.quiz.title,
                "learner": attempt.learner.email,
                "score": float(attempt.score),
                "percentage": float(attempt.percentage),
                "status": attempt.status,
                "is_passed": attempt.is_passed,
            },
        )
        messages.success(request, "Quiz marks finalized successfully.")
        return redirect("quiz-attempt-review", attempt_id=attempt.id)


class QuizLiveInsightsView(LoginRequiredMixin, DetailView):
    model = Quiz
    pk_url_kwarg = "quiz_id"

    def get_queryset(self):
        queryset = Quiz.objects.select_related("company")
        if self.request.user.company_id:
            queryset = queryset.filter(company=self.request.user.company)
        return queryset

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        if not (request.user.is_admin_like or request.user.is_manager_like):
            return JsonResponse({"detail": "Forbidden"}, status=403)
        quiz = get_object_or_404(self.get_queryset(), id=kwargs["quiz_id"])
        attempts = QuizAttempt.objects.filter(quiz=quiz).exclude(status=QuizAttempt.Status.IN_PROGRESS)
        summary = attempts.aggregate(
            total=Count("id"),
            avg_score=Avg("percentage"),
            pass_count=Count("id", filter=Q(is_passed=True)),
            fail_count=Count("id", filter=Q(is_passed=False)),
            pending_count=Count("id", filter=Q(status=QuizAttempt.Status.PENDING_EVALUATION)),
        )
        question_insights = []
        for question in quiz.questions.all():
            question_answers = question.answers.filter(attempt__quiz=quiz)
            total_answers = question_answers.count()
            auto_correct = question_answers.filter(
                requires_manual_review=False,
                awarded_marks__gte=question.marks,
            ).count()
            accuracy = round((auto_correct / total_answers) * 100, 1) if total_answers else 0
            question_insights.append(
                {
                    "question": question.prompt[:110],
                    "type": question.get_question_type_display(),
                    "total_answers": total_answers,
                    "accuracy": accuracy,
                }
            )
        question_insights.sort(key=lambda item: item["accuracy"])
        return JsonResponse(
            {
                "quiz_title": quiz.title,
                "summary": {
                    "total_attempts": summary["total"] or 0,
                    "avg_score": round(float(summary["avg_score"] or 0), 2),
                    "pass_count": summary["pass_count"] or 0,
                    "fail_count": summary["fail_count"] or 0,
                    "pending_count": summary["pending_count"] or 0,
                },
                "question_insights": question_insights[:8],
            }
        )


class QuizAssignmentCreateView(LoginRequiredMixin, CreateView):
    template_name = "assessments/quiz_assignment_form.html"
    form_class = QuizAssignmentForm

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin_like or request.user.is_manager_like):
            return HttpResponse(status=403)
        messages.info(request, "Quiz assignment now happens inside the Create Quiz screen.")
        return redirect("quiz-create")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        quiz_id = self.request.GET.get("quiz")
        if quiz_id:
            initial["quiz"] = quiz_id
        return initial

    def form_valid(self, form):
        learners = list(form.cleaned_data.get("learners") or [])
        quiz = form.cleaned_data["quiz"]
        department = form.cleaned_data.get("department")
        due_date = form.cleaned_data.get("due_date")
        assigned_by = self.request.user

        created_any = False
        if department:
            assignment = QuizAssignment.objects.create(
                quiz=quiz,
                department=department,
                due_date=due_date,
                assigned_by=assigned_by,
            )
            sync_quiz_calendar_event(quiz=quiz, department=department, due_date=due_date)
            created_any = True
            create_learning_audit_event(
                event_type="quiz_assigned",
                actor=assigned_by,
                company=quiz.company,
                department=department,
                course=quiz.course or getattr(quiz.module, "course", None),
                module=quiz.module,
                quiz=quiz,
                entity_type="quiz_assignment",
                entity_id=str(assignment.id),
                metadata={
                    "target_type": "department",
                    "target_label": department.name,
                    "due_date": due_date.isoformat() if due_date else "",
                },
            )
        for learner in learners:
            assignment = QuizAssignment.objects.create(
                quiz=quiz,
                learner=learner,
                due_date=due_date,
                assigned_by=assigned_by,
            )
            created_any = True
            create_learning_audit_event(
                event_type="quiz_assigned",
                actor=assigned_by,
                learner=learner,
                company=quiz.company,
                department=learner.department,
                course=quiz.course or getattr(quiz.module, "course", None),
                module=quiz.module,
                quiz=quiz,
                entity_type="quiz_assignment",
                entity_id=str(assignment.id),
                metadata={
                    "target_type": "learner",
                    "target_label": learner.get_full_name() or learner.email,
                    "due_date": due_date.isoformat() if due_date else "",
                },
            )
        if not created_any:
            return self.form_invalid(form)
        create_admin_audit_log(
            action="quiz_assigned",
            actor=assigned_by,
            department=department,
            entity_type="quiz",
            entity_id=str(quiz.id),
            after_json={
                "quiz_title": quiz.title,
                "department": department.name if department else "",
                "learner_count": len(learners),
                "due_date": due_date.isoformat() if due_date else "",
            },
        )
        messages.success(self.request, "Quiz assigned successfully.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return redirect("quiz-list").url


class QuizCreateView(LoginRequiredMixin, CreateView):
    template_name = "assessments/quiz_builder_form.html"
    form_class = QuizBuilderForm
    model = Quiz

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin_like or request.user.is_manager_like):
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        selected_department = self.request.GET.get("department", "").strip()
        selected_course = self.request.GET.get("course", "").strip()
        selected_module = self.request.GET.get("module", "").strip()
        assessment_type = self.request.GET.get("assessment_type", "").strip()
        title = self.request.GET.get("title", "").strip()
        if selected_department:
            initial["department"] = selected_department
            initial["assign_department"] = selected_department
        if selected_course:
            initial["course"] = selected_course
        if selected_module:
            initial["module"] = selected_module
        if assessment_type in {Quiz.AssessmentType.QUIZ, Quiz.AssessmentType.TEST}:
            initial["assessment_type"] = assessment_type
        if title:
            initial["title"] = title
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question_types"] = [
            (Question.QuestionType.SINGLE_CHOICE, "MCQ"),
            (Question.QuestionType.MULTIPLE_CHOICE, "MSQ"),
            (Question.QuestionType.TRUE_FALSE, "True / False"),
            (Question.QuestionType.SHORT_ANSWER, "Fill In"),
            (Question.QuestionType.ESSAY, "Descriptive"),
        ]
        form = context["form"]
        departments = list(form.fields["department"].queryset)
        courses = list(form.fields["course"].queryset.select_related("department"))
        modules = list(form.fields["module"].queryset.select_related("course", "course__department"))
        filter_map = {
            "departments": [{"id": str(department.id), "name": department.name} for department in departments],
            "courses": [
                {
                    "id": str(course.id),
                    "title": course.title,
                    "department_id": str(course.department_id) if course.department_id else "",
                }
                for course in courses
            ],
            "modules": [
                {
                    "id": str(module.id),
                    "title": module.title,
                    "course_id": str(module.course_id),
                    "department_id": str(module.course.department_id) if module.course.department_id else "",
                }
                for module in modules
            ],
        }
        context["quiz_builder_filter_json"] = filter_map
        current_year = timezone.localdate().year
        context["india_holiday_map_json"] = get_india_holiday_map([current_year - 1, current_year, current_year + 1])
        context["initial_questions_payload"] = []
        context["builder_mode"] = "create"
        return context

    def form_valid(self, form):
        selected_module = form.cleaned_data.get("module")
        selected_course = form.cleaned_data.get("course") or getattr(selected_module, "course", None)
        selected_department = form.cleaned_data.get("department")
        assign_department = form.cleaned_data.get("assign_department")
        form.instance.company = _resolve_quiz_company(
            user=self.request.user,
            department=selected_department,
            course=selected_course,
            module=selected_module,
            assign_department=assign_department,
        )
        form.instance.course = selected_course
        form.instance.module = selected_module
        linked_course = selected_course
        if selected_department and linked_course and not linked_course.department_id:
            linked_course.department = selected_department
            linked_course.save()
        response = super().form_valid(form)
        assign_due_date = form.cleaned_data.get("assign_due_date")
        questions_payload = self.request.POST.get("questions_payload", "[]")
        try:
            question_items = json.loads(questions_payload)
        except json.JSONDecodeError:
            question_items = []

        for index, item in enumerate(question_items, start=1):
            prompt = (item.get("prompt") or "").strip()
            if not prompt:
                continue
            question = Question.objects.create(
                quiz=self.object,
                prompt=prompt,
                section_title=(item.get("section_title") or "").strip(),
                question_type=item.get("question_type") or Question.QuestionType.SINGLE_CHOICE,
                marks=int(item.get("marks") or 1),
                negative_marks=item.get("negative_marks") or 0,
                suggested_seconds=int(item.get("suggested_seconds") or 0),
                explanation=item.get("explanation") or "",
                correct_answer_text=(item.get("correct_answer_text") or "").strip(),
                style_config=item.get("style_config") or {},
                order=index,
            )
            for choice_index, option in enumerate(item.get("options") or [], start=1):
                text = (option.get("text") or "").strip()
                if not text:
                    continue
                Choice.objects.create(
                    question=question,
                    text=text,
                    is_correct=bool(option.get("is_correct")),
                    order=choice_index,
                )
        created_assignments = 0
        if assign_department:
            assignment = QuizAssignment.objects.create(
                quiz=self.object,
                department=assign_department,
                due_date=assign_due_date,
                assigned_by=self.request.user,
            )
            sync_quiz_calendar_event(quiz=self.object, department=assign_department, due_date=assign_due_date)
            created_assignments += 1
            create_learning_audit_event(
                event_type="quiz_assigned",
                actor=self.request.user,
                company=self.object.company,
                department=assign_department,
                course=self.object.course or getattr(self.object.module, "course", None),
                module=self.object.module,
                quiz=self.object,
                entity_type="quiz_assignment",
                entity_id=str(assignment.id),
                metadata={
                    "target_type": "department",
                    "target_label": assign_department.name,
                    "due_date": assign_due_date.isoformat() if assign_due_date else "",
                    "source": "quiz_create_flow",
                },
            )
        create_admin_audit_log(
            action="quiz_created",
            actor=self.request.user,
            department=form.cleaned_data.get("department"),
            entity_type="quiz",
            entity_id=str(self.object.id),
            after_json={
                **snapshot_model(
                    self.object,
                    fields=[
                        "id",
                        "title",
                        "assessment_type",
                        "status",
                        "instructions",
                        "passing_score",
                        "time_limit_minutes",
                        "allow_multiple_attempts",
                        "max_attempts",
                        "allow_continue_on_fail",
                        "course",
                        "module",
                        "category",
                    ],
                ),
                "question_count": len(question_items),
                "created_assignments": created_assignments,
            },
        )
        if created_assignments:
            create_admin_audit_log(
                action="quiz_assigned",
                actor=self.request.user,
                department=assign_department or form.cleaned_data.get("department"),
                entity_type="quiz",
                entity_id=str(self.object.id),
                after_json={
                    "quiz_title": self.object.title,
                    "department": assign_department.name if assign_department else "",
                    "due_date": assign_due_date.isoformat() if assign_due_date else "",
                    "source": "quiz_create_flow",
                },
            )
        messages.success(
            self.request,
            f"Quiz created successfully.{f' {created_assignments} assignment(s) were created too.' if created_assignments else ''}",
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Quiz was not saved. Check the highlighted course, module, and assignment fields.")
        return super().form_invalid(form)

    def get_success_url(self):
        return redirect("quiz-list").url


class QuizUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "assessments/quiz_builder_form.html"
    form_class = QuizBuilderForm
    model = Quiz
    pk_url_kwarg = "quiz_id"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin_like or request.user.is_manager_like):
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Quiz.objects.select_related("course", "module", "module__course", "company").prefetch_related("questions__choices")
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        quiz = self.get_object()
        initial["department"] = getattr(quiz.course, "department_id", None) or getattr(getattr(quiz.module, "course", None), "department_id", None)
        existing_assignments = list(
            quiz.assignments.select_related("department", "learner").order_by("created_at")
        )
        department_assignment = next((assignment for assignment in existing_assignments if assignment.department_id), None)
        initial["assign_department"] = department_assignment.department_id if department_assignment else None
        initial["assign_due_date"] = (
            department_assignment.due_date
            if department_assignment and department_assignment.due_date
            else next((assignment.due_date for assignment in existing_assignments if assignment.due_date), None)
        )
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question_types"] = [
            (Question.QuestionType.SINGLE_CHOICE, "MCQ"),
            (Question.QuestionType.MULTIPLE_CHOICE, "MSQ"),
            (Question.QuestionType.TRUE_FALSE, "True / False"),
            (Question.QuestionType.SHORT_ANSWER, "Fill In"),
            (Question.QuestionType.ESSAY, "Descriptive"),
        ]
        form = context["form"]
        departments = list(form.fields["department"].queryset)
        courses = list(form.fields["course"].queryset.select_related("department"))
        modules = list(form.fields["module"].queryset.select_related("course", "course__department"))
        filter_map = {
            "departments": [{"id": str(department.id), "name": department.name} for department in departments],
            "courses": [{"id": str(course.id), "title": course.title, "department_id": str(course.department_id) if course.department_id else ""} for course in courses],
            "modules": [{"id": str(module.id), "title": module.title, "course_id": str(module.course_id), "department_id": str(module.course.department_id) if module.course.department_id else ""} for module in modules],
        }
        context["quiz_builder_filter_json"] = filter_map
        current_year = timezone.localdate().year
        context["india_holiday_map_json"] = get_india_holiday_map([current_year - 1, current_year, current_year + 1])
        context["initial_questions_payload"] = [
            {
                "question_id": str(question.id),
                "prompt": question.prompt,
                "section_title": question.section_title,
                "question_type": question.question_type,
                "marks": float(question.marks),
                "negative_marks": float(question.negative_marks),
                "suggested_seconds": int(question.suggested_seconds or 0),
                "explanation": question.explanation,
                "correct_answer_text": question.correct_answer_text,
                "style_config": question.style_config or {},
                "options": [{"text": choice.text, "is_correct": choice.is_correct} for choice in question.choices.all().order_by("order")],
            }
            for question in self.object.questions.all().order_by("order")
        ]
        context["builder_mode"] = "edit"
        context["existing_question_count"] = self.object.questions.count()
        return context

    def form_valid(self, form):
        selected_module = form.cleaned_data.get("module")
        selected_course = form.cleaned_data.get("course") or getattr(selected_module, "course", None)
        selected_department = form.cleaned_data.get("department")
        assign_department = form.cleaned_data.get("assign_department")
        form.instance.company = _resolve_quiz_company(
            user=self.request.user,
            department=selected_department,
            course=selected_course,
            module=selected_module,
            assign_department=assign_department,
            existing_quiz=self.object,
        )
        form.instance.course = selected_course
        form.instance.module = selected_module
        linked_course = selected_course
        if selected_department and linked_course and not linked_course.department_id:
            linked_course.department = selected_department
            linked_course.save()
        response = super().form_valid(form)
        questions_payload = self.request.POST.get("questions_payload", "[]")
        try:
            question_items = json.loads(questions_payload)
        except json.JSONDecodeError:
            question_items = []
        self.object.questions.all().delete()
        for index, item in enumerate(question_items, start=1):
            prompt = (item.get("prompt") or "").strip()
            if not prompt:
                continue
            question = Question.objects.create(
                quiz=self.object,
                prompt=prompt,
                section_title=(item.get("section_title") or "").strip(),
                question_type=item.get("question_type") or Question.QuestionType.SINGLE_CHOICE,
                marks=int(item.get("marks") or 1),
                negative_marks=item.get("negative_marks") or 0,
                suggested_seconds=int(item.get("suggested_seconds") or 0),
                explanation=item.get("explanation") or "",
                correct_answer_text=(item.get("correct_answer_text") or "").strip(),
                style_config=item.get("style_config") or {},
                order=index,
            )
            for choice_index, option in enumerate(item.get("options") or [], start=1):
                text = (option.get("text") or "").strip()
                if not text:
                    continue
                Choice.objects.create(
                    question=question,
                    text=text,
                    is_correct=bool(option.get("is_correct")),
                    order=choice_index,
                )
        create_admin_audit_log(
            action="quiz_updated",
            actor=self.request.user,
            department=form.cleaned_data.get("department"),
            entity_type="quiz",
            entity_id=str(self.object.id),
            after_json={
                "quiz_title": self.object.title,
                "question_count": len([item for item in question_items if (item.get("prompt") or "").strip()]),
            },
        )
        messages.success(self.request, "Quiz updated successfully.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Quiz was not updated. Check the highlighted course, module, and question fields.")
        return super().form_invalid(form)

    def get_success_url(self):
        return redirect("quiz-detail", quiz_id=self.object.id).url


class QuizDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "assessments/quiz_confirm_delete.html"
    model = Quiz
    pk_url_kwarg = "quiz_id"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin_like or request.user.is_manager_like):
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Quiz.objects.select_related("course", "module", "module__course", "company")
        return queryset

    def form_valid(self, form):
        before_snapshot = snapshot_model(
            self.object,
            fields=[
                "id",
                "title",
                "assessment_type",
                "status",
                "passing_score",
                "time_limit_minutes",
                "allow_multiple_attempts",
                "max_attempts",
                "allow_continue_on_fail",
                "course",
                "module",
                "category",
            ],
        )
        before_snapshot["question_count"] = self.object.questions.count()
        before_snapshot["assignment_count"] = self.object.assignments.count()
        before_snapshot["attempt_count"] = self.object.attempts.count()
        create_admin_audit_log(
            action="quiz_deleted",
            actor=self.request.user,
            department=getattr(self.object.course, "department", None) or getattr(getattr(self.object.module, "course", None), "department", None),
            entity_type="quiz",
            entity_id=str(self.object.id),
            before_json=before_snapshot,
        )
        messages.success(self.request, "Quiz deleted successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return redirect("quiz-list").url
