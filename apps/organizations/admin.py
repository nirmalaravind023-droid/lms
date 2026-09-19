from django.contrib import admin

from .models import Company, Department


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "company_code", "domain", "is_active")
    search_fields = ("name", "company_code", "domain")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "color", "manager")
    list_filter = ("company",)
    search_fields = ("name", "code")

