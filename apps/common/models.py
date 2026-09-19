"""Small reusable base models.

Other apps inherit from these so they all get:
- UUID primary keys
- created/updated timestamps
- consistent ordering support
"""
import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrderedModel(TimeStampedModel):
    order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ("order", "created_at")


class LearningAuditEvent(TimeStampedModel):
    """Stores learner evidence for audits and future analytics.

    This is the central log for answers to questions like:
    - who got what
    - who opened/completed it
    - how long they spent
    - what they answered
    - when it happened
    - which company/department it belonged to
    """

    event_type = models.CharField(max_length=80)
    happened_at = models.DateTimeField(default=timezone.now)
    actor = models.ForeignKey(
        "accounts.User",
        related_name="triggered_learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    learner = models.ForeignKey(
        "accounts.User",
        related_name="learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    company = models.ForeignKey(
        "organizations.Company",
        related_name="learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    department = models.ForeignKey(
        "organizations.Department",
        related_name="learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    course = models.ForeignKey(
        "courses.Course",
        related_name="learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    module = models.ForeignKey(
        "courses.Module",
        related_name="learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        related_name="learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    quiz = models.ForeignKey(
        "assessments.Quiz",
        related_name="learning_audit_events",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-happened_at", "-created_at")
        indexes = [
            models.Index(fields=["company", "event_type", "happened_at"], name="learn_audit_comp_type_time_idx"),
            models.Index(fields=["learner", "happened_at"], name="learn_audit_learner_time_idx"),
            models.Index(fields=["course", "happened_at"], name="learn_audit_course_time_idx"),
        ]


class AdminAuditLog(TimeStampedModel):
    """Tracks admin/HR-side create, update, delete, and assignment changes."""

    action = models.CharField(max_length=80)
    performed_at = models.DateTimeField(default=timezone.now)
    actor = models.ForeignKey(
        "accounts.User",
        related_name="admin_audit_logs",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    company = models.ForeignKey(
        "organizations.Company",
        related_name="admin_audit_logs",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    department = models.ForeignKey(
        "organizations.Department",
        related_name="admin_audit_logs",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=64)
    before_json = models.JSONField(default=dict, blank=True)
    after_json = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-performed_at", "-created_at")
        indexes = [
            models.Index(fields=["company", "action", "performed_at"], name="admin_audit_comp_action_idx"),
            models.Index(fields=["actor", "performed_at"], name="admin_audit_actor_time_idx"),
            models.Index(fields=["entity_type", "entity_id"], name="admin_audit_entity_idx"),
        ]
