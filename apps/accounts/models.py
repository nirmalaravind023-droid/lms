"""Account models.

`User` is the central identity model used across all apps:
- courses point to users
- messages point to users
- quiz attempts point to users
- notifications point to users
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Platform Admin"
        COMPANY_ADMIN = "company_admin", "Developer Admin"
        HR_MANAGER = "hr_manager", "HR / Manager"
        LEARNER = "learner", "Learner"
        CONTENT_AUTHOR = "content_author", "Content Author"

    email = models.EmailField(unique=True)
    company = models.ForeignKey(
        "organizations.Company",
        related_name="users",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    department = models.ForeignKey(
        "organizations.Department",
        related_name="users",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.LEARNER)
    employee_code = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    must_change_password = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ("email",)
        indexes = [
            models.Index(fields=["company", "role"], name="acct_user_company_role_idx"),
            models.Index(fields=["company", "department"], name="acct_user_company_dept_idx"),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.email

    @property
    def is_admin_like(self) -> bool:
        # Used by templates/views to show authoring and admin actions.
        return self.role in {
            self.Role.SUPER_ADMIN,
            self.Role.COMPANY_ADMIN,
            self.Role.CONTENT_AUTHOR,
        }

    @property
    def is_manager_like(self) -> bool:
        return self.role in {self.Role.HR_MANAGER, self.Role.COMPANY_ADMIN, self.Role.SUPER_ADMIN}

    @property
    def can_access_django_admin(self) -> bool:
        return self.is_superuser or self.role in {
            self.Role.SUPER_ADMIN,
            self.Role.COMPANY_ADMIN,
        }


class UserLifecycleRequest(TimeStampedModel):
    class Action(models.TextChoices):
        REGISTRATION_APPROVAL = "registration_approval", "Approve Employee Registration"
        DEACTIVATE = "deactivate", "Deactivate User"
        REACTIVATE = "reactivate", "Reactivate User"
        TRANSFER = "transfer", "Transfer Department"
        SOFT_DELETE = "soft_delete", "Soft Delete / Reset"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    target_user = models.ForeignKey(
        "accounts.User",
        related_name="lifecycle_requests",
        on_delete=models.CASCADE,
    )
    requested_by = models.ForeignKey(
        "accounts.User",
        related_name="requested_lifecycle_actions",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_department = models.ForeignKey(
        "organizations.Department",
        related_name="requested_user_transfers",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        related_name="reviewed_lifecycle_actions",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "action"], name="acct_life_status_action_idx"),
            models.Index(fields=["target_user", "status"], name="acct_life_target_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.target_user} - {self.get_action_display()} ({self.get_status_display()})"
