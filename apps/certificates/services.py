from __future__ import annotations
"""Certificate helper logic.

`issue_certificate()` is called after course completion when a certificate should be created.
"""

from uuid import uuid4

from django.template import Context, Template

from apps.courses.models import LessonProgress

from .models import Certificate, CertificateTemplate


def issue_certificate(enrollment, template: CertificateTemplate | None = None, module=None) -> Certificate:
    # Pick the latest active template for the course if one was not passed in.
    template = template or CertificateTemplate.objects.filter(
        company=enrollment.course.company,
        course=enrollment.course,
        is_active=True,
    ).order_by("-version").first()

    certificate, created = Certificate.objects.get_or_create(
        company=enrollment.course.company,
        learner=enrollment.learner,
        course=enrollment.course,
        module=module,
        defaults={
            "template": template,
            "certificate_number": f"CERT-{uuid4().hex[:12].upper()}",
        },
    )
    if not created:
        return certificate
    if template:
        rendered = Template(template.html_template).render(
            Context(
                {
                    "learner": enrollment.learner,
                    "course": enrollment.course,
                    "module": module,
                    "certificate": certificate,
                }
            )
        )
        certificate.file_path = f"certificates/{certificate.certificate_number}.html"
        certificate.save(update_fields=["file_path", "updated_at"])
        _ = rendered
    return certificate


def is_module_completed(*, enrollment, module) -> bool:
    module_lessons = list(module.lessons.order_by("order", "created_at"))
    if not module_lessons:
        return False
    progress_by_lesson_id = {
        progress.lesson_id: progress
        for progress in LessonProgress.objects.filter(
            enrollment=enrollment,
            learner=enrollment.learner,
            lesson__module=module,
        )
    }
    return all(
        progress_by_lesson_id.get(lesson.id)
        and progress_by_lesson_id[lesson.id].status == LessonProgress.Status.COMPLETED
        for lesson in module_lessons
    )


def ensure_module_certificates(enrollment):
    issued = []
    course = enrollment.course
    if not course.certificate_enabled:
        return issued
    for module in course.modules.order_by("order", "created_at").prefetch_related("lessons"):
        if is_module_completed(enrollment=enrollment, module=module):
            issued.append(issue_certificate(enrollment, module=module))
    return issued
