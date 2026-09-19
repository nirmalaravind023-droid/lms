"""Read/query helpers for the courses app."""

from apps.accounts.models import User
from apps.organizations.models import Department


def manageable_departments_for_user(user: User):
    """Return departments the user may manage or view in authoring flows."""
    if not user.company_id:
        return Department.objects.none()
    departments = user.company.departments.order_by("name")
    if user.is_manager_like or user.is_admin_like:
        return departments
    if user.department_id:
        return departments.filter(id=user.department_id)
    return Department.objects.none()
