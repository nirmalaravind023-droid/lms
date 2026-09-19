"""Shared audit helpers.

These helpers centralize how the LMS writes:
- learner evidence events
- admin/HR audit trails
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from .models import AdminAuditLog, LearningAuditEvent


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def snapshot_model(instance, *, fields: list[str] | None = None) -> dict:
    if not instance:
        return {}
    chosen_fields = fields or [field.name for field in instance._meta.fields]
    data = {}
    for field_name in chosen_fields:
        value = getattr(instance, field_name, None)
        if hasattr(value, "pk"):
            data[field_name] = str(value.pk)
            data[f"{field_name}_label"] = str(value)
        else:
            data[field_name] = _json_safe(value)
    return data


def create_learning_audit_event(
    *,
    event_type: str,
    actor=None,
    learner=None,
    company=None,
    department=None,
    course=None,
    module=None,
    lesson=None,
    quiz=None,
    entity_type: str = "",
    entity_id: str | None = None,
    metadata: dict | None = None,
):
    learner = learner or actor
    company = company or getattr(learner, "company", None) or getattr(actor, "company", None) or getattr(course, "company", None) or getattr(quiz, "company", None)
    department = department or getattr(learner, "department", None) or getattr(actor, "department", None) or getattr(course, "department", None)
    course = course or getattr(module, "course", None) or getattr(lesson, "module", None) and lesson.module.course or getattr(quiz, "course", None) or getattr(getattr(quiz, "module", None), "course", None)
    module = module or getattr(lesson, "module", None) or getattr(quiz, "module", None)
    entity_pk = entity_id or getattr(lesson, "pk", None) or getattr(module, "pk", None) or getattr(course, "pk", None) or getattr(quiz, "pk", None) or getattr(learner, "pk", None)
    return LearningAuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        learner=learner,
        company=company,
        department=department,
        course=course,
        module=module,
        lesson=lesson,
        quiz=quiz,
        entity_type=entity_type,
        entity_id=str(entity_pk or ""),
        metadata=_json_safe(metadata or {}),
    )


def create_admin_audit_log(
    *,
    action: str,
    actor=None,
    department=None,
    entity_type: str,
    entity_id: str | None,
    before_json: dict | None = None,
    after_json: dict | None = None,
    metadata: dict | None = None,
):
    return AdminAuditLog.objects.create(
        action=action,
        actor=actor,
        company=getattr(actor, "company", None),
        department=department or getattr(actor, "department", None),
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        before_json=_json_safe(before_json or {}),
        after_json=_json_safe(after_json or {}),
        metadata=_json_safe(metadata or {}),
    )
