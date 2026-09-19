from django.contrib import admin

from .models import Certificate, CertificateTemplate


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "course", "version", "is_active")
    list_filter = ("company", "is_active")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_number", "learner", "course", "status", "issued_at")
    list_filter = ("status", "company")

