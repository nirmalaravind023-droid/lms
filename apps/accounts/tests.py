from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from apps.accounts.forms import RegistrationForm
from apps.accounts.models import User, UserLifecycleRequest
from apps.assessments.models import Quiz, QuizAssignment, QuizAttempt
from apps.common.context_processors import notification_counts
from apps.common.models import AdminAuditLog, LearningAuditEvent
from apps.courses.models import Course, CourseAssignment, CourseNotification, Enrollment, Lesson, LessonProgress, Module
from apps.organizations.models import Company, Department


class UserLifecycleFlowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="People Co", company_code="PEOPLE")
        self.old_department = Department.objects.create(company=self.company, name="HR", code="HR")
        self.new_department = Department.objects.create(company=self.company, name="IT", code="IT")
        self.hr_user = User.objects.create_user(
            username="hr-user",
            email="hr@people.example",
            password="pass1234",
            company=self.company,
            department=self.old_department,
            role=User.Role.HR_MANAGER,
        )
        self.learner = User.objects.create_user(
            username="learner-user",
            email="learner@people.example",
            password="pass1234",
            company=self.company,
            department=self.old_department,
            role=User.Role.LEARNER,
            employee_code="A-HR-LEAR-0001",
            phone_number="1234567890",
        )
        self.old_course = Course.objects.create(
            company=self.company,
            title="HR Basics",
            department=self.old_department,
            status=Course.Status.PUBLISHED,
            created_by=self.hr_user,
        )
        self.old_quiz = Quiz.objects.create(
            company=self.company,
            title="HR Quiz",
            course=self.old_course,
            status=Quiz.Status.PUBLISHED,
        )
        self.old_module = Module.objects.create(course=self.old_course, title="HR Module")
        self.old_lesson = Lesson.objects.create(
            module=self.old_module,
            title="HR Lesson",
            lesson_type=Lesson.LessonType.ARTICLE,
            content="Read this",
            order=1,
        )

    def test_hr_can_deactivate_and_reactivate_user(self):
        self.client.force_login(self.hr_user)

        deactivate_response = self.client.post(
            reverse("user-lifecycle-action", kwargs={"user_id": self.learner.id}),
            data={"action": UserLifecycleRequest.Action.DEACTIVATE},
        )
        self.assertEqual(deactivate_response.status_code, 302)
        self.learner.refresh_from_db()
        self.assertFalse(self.learner.is_active)

        reactivate_response = self.client.post(
            reverse("user-lifecycle-action", kwargs={"user_id": self.learner.id}),
            data={"action": UserLifecycleRequest.Action.REACTIVATE},
        )
        self.assertEqual(reactivate_response.status_code, 302)
        self.learner.refresh_from_db()
        self.assertTrue(self.learner.is_active)

    def test_transfer_updates_department_and_clears_old_department_learning(self):
        CourseAssignment.objects.create(company=self.company, course=self.old_course, learner=self.learner)
        Enrollment.objects.create(learner=self.learner, course=self.old_course)
        QuizAssignment.objects.create(quiz=self.old_quiz, learner=self.learner)
        QuizAttempt.objects.create(quiz=self.old_quiz, learner=self.learner)

        self.client.force_login(self.hr_user)
        response = self.client.post(
            reverse("user-transfer", kwargs={"user_id": self.learner.id}),
            data={
                "department": str(self.new_department.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.learner.refresh_from_db()
        self.assertEqual(self.learner.department_id, self.new_department.id)
        self.assertFalse(Enrollment.objects.filter(learner=self.learner, course=self.old_course).exists())
        self.assertFalse(CourseAssignment.objects.filter(learner=self.learner, course=self.old_course).exists())
        self.assertFalse(QuizAssignment.objects.filter(learner=self.learner, quiz=self.old_quiz).exists())
        self.assertFalse(QuizAttempt.objects.filter(learner=self.learner, quiz=self.old_quiz).exists())
        self.assertContains(response, "data-flash-popup=\"true\"", html=False)

    def test_transfer_to_same_department_returns_without_changes(self):
        self.client.force_login(self.hr_user)

        response = self.client.post(
            reverse("user-transfer", kwargs={"user_id": self.learner.id}),
            data={
                "department": str(self.old_department.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.learner.refresh_from_db()
        self.assertEqual(self.learner.department_id, self.old_department.id)

    def test_transfer_page_loads_for_hr(self):
        self.client.force_login(self.hr_user)

        response = self.client.get(reverse("user-transfer", kwargs={"user_id": self.learner.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transfer User")
        self.assertContains(response, self.learner.email)

    def test_hr_can_still_manage_user_after_transfer_to_another_department(self):
        self.learner.department = self.new_department
        self.learner.save(update_fields=["department", "updated_at"])

        self.client.force_login(self.hr_user)
        response = self.client.post(
            reverse("user-lifecycle-action", kwargs={"user_id": self.learner.id}),
            data={"action": UserLifecycleRequest.Action.DEACTIVATE},
        )

        self.assertEqual(response.status_code, 302)
        self.learner.refresh_from_db()
        self.assertFalse(self.learner.is_active)

    def test_soft_delete_request_can_be_approved_by_hr_and_resets_user(self):
        CourseAssignment.objects.create(company=self.company, course=self.old_course, learner=self.learner)
        Enrollment.objects.create(learner=self.learner, course=self.old_course)
        QuizAssignment.objects.create(quiz=self.old_quiz, learner=self.learner)
        QuizAttempt.objects.create(quiz=self.old_quiz, learner=self.learner)

        self.client.force_login(self.learner)
        request_response = self.client.post(
            reverse("user-lifecycle-request-create"),
            data={"action": UserLifecycleRequest.Action.SOFT_DELETE},
        )
        self.assertEqual(request_response.status_code, 302)
        lifecycle_request = UserLifecycleRequest.objects.get(target_user=self.learner)
        self.assertEqual(lifecycle_request.status, UserLifecycleRequest.Status.PENDING)

        self.client.force_login(self.hr_user)
        approval_response = self.client.post(
            reverse("user-lifecycle-request-decision", kwargs={"request_id": lifecycle_request.id}),
            data={"decision": "approve"},
        )
        self.assertEqual(approval_response.status_code, 302)

        lifecycle_request.refresh_from_db()
        self.learner.refresh_from_db()
        self.assertEqual(lifecycle_request.status, UserLifecycleRequest.Status.APPROVED)
        self.assertFalse(self.learner.is_active)
        self.assertIsNone(self.learner.company)
        self.assertIsNone(self.learner.department)
        self.assertEqual(self.learner.employee_code, "")
        self.assertNotEqual(self.learner.email, "learner@people.example")
        self.assertNotEqual(self.learner.username, "learner-user")
        self.assertFalse(Enrollment.objects.filter(learner=self.learner).exists())
        self.assertFalse(CourseAssignment.objects.filter(learner=self.learner).exists())
        self.assertFalse(QuizAssignment.objects.filter(learner=self.learner).exists())
        self.assertFalse(QuizAttempt.objects.filter(learner=self.learner).exists())

    def test_learner_directory_only_shows_own_details(self):
        other_learner = User.objects.create_user(
            username="other-learner",
            email="other@people.example",
            password="pass1234",
            company=self.company,
            department=self.old_department,
            role=User.Role.LEARNER,
            employee_code="A-HR-LEAR-0002",
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("user-directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Details")
        self.assertContains(response, self.learner.email)
        self.assertNotContains(response, "All Users")
        self.assertNotContains(response, "Pending User Requests")
        self.assertNotContains(response, other_learner.email)

    def test_hr_can_open_people_profile_and_see_hours_and_activity(self):
        enrollment = Enrollment.objects.create(learner=self.learner, course=self.old_course, completion_percentage=80)
        LessonProgress.objects.create(
            learner=self.learner,
            enrollment=enrollment,
            lesson=self.old_lesson,
            status=LessonProgress.Status.COMPLETED,
            time_spent_seconds=7200,
        )
        QuizAttempt.objects.create(
            quiz=self.old_quiz,
            learner=self.learner,
            status=QuizAttempt.Status.SUBMITTED,
            percentage=85,
            score=8.5,
        )
        LearningAuditEvent.objects.create(
            event_type="lesson_completed",
            learner=self.learner,
            actor=self.learner,
            company=self.company,
            department=self.old_department,
            course=self.old_course,
            lesson=self.old_lesson,
            entity_type="lesson",
            entity_id=str(self.old_lesson.id),
        )

        self.client.force_login(self.hr_user)
        response = self.client.get(reverse("user-detail", kwargs={"user_id": self.learner.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "People Management")
        self.assertContains(response, self.learner.username)
        self.assertContains(response, "2.0 hrs")
        self.assertContains(response, self.old_course.title)
        self.assertContains(response, self.old_lesson.title)

    def test_global_people_search_points_to_person_detail(self):
        from apps.common.search import unified_search

        results, _source = unified_search(self.hr_user, "learner-user")

        people_result = next(item for item in results if item["category"] == "People")
        self.assertEqual(people_result["url"], reverse("user-detail", kwargs={"user_id": self.learner.id}))


class AuthenticationAuditTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Audit Co", company_code="AUDIT")
        self.department = Department.objects.create(company=self.company, name="Security", code="SEC")
        self.user = User.objects.create_user(
            username="audit-user",
            email="audit@example.com",
            password="StrongPass123!",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )

    def test_login_logout_and_failed_login_create_audit_logs(self):
        self.client.post(
            reverse("login"),
            data={"username": self.user.email, "password": "StrongPass123!"},
            HTTP_USER_AGENT="Audit test browser",
            REMOTE_ADDR="192.0.2.10",
        )
        self.client.post(reverse("logout"), HTTP_USER_AGENT="Audit test browser", REMOTE_ADDR="192.0.2.10")
        self.client.post(
            reverse("login"),
            data={"username": self.user.email, "password": "wrong-password"},
            HTTP_USER_AGENT="Audit test browser",
            REMOTE_ADDR="192.0.2.11",
        )

        actions = list(AdminAuditLog.objects.order_by("created_at").values_list("action", flat=True))
        self.assertIn("auth_login", actions)
        self.assertIn("auth_logout", actions)
        self.assertIn("auth_login_failed", actions)
        failed_log = AdminAuditLog.objects.get(action="auth_login_failed")
        self.assertEqual(failed_log.metadata["username"], self.user.email)
        self.assertEqual(failed_log.metadata["ip_address"], "192.0.2.11")


class RegistrationApprovalFlowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Demo Company", company_code="DEMO")
        self.department = Department.objects.create(company=self.company, name="Sales", code="SALES")
        self.second_company = Company.objects.create(name="Beta Learning", company_code="BETA")
        self.second_department = Department.objects.create(company=self.second_company, name="Finance", code="FIN")
        self.hr_user = User.objects.create_user(
            username="hr-admin",
            email="hr@acme.example",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.HR_MANAGER,
        )
        self.sales_course = Course.objects.create(
            company=self.company,
            title="Sales Onboarding",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.hr_user,
        )
        self.sales_quiz = Quiz.objects.create(
            company=self.company,
            title="Sales Basics Quiz",
            course=self.sales_course,
            status=Quiz.Status.PUBLISHED,
        )
        CourseAssignment.objects.create(
            company=self.company,
            course=self.sales_course,
            department=self.department,
            assigned_by=self.hr_user,
        )
        QuizAssignment.objects.create(
            quiz=self.sales_quiz,
            department=self.department,
            assigned_by=self.hr_user,
        )

    def test_registration_creates_pending_employee_request_for_hr_approval(self):
        response = self.client.post(
            reverse("register"),
            data={
                "first_name": "New",
                "last_name": "Employee",
                "email": "employee@acme.example",
                "username": "employee-user",
                "phone_number": "9999999999",
                "department": str(self.department.id),
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("register-success"))
        user = User.objects.get(email="employee@acme.example")
        self.assertFalse(user.is_active)
        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertEqual(user.employee_code, "")
        approval_request = UserLifecycleRequest.objects.get(target_user=user)
        self.assertEqual(approval_request.action, UserLifecycleRequest.Action.REGISTRATION_APPROVAL)
        self.assertEqual(approval_request.status, UserLifecycleRequest.Status.PENDING)

        self.client.force_login(self.hr_user)
        approval_response = self.client.post(
            reverse("user-lifecycle-request-decision", kwargs={"request_id": approval_request.id}),
            data={"decision": "approve"},
        )

        self.assertEqual(approval_response.status_code, 302)
        user.refresh_from_db()
        approval_request.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.employee_code)
        self.assertEqual(approval_request.status, UserLifecycleRequest.Status.APPROVED)
        self.assertTrue(CourseAssignment.objects.filter(course=self.sales_course, learner=user, department=self.department).exists())
        self.assertTrue(Enrollment.objects.filter(course=self.sales_course, learner=user, status=Enrollment.Status.ASSIGNED).exists())
        self.assertTrue(QuizAssignment.objects.filter(quiz=self.sales_quiz, learner=user, department=self.department).exists())
        welcome_notification = CourseNotification.objects.filter(recipient=user, course=self.sales_course).order_by('-created_at').first()
        self.assertIsNotNone(welcome_notification)
        self.assertIn('Congratulations', welcome_notification.message)
        self.assertIn(self.sales_course.title, welcome_notification.message)

    def test_registration_form_only_lists_existing_admin_departments(self):
        form = RegistrationForm()

        self.assertQuerySetEqual(
            form.fields["department"].queryset.order_by("company__name", "name"),
            Department.objects.filter(company=self.company).order_by("company__name", "name"),
            transform=lambda department: department,
        )

    def test_registration_form_department_labels_show_only_department_name(self):
        form = RegistrationForm()

        label = form.fields["department"].label_from_instance(self.department)

        self.assertEqual(label, "Sales")
        self.assertNotIn(self.company.name, label)

    def test_registration_does_not_seed_extra_default_departments(self):
        self.client.post(
            reverse("register"),
            data={
                "first_name": "Seed",
                "last_name": "Check",
                "email": "seed-check@acme.example",
                "username": "seed-check-user",
                "phone_number": "8888888888",
                "department": str(self.department.id),
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertQuerySetEqual(
            Department.objects.filter(company__in=[self.company, self.second_company]).order_by("company__name", "name"),
            [self.second_department, self.department],
            transform=lambda department: department,
        )

    def test_registration_rejects_department_outside_demo_company(self):
        response = self.client.post(
            reverse("register"),
            data={
                "first_name": "Finance",
                "last_name": "Joiner",
                "email": "finance-joiner@beta.example",
                "username": "finance-joiner",
                "phone_number": "7777777777",
                "department": str(self.second_department.id),
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("department", form.errors)

    def test_registration_rejects_duplicate_email_username_and_phone_number(self):
        User.objects.create_user(
            username="existing-user",
            email="existing@acme.example",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
            phone_number="6666666666",
        )

        response = self.client.post(
            reverse("register"),
            data={
                "first_name": "Dup",
                "last_name": "Check",
                "email": "existing@acme.example",
                "username": "existing-user",
                "phone_number": "6666666666",
                "department": str(self.department.id),
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("email", form.errors)
        self.assertIn("username", form.errors)
        self.assertIn("phone_number", form.errors)

    def test_pending_registration_increases_admin_notification_count(self):
        pending_user = User.objects.create_user(
            username="notify-user",
            email="notify@demo.example",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
            is_active=False,
        )
        UserLifecycleRequest.objects.create(
            target_user=pending_user,
            requested_by=pending_user,
            action=UserLifecycleRequest.Action.REGISTRATION_APPROVAL,
            status=UserLifecycleRequest.Status.PENDING,
        )

        request = RequestFactory().get("/")
        request.user = self.hr_user
        context = notification_counts(request)

        self.assertEqual(context["unread_course_notifications"], 1)

    def test_hr_can_change_department_during_registration_approval(self):
        replacement_department = Department.objects.create(company=self.company, name="Finance", code="FIN")
        pending_user = User.objects.create_user(
            username="new-joiner",
            email="new-joiner@demo.example",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
            is_active=False,
        )
        approval_request = UserLifecycleRequest.objects.create(
            target_user=pending_user,
            requested_by=pending_user,
            action=UserLifecycleRequest.Action.REGISTRATION_APPROVAL,
            status=UserLifecycleRequest.Status.PENDING,
        )

        self.client.force_login(self.hr_user)
        response = self.client.post(
            reverse("user-lifecycle-request-decision", kwargs={"request_id": approval_request.id}),
            data={"decision": "approve", "requested_department": str(replacement_department.id)},
        )

        self.assertEqual(response.status_code, 302)
        pending_user.refresh_from_db()
        approval_request.refresh_from_db()
        self.assertEqual(approval_request.requested_department_id, replacement_department.id)
        self.assertEqual(pending_user.department_id, replacement_department.id)

    def test_registration_approval_syncs_department_course_quizzes_to_new_employee(self):
        pending_user = User.objects.create_user(
            username="new-sales-user",
            email="new-sales@acme.example",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
            is_active=False,
        )
        approval_request = UserLifecycleRequest.objects.create(
            target_user=pending_user,
            requested_by=pending_user,
            action=UserLifecycleRequest.Action.REGISTRATION_APPROVAL,
            status=UserLifecycleRequest.Status.PENDING,
        )

        self.client.force_login(self.hr_user)
        response = self.client.post(
            reverse("user-lifecycle-request-decision", kwargs={"request_id": approval_request.id}),
            data={"decision": "approve"},
        )

        self.assertEqual(response.status_code, 302)
        pending_user.refresh_from_db()
        self.assertTrue(pending_user.is_active)
        self.assertTrue(
            QuizAssignment.objects.filter(
                quiz=self.sales_quiz,
                learner=pending_user,
                department=self.department,
            ).exists()
        )

    def test_pending_registration_login_shows_wait_for_admin_approval_message(self):
        pending_user = User.objects.create_user(
            username="pending-login-user",
            email="pending-login@acme.example",
            password="StrongPass123!",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
            is_active=False,
        )
        UserLifecycleRequest.objects.create(
            target_user=pending_user,
            requested_by=pending_user,
            action=UserLifecycleRequest.Action.REGISTRATION_APPROVAL,
            status=UserLifecycleRequest.Status.PENDING,
        )

        response = self.client.post(
            reverse("login"),
            data={
                "username": "pending-login@acme.example",
                "password": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please Wait For HR Approval")


class DjangoAdminAccessSeparationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Admin Scope Co", company_code="ADM")
        self.department = Department.objects.create(company=self.company, name="Operations", code="OPS")
        self.hr_user = User.objects.create_user(
            username="hr-ops",
            email="hr-ops@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.HR_MANAGER,
            is_staff=True,
        )
        self.developer_admin = User.objects.create_user(
            username="dev-admin",
            email="dev-admin@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.COMPANY_ADMIN,
            is_staff=True,
        )

    def test_hr_staff_user_is_redirected_out_of_django_admin(self):
        self.client.force_login(self.hr_user)

        response = self.client.get(reverse("admin:index"), follow=True)

        self.assertRedirects(response, reverse("dashboard-home"))
        self.assertContains(response, "Django admin is reserved for Developer Admin and Platform Admin accounts.")

    def test_developer_admin_can_stay_inside_django_admin(self):
        self.client.force_login(self.developer_admin)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Site administration")
        self.assertNotContains(response, "Django admin is reserved for Developer Admin and Platform Admin accounts.")
