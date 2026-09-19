from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.models import Quiz
from apps.courses.models import CalendarEvent, Course
from apps.messaging.models import Conversation, ConversationParticipant, Message
from apps.organizations.models import Company, Department


class GlobalSearchApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Search Co", company_code="SEARCH")
        self.department = Department.objects.create(company=self.company, name="IT", code="IT")
        self.admin_user = User.objects.create_user(
            username="search-admin",
            email="search-admin@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.COMPANY_ADMIN,
        )
        self.learner = User.objects.create_user(
            username="search-learner",
            email="search-learner@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.course = Course.objects.create(
            company=self.company,
            title="Elastic Python Basics",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.quiz = Quiz.objects.create(
            company=self.company,
            title="Elastic Search Quiz",
            course=self.course,
            status=Quiz.Status.PUBLISHED,
        )
        self.calendar_event = CalendarEvent.objects.create(
            company=self.company,
            title="Elastic Kickoff",
            department=self.department,
            course=self.course,
            event_type=CalendarEvent.EventType.MEETING,
            start_at="2026-04-10T09:00:00Z",
            end_at="2026-04-10T10:00:00Z",
        )
        self.conversation = Conversation.objects.create(company=self.company, title="Elastic Search Thread")
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.admin_user)
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.learner)
        Message.objects.create(conversation=self.conversation, sender=self.admin_user, body="Elastic rollout is ready")

    def test_search_api_returns_cross_module_results(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("global-search-api"), {"q": "Elastic"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "database")
        categories = {item["category"] for item in payload["results"]}
        self.assertIn("Courses", categories)
        self.assertIn("Assessments", categories)
        self.assertIn("Messages", categories)
        self.assertIn("Calendar", categories)

    def test_v1_search_api_uses_standard_response_envelope(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("api_v1:search"), {"q": "Elastic"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["api_version"], "v1")
        self.assertEqual(payload["meta"]["source"], "database")
        self.assertEqual(payload["data"]["query"], "Elastic")
        self.assertTrue(payload["data"]["results"])
        self.assertEqual(payload["errors"], [])

    def test_learner_search_is_company_scoped_and_self_safe(self):
        outsider_company = Company.objects.create(name="Other Co", company_code="OTHER")
        outsider_department = Department.objects.create(company=outsider_company, name="Sales", code="SALES")
        User.objects.create_user(
            username="outside-user",
            email="outside@example.com",
            password="pass1234",
            company=outsider_company,
            department=outsider_department,
            role=User.Role.LEARNER,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("global-search-api"), {"q": "outside"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["results"], [])
