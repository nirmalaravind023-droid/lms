from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import LMSUserChangeForm, LMSUserCreationForm
from .models import User, UserLifecycleRequest


@admin.register(User)
class LMSUserAdmin(UserAdmin):
    add_form = LMSUserCreationForm
    form = LMSUserChangeForm
    model = User
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "company", "department", "role", "is_active")
    list_filter = ("role", "company", "department", "is_active")
    search_fields = ("email", "first_name", "last_name", "username", "employee_code")
    fieldsets = UserAdmin.fieldsets + (
        (
            "LMS",
            {
                "fields": (
                    "company",
                    "department",
                    "role",
                    "employee_code",
                    "phone_number",
                    "must_change_password",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "LMS",
            {
                "fields": (
                    "email",
                    "company",
                    "department",
                    "role",
                    "employee_code",
                )
            },
        ),
    )


@admin.register(UserLifecycleRequest)
class UserLifecycleRequestAdmin(admin.ModelAdmin):
    list_display = (
        "target_user",
        "action",
        "status",
        "requested_by",
        "requested_department",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("action", "status", "requested_department", "reviewed_at", "created_at")
    search_fields = (
        "target_user__email",
        "target_user__username",
        "requested_by__email",
        "reviewed_by__email",
        "note",
        "resolution_note",
    )
    autocomplete_fields = ("target_user", "requested_by", "requested_department", "reviewed_by")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
