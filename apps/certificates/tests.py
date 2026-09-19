from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.certificates.models import Certificate
from apps.courses.models import Course, Enrollment, Lesson, LessonProgress, Module
from apps.organizations.models import Company, Department


class CertificateListTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Demo Company", company_code="DEMO")
        self.department = Department.objects.create(company=self.company, name="Sales", code="SAL")
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.COMPANY_ADMIN,
        )
        self.learner = User.objects.create_user(
            username="learner",
            email="learner@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.course = Course.objects.create(
            company=self.company,
            department=self.department,
            title="Basics",
            status=Course.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.module = Module.objects.create(course=self.course, title="Module A")

    def test_certificate_list_shows_module_title_for_module_certificate(self):
        Certificate.objects.create(
            company=self.company,
            learner=self.learner,
            course=self.course,
            module=self.module,
            certificate_number="CERT-MODULE-1",
        )
        self.client.force_login(self.learner)

        response = self.client.get(reverse("certificate-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Module A")

    def test_learner_certificate_page_auto_creates_module_certificate_for_completed_module(self):
        lesson = Lesson.objects.create(
            module=self.module,
            title="Lesson 1",
            lesson_type=Lesson.LessonType.ARTICLE,
            content="Done",
            order=1,
        )
        enrollment = Enrollment.objects.create(
            learner=self.learner,
            course=self.course,
            status=Enrollment.Status.IN_PROGRESS,
        )
        LessonProgress.objects.create(
            learner=self.learner,
            enrollment=enrollment,
            lesson=lesson,
            status=LessonProgress.Status.COMPLETED,
        )
        self.client.force_login(self.learner)

        response = self.client.get(reverse("certificate-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Certificate.objects.filter(
                learner=self.learner,
                course=self.course,
                module=self.module,
            ).exists()
        )

    def test_admin_certificate_list_can_filter_by_department(self):
        Certificate.objects.create(
            company=self.company,
            learner=self.learner,
            course=self.course,
            certificate_number="CERT-COURSE-1",
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("certificate-list"), {"department": str(self.department.id)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CERT-COURSE-1")
