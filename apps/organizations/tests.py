from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Company, Department


class OrganizationModelTests(TestCase):
    def test_company_save_generates_slug_from_name(self):
        company = Company.objects.create(name="Demo Company", company_code="DEMO")

        self.assertEqual(company.slug, "demo-company")

    def test_department_string_returns_name_only(self):
        company = Company.objects.create(name="Demo Company", company_code="DEMO")
        department = Department.objects.create(company=company, name="Sales and Marketing", code="SAM")

        self.assertEqual(str(department), "Sales and Marketing")

    def test_department_can_store_manager_reference(self):
        company = Company.objects.create(name="Demo Company", company_code="DEMO")
        manager = User.objects.create_user(
            username="hr",
            email="hr@example.com",
            password="pass1234",
            company=company,
            role=User.Role.HR_MANAGER,
        )
        department = Department.objects.create(
            company=company,
            name="Human Resources",
            code="HR",
            manager=manager,
        )

        self.assertEqual(department.manager, manager)
