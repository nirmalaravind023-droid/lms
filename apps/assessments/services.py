from __future__ import annotations
"""Quiz grading helpers.

Views call these functions after a learner submits a quiz:
- start_attempt()
- record_answers()
- grade_attempt()
- finalize_manual_review()
"""

from decimal import Decimal

from django.utils import timezone

from .models import Choice, Question, Quiz, QuizAnswer, QuizAttempt


OBJECTIVE_TYPES = {
    Question.QuestionType.SINGLE_CHOICE,
    Question.QuestionType.MULTIPLE_CHOICE,
    Question.QuestionType.TRUE_FALSE,
    Question.QuestionType.SHORT_ANSWER,
}


def start_attempt(quiz: Quiz, learner) -> QuizAttempt:
    # Reuse an unfinished attempt so the learner does not lose progress on refresh.
    in_progress = QuizAttempt.objects.filter(
        quiz=quiz,
        learner=learner,
        status=QuizAttempt.Status.IN_PROGRESS,
    ).order_by("-created_at").first()
    if in_progress:
        return in_progress

    if not quiz.allow_multiple_attempts:
        existing = QuizAttempt.objects.filter(
            quiz=quiz,
            learner=learner,
            status__in=[
                QuizAttempt.Status.SUBMITTED,
                QuizAttempt.Status.GRADED,
                QuizAttempt.Status.PENDING_EVALUATION,
            ],
        ).order_by("-created_at").first()
        if existing:
            return None
        return QuizAttempt.objects.create(quiz=quiz, learner=learner)

    completed_count = QuizAttempt.objects.filter(
        quiz=quiz,
        learner=learner,
        status__in=[QuizAttempt.Status.SUBMITTED, QuizAttempt.Status.GRADED, QuizAttempt.Status.PENDING_EVALUATION],
    ).count()
    if completed_count >= max(quiz.max_attempts, 1):
        return None
    return QuizAttempt.objects.create(quiz=quiz, learner=learner)


def save_draft_answers(attempt: QuizAttempt, answer_payload: dict[int, dict]) -> None:
    questions = Question.objects.filter(quiz=attempt.quiz)
    for question in questions:
        payload = answer_payload.get(question.id, {})
        selected_ids = payload.get("selected_choice_ids", [])
        answer_text = payload.get("answer_text", "")
        QuizAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                "selected_choice_ids": selected_ids,
                "answer_text": answer_text,
                "requires_manual_review": question.question_type not in OBJECTIVE_TYPES,
            },
        )


def record_answers(attempt: QuizAttempt, answer_payload: dict[int, dict]) -> None:
    # Converts raw POST data from the form into per-question QuizAnswer rows.
    QuizAnswer.objects.filter(attempt=attempt).delete()
    questions = Question.objects.filter(quiz=attempt.quiz).prefetch_related("choices")
    for question in questions:
        payload = answer_payload.get(question.id, {})
        selected_ids = payload.get("selected_choice_ids", [])
        answer_text = payload.get("answer_text", "")
        QuizAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_choice_ids=selected_ids,
            answer_text=answer_text,
            requires_manual_review=question.question_type not in OBJECTIVE_TYPES,
        )


def grade_attempt(attempt: QuizAttempt) -> QuizAttempt:
    # Objective questions are auto-graded here.
    # Essay/short-answer questions stay pending for manual review.
    total_marks = Decimal("0")
    available_marks = Decimal("0")
    manual_review_required = False

    answers = attempt.answers.select_related("question").all()
    for answer in answers:
        question = answer.question
        available_marks += Decimal(question.marks)

        if question.question_type == Question.QuestionType.SHORT_ANSWER:
            submitted = (answer.answer_text or "").strip().casefold()
            expected = (question.correct_answer_text or "").strip().casefold()
            if submitted and expected and submitted == expected:
                answer.awarded_marks = Decimal(question.marks)
                answer.save(update_fields=["awarded_marks", "updated_at"])
                total_marks += Decimal(question.marks)
            else:
                answer.awarded_marks = Decimal("0") - Decimal(question.negative_marks or 0)
                answer.save(update_fields=["awarded_marks", "updated_at"])
                total_marks += answer.awarded_marks
            continue

        if question.question_type not in OBJECTIVE_TYPES:
            manual_review_required = True
            continue

        selected = {str(choice_id) for choice_id in (answer.selected_choice_ids or [])}
        correct = {str(choice_id) for choice_id in Choice.objects.filter(question=question, is_correct=True).values_list("id", flat=True)}
        if selected == correct:
            answer.awarded_marks = Decimal(question.marks)
            answer.save(update_fields=["awarded_marks", "updated_at"])
            total_marks += Decimal(question.marks)
        else:
            answer.awarded_marks = Decimal("0") - Decimal(question.negative_marks or 0)
            answer.save(update_fields=["awarded_marks", "updated_at"])
            total_marks += answer.awarded_marks

    attempt.submitted_at = timezone.now()
    attempt.score = total_marks
    attempt.percentage = Decimal("0") if available_marks == 0 else (total_marks / available_marks) * Decimal("100")
    attempt.status = QuizAttempt.Status.PENDING_EVALUATION if manual_review_required else QuizAttempt.Status.GRADED
    attempt.is_passed = None if manual_review_required else attempt.percentage >= attempt.quiz.passing_score
    attempt.save(update_fields=["submitted_at", "score", "percentage", "status", "is_passed", "updated_at"])
    return attempt


def finalize_manual_review(attempt: QuizAttempt, marks_map: dict[int, Decimal | int | float | str]) -> QuizAttempt:
    """Finalize HR/admin review for questions that need manual marks."""
    total_marks = Decimal("0")
    available_marks = Decimal("0")

    answers = attempt.answers.select_related("question").all()
    for answer in answers:
        question = answer.question
        available_marks += Decimal(question.marks)
        if answer.requires_manual_review:
            raw_value = marks_map.get(answer.id, answer.awarded_marks)
            awarded = Decimal(str(raw_value or 0))
            max_marks = Decimal(question.marks)
            min_marks = Decimal("0") - Decimal(question.negative_marks or 0)
            awarded = min(max(awarded, min_marks), max_marks)
            answer.awarded_marks = awarded
            answer.requires_manual_review = False
            answer.save(update_fields=["awarded_marks", "requires_manual_review", "updated_at"])
        total_marks += Decimal(answer.awarded_marks or 0)

    attempt.score = total_marks
    attempt.percentage = Decimal("0") if available_marks == 0 else (total_marks / available_marks) * Decimal("100")
    attempt.status = QuizAttempt.Status.GRADED
    attempt.is_passed = attempt.percentage >= attempt.quiz.passing_score
    attempt.submitted_at = attempt.submitted_at or timezone.now()
    attempt.save(update_fields=["submitted_at", "score", "percentage", "status", "is_passed", "updated_at"])
    return attempt
