"""Certificate templates and issued certificate records."""
from django.db import models

from apps.common.models import TimeStampedModel


class CertificateTemplate(TimeStampedModel):
    company = models.ForeignKey("organizations.Company", related_name="certificate_templates", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    course = models.ForeignKey("courses.Course", related_name="certificate_templates", on_delete=models.SET_NULL, blank=True, null=True)
    version = models.PositiveIntegerField(default=1)
    html_template = models.TextField(default="<h1>{{ course }}</h1><p>{{ learner }}</p>")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User",
        related_name="created_certificate_templates",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("company", "name", "-version")

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class Certificate(TimeStampedModel):
    class Status(models.TextChoices):
        ISSUED = "issued", "Issued"
        REVOKED = "revoked", "Revoked"

    company = models.ForeignKey("organizations.Company", related_name="certificates", on_delete=models.CASCADE)
    learner = models.ForeignKey("accounts.User", related_name="certificates", on_delete=models.CASCADE)
    course = models.ForeignKey("courses.Course", related_name="certificates", on_delete=models.CASCADE)
    module = models.ForeignKey(
        "courses.Module",
        related_name="certificates",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    template = models.ForeignKey(CertificateTemplate, related_name="issued_certificates", on_delete=models.SET_NULL, null=True)
    certificate_number = models.CharField(max_length=100, unique=True)
    file_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-issued_at",)

    def __str__(self) -> str:
        return self.certificate_number
