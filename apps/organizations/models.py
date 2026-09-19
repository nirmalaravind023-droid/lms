"""Organization data.

These models define the tenant structure for the LMS:
- Company is the top container
- Department/Sector is used to target users, courses, quizzes, and calendar items
"""
from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel


class Company(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    company_code = models.CharField(max_length=50, unique=True)
    domain = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    primary_color = models.CharField(max_length=20, default="#1d4ed8")
    accent_color = models.CharField(max_length=20, default="#16a34a")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Department(TimeStampedModel):
    # Department is also used as the "sector" concept throughout the UI.
    company = models.ForeignKey(Company, related_name="departments", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default="#2563eb")
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        "accounts.User",
        related_name="managed_departments",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("name",)
        unique_together = ("company", "code")

    def __str__(self) -> str:
        return self.name
