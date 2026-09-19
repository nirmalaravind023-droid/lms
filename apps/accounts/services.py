"""Account lifecycle helpers."""
from __future__ import annotations

from datetime import datetime

from django.db import models, transaction
from django.utils import timezone

from apps.common.services import create_admin_audit_log, snapshot_model
from apps.courses.models import CourseAssignment, CourseNotification, Enrollment
from apps.assessments.models import Quiz, QuizAssignment, QuizAttempt

from .models import User, UserLifecycleRequest


def _archive_identifier(prefix: str, user_id, original_value: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    cleaned = (original_value or prefix).replace("@", "_at_").replace(" ", "_")
    return f"archived_{prefix}_{user_id}_{timestamp}_{cleaned}"[:150]


def _alpha_sequence(index: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    value = index
    output = ""
    while True:
        value, remainder = divmod(value, 26)
        output = letters[remainder] + output
        if value == 0:
            return output
        value -= 1


def _name_token(first_name: str, last_name: str, username: str) -> str:
    source = (first_name or last_name or username or "USER").upper()
    cleaned = "".join(char for char in source if char.isalpha())
    return (cleaned[:4] or "USER").ljust(4, "X")


def _generate_employee_code(user: User) -> str:
    if not user.company_id:
        return ""
    existing_count = User.objects.filter(company__company_code=user.company.company_code.upper()).exclude(id=user.id).count()
    sequence_number = existing_count + 1
    alpha_prefix = _alpha_sequence((sequence_number - 1) // 9999)
    sector_token = ((getattr(user.department, "code", "") or "GEN")[:4]).upper()
    name_token = _name_token(user.first_name, user.last_name, user.username)
    while True:
        serial = ((sequence_number - 1) % 9999) + 1
        candidate = f"{alpha_prefix}-{sector_token}-{name_token}-{serial:04d}"
        if not User.objects.filter(employee_code=candidate).exclude(id=user.id).exists():
            return candidate
        sequence_number += 1


def _clear_old_department_learning(user: User, *, old_department_id=None) -> None:
    if old_department_id:
        Enrollment.objects.filter(learner=user, course__department_id=old_department_id).delete()
        CourseAssignment.objects.filter(learner=user, course__department_id=old_department_id).delete()
        QuizAssignment.objects.filter(learner=user, quiz__course__department_id=old_department_id).delete()
        QuizAssignment.objects.filter(learner=user, quiz__module__course__department_id=old_department_id).delete()
        QuizAttempt.objects.filter(learner=user, quiz__course__department_id=old_department_id).delete()
        QuizAttempt.objects.filter(learner=user, quiz__module__course__department_id=old_department_id).delete()


def _sync_department_course_assignments(user: User, *, assigned_by: User | None = None) -> list[CourseAssignment]:
    if not (user.company_id and user.department_id):
        return []

    created_assignments: list[CourseAssignment] = []
    department_assignments = (
        CourseAssignment.objects.select_related("course", "department", "assigned_by")
        .filter(
            company=user.company,
            department=user.department,
            learner__isnull=True,
            is_active=True,
        )
        .order_by("created_at")
    )
    for assignment in department_assignments:
        learner_assignment, created = CourseAssignment.objects.get_or_create(
            company=user.company,
            course=assignment.course,
            learner=user,
            defaults={
                "department": user.department,
                "assigned_by": assignment.assigned_by or assigned_by,
                "due_date": assignment.due_date,
                "is_required": assignment.is_required,
                "is_active": assignment.is_active,
            },
        )
        Enrollment.objects.get_or_create(
            learner=user,
            course=assignment.course,
            defaults={
                "assignment": learner_assignment,
                "status": Enrollment.Status.ASSIGNED,
                "due_date": learner_assignment.due_date,
            },
        )
        if created:
            created_assignments.append(learner_assignment)
    return created_assignments


def _sync_department_quiz_assignments(user: User, *, assigned_by: User | None = None) -> list[QuizAssignment]:
    if not (user.company_id and user.department_id):
        return []

    created_assignments: list[QuizAssignment] = []
    department_assignments = (
        QuizAssignment.objects.select_related("quiz", "assigned_by")
        .filter(
            department=user.department,
            learner__isnull=True,
            quiz__company=user.company,
            quiz__status=Quiz.Status.PUBLISHED,
        )
        .order_by("created_at")
    )
    for assignment in department_assignments:
        learner_assignment, created = QuizAssignment.objects.get_or_create(
            quiz=assignment.quiz,
            learner=user,
            defaults={
                "department": user.department,
                "assigned_by": assignment.assigned_by or assigned_by,
                "due_date": assignment.due_date,
            },
        )
        if created:
            created_assignments.append(learner_assignment)

    department_quizzes = Quiz.objects.filter(
        company=user.company,
        status=Quiz.Status.PUBLISHED,
    ).filter(
        models.Q(course__department=user.department) | models.Q(module__course__department=user.department)
    ).distinct()
    for quiz in department_quizzes:
        learner_assignment, created = QuizAssignment.objects.get_or_create(
            quiz=quiz,
            learner=user,
            defaults={
                "department": user.department,
                "assigned_by": assigned_by,
            },
        )
        if created:
            created_assignments.append(learner_assignment)
    return created_assignments


def _quiz_course(quiz: Quiz):
    return quiz.course or getattr(quiz.module, "course", None)


def _create_new_joiner_learning_notifications(
    user: User,
    *,
    actor: User | None = None,
    course_assignments: list[CourseAssignment] | None = None,
    quiz_assignments: list[QuizAssignment] | None = None,
) -> None:
    grouped: dict[str, dict] = {}

    for assignment in course_assignments or []:
        course = assignment.course
        grouped.setdefault(
            str(course.id),
            {"course": course, "course_assigned": False, "quiz_count": 0},
        )["course_assigned"] = True

    for assignment in quiz_assignments or []:
        course = _quiz_course(assignment.quiz)
        if not course:
            continue
        entry = grouped.setdefault(
            str(course.id),
            {"course": course, "course_assigned": False, "quiz_count": 0},
        )
        entry["quiz_count"] += 1

    display_name = user.get_full_name() or user.username or user.email
    for entry in grouped.values():
        course = entry["course"]
        quiz_count = entry["quiz_count"]
        course_assigned = entry["course_assigned"]
        if course_assigned and quiz_count:
            message = (
                f"Congratulations {display_name}! You are approved. "
                f"{course.title} is ready for you, with {quiz_count} quiz/test item(s) waiting."
            )
        elif course_assigned:
            message = f"Congratulations {display_name}! You are approved. {course.title} is now ready in your learning plan."
        else:
            message = (
                f"Congratulations {display_name}! You are approved. "
                f"{course.title} has {quiz_count} quiz/test item(s) ready for you."
            )
        CourseNotification.objects.create(
            recipient=user,
            actor=actor,
            course=course,
            message=message,
        )


@transaction.atomic
def apply_user_lifecycle_action(
    *,
    user: User,
    action: str,
    actor: User | None = None,
    new_department=None,
    note: str = "",
):
    before_snapshot = snapshot_model(
        user,
        fields=["id", "email", "username", "first_name", "last_name", "company", "department", "role", "is_active", "employee_code"],
    )
    old_department_id = user.department_id

    if action == UserLifecycleRequest.Action.REGISTRATION_APPROVAL:
        if new_department is not None:
            user.department = new_department
            user.company = new_department.company
        user.is_active = True
        if not user.employee_code:
            user.employee_code = _generate_employee_code(user)
        update_fields = ["is_active", "employee_code", "updated_at"]
        if new_department is not None:
            update_fields.extend(["department", "company"])
        user.save(update_fields=update_fields)
        created_course_assignments = _sync_department_course_assignments(user, assigned_by=actor)
        created_quiz_assignments = _sync_department_quiz_assignments(user, assigned_by=actor)
        _create_new_joiner_learning_notifications(
            user,
            actor=actor,
            course_assignments=created_course_assignments,
            quiz_assignments=created_quiz_assignments,
        )
    elif action == UserLifecycleRequest.Action.DEACTIVATE:
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
    elif action == UserLifecycleRequest.Action.REACTIVATE:
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
        _sync_department_course_assignments(user, assigned_by=actor)
        _sync_department_quiz_assignments(user, assigned_by=actor)
    elif action == UserLifecycleRequest.Action.TRANSFER:
        user.department = new_department
        user.is_active = True
        user.save(update_fields=["department", "is_active", "updated_at"])
        _clear_old_department_learning(user, old_department_id=old_department_id)
        _sync_department_course_assignments(user, assigned_by=actor)
        _sync_department_quiz_assignments(user, assigned_by=actor)
    elif action == UserLifecycleRequest.Action.SOFT_DELETE:
        Enrollment.objects.filter(learner=user).delete()
        CourseAssignment.objects.filter(learner=user).delete()
        QuizAssignment.objects.filter(learner=user).delete()
        QuizAttempt.objects.filter(learner=user).delete()
        user.is_active = False
        user.company = None
        user.department = None
        user.employee_code = ""
        user.phone_number = ""
        user.must_change_password = False
        user.email = _archive_identifier("email", user.id, user.email)
        user.username = _archive_identifier("user", user.id, user.username)
        user.first_name = ""
        user.last_name = ""
        user.save()
    else:
        raise ValueError(f"Unsupported lifecycle action: {action}")

    create_admin_audit_log(
        action=f"user_{action}",
        actor=actor,
        department=new_department or getattr(user, "department", None),
        entity_type="user",
        entity_id=str(user.id),
        before_json=before_snapshot,
        after_json=snapshot_model(
            user,
            fields=["id", "email", "username", "first_name", "last_name", "company", "department", "role", "is_active", "employee_code"],
        ),
        metadata={"note": note},
    )
    return user


@transaction.atomic
def resolve_lifecycle_request(*, request_obj: UserLifecycleRequest, reviewer: User, approve: bool, resolution_note: str = ""):
    request_obj.reviewed_by = reviewer
    request_obj.reviewed_at = timezone.now()
    request_obj.resolution_note = resolution_note
    if approve:
        apply_user_lifecycle_action(
            user=request_obj.target_user,
            action=request_obj.action,
            actor=reviewer,
            new_department=request_obj.requested_department,
            note=resolution_note or request_obj.note,
        )
        request_obj.status = UserLifecycleRequest.Status.APPROVED
    else:
        request_obj.status = UserLifecycleRequest.Status.REJECTED
    request_obj.save(
        update_fields=["reviewed_by", "reviewed_at", "resolution_note", "status", "updated_at"]
    )
    return request_obj
