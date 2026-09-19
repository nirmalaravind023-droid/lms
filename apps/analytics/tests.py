from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.models import Quiz, QuizAttempt
from apps.courses.models import Course, Enrollment, Lesson, LessonProgress, Module
from apps.organizations.models import Company, Department


class LearnerDashboardTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Analytics Co", company_code="ANLT")
        self.department = Department.objects.create(company=self.company, name="Tech", code="TECH")
        self.learner = User.objects.create_user(
            username="learner",
            email="learner@analytics.example",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.other_learner = User.objects.create_user(
            username="other",
            email="other@analytics.example",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.course = Course.objects.create(
            company=self.company,
            title="Python Basics",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.learner,
        )
        self.module = Module.objects.create(course=self.course, title="Intro")
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1")
        self.quiz = Quiz.objects.create(company=self.company, title="Quiz 1", course=self.course, status=Quiz.Status.PUBLISHED)

    def test_learner_dashboard_metrics_only_use_current_learner(self):
        Enrollment.objects.create(learner=self.learner, course=self.course, status=Enrollment.Status.COMPLETED)
        Enrollment.objects.create(learner=self.other_learner, course=self.course, status=Enrollment.Status.IN_PROGRESS)
        QuizAttempt.objects.create(quiz=self.quiz, learner=self.learner, percentage=80, is_passed=True)
        LessonProgress.objects.create(
            learner=self.learner,
            enrollment=Enrollment.objects.get(learner=self.learner, course=self.course),
            lesson=self.lesson,
            suspicious_event_count=3,
        )
        LessonProgress.objects.create(
            learner=self.other_learner,
            enrollment=Enrollment.objects.get(learner=self.other_learner, course=self.course),
            lesson=self.lesson,
            suspicious_event_count=6,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("dashboard-home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Sections In Progress")
        self.assertContains(response, "My Completed Sections")
        self.assertContains(response, "My Not Started Sections")
        self.assertContains(response, "My Attention Events")
        self.assertContains(response, "Reading Speed Metric")
        self.assertContains(response, ">3<", html=False)
        self.assertNotContains(response, ">6<", html=False)
