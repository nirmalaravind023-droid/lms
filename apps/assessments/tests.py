import json
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.forms import QuizBuilderForm
from apps.assessments.models import Question, Quiz, QuizAnswer, QuizAssignment, QuizAttempt
from apps.courses.models import CalendarEvent, Course, Module, Enrollment
from apps.certificates.models import Certificate
from apps.organizations.models import Company, Department


class QuizDepartmentAlignmentTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Acme Learning",
            company_code="ACME",
        )
        self.department_a = Department.objects.create(
            company=self.company,
            name="Sales",
            code="SALES",
        )
        self.department_b = Department.objects.create(
            company=self.company,
            name="Support",
            code="SUPPORT",
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass1234",
            company=self.company,
            role=User.Role.COMPANY_ADMIN,
        )
        self.learner_a = User.objects.create_user(
            username="learner-a",
            email="learner-a@example.com",
            password="pass1234",
            company=self.company,
            department=self.department_a,
            role=User.Role.LEARNER,
        )
        self.learner_b = User.objects.create_user(
            username="learner-b",
            email="learner-b@example.com",
            password="pass1234",
            company=self.company,
            department=self.department_b,
            role=User.Role.LEARNER,
        )
        self.course_a = Course.objects.create(
            company=self.company,
            title="Sales Basics",
            department=self.department_a,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.course_b = Course.objects.create(
            company=self.company,
            title="Support Basics",
            department=self.department_b,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.module_a = Module.objects.create(course=self.course_a, title="Sales Module")

    def test_department_filter_excludes_quiz_from_other_course_department(self):
        quiz_for_department_a = Quiz.objects.create(
            company=self.company,
            title="Sales Quiz",
            course=self.course_a,
            status=Quiz.Status.PUBLISHED,
        )
        mismatched_quiz = Quiz.objects.create(
            company=self.company,
            title="Support Quiz",
            course=self.course_b,
            status=Quiz.Status.PUBLISHED,
        )
        QuizAssignment.objects.create(quiz=mismatched_quiz, department=self.department_a, assigned_by=self.admin_user)

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-list"), {"department": str(self.department_a.id)})

        quizzes = list(response.context["quizzes"])
        self.assertIn(quiz_for_department_a, quizzes)
        self.assertNotIn(mismatched_quiz, quizzes)

    def test_hr_manager_can_see_company_quizzes_outside_own_department(self):
        hr_user = User.objects.create_user(
            username="hr-user",
            email="hr-user@example.com",
            password="pass1234",
            company=self.company,
            department=self.department_b,
            role=User.Role.HR_MANAGER,
        )
        cross_department_quiz = Quiz.objects.create(
            company=self.company,
            title="Sales Managed Quiz",
            course=self.course_a,
            status=Quiz.Status.PUBLISHED,
        )

        self.client.force_login(hr_user)
        response = self.client.get(reverse("quiz-list"))

        quizzes = list(response.context["quizzes"])
        self.assertIn(cross_department_quiz, quizzes)

    def test_admin_can_edit_quiz_from_another_company_in_single_company_mode(self):
        other_company = Company.objects.create(name="Global Demo", company_code="GLOBAL")
        other_department = Department.objects.create(company=other_company, name="Operations", code="OPS")
        other_admin = User.objects.create_user(
            username="global-admin",
            email="global-admin@example.com",
            password="pass1234",
            company=other_company,
            role=User.Role.COMPANY_ADMIN,
        )
        other_course = Course.objects.create(
            company=other_company,
            title="Global Course",
            department=other_department,
            status=Course.Status.PUBLISHED,
            created_by=other_admin,
        )
        other_module = Module.objects.create(course=other_course, title="Global Module")
        shared_quiz = Quiz.objects.create(
            company=other_company,
            title="Shared Quiz",
            course=other_course,
            module=other_module,
            status=Quiz.Status.PUBLISHED,
        )
        question = Question.objects.create(
            quiz=shared_quiz,
            prompt="Visible across admins",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            marks=1,
            order=1,
        )
        from apps.assessments.models import Choice
        Choice.objects.create(question=question, text="Yes", is_correct=True, order=1)
        Choice.objects.create(question=question, text="No", is_correct=False, order=2)

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-update", kwargs={"quiz_id": shared_quiz.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible across admins")
        self.assertContains(response, "Yes")
        self.assertContains(response, "No")

    def test_quiz_builder_form_without_user_company_defaults_to_single_lms_company_departments(self):
        demo_company = Company.objects.create(name="Demo Company", company_code="DEMO")
        demo_department = Department.objects.create(company=demo_company, name="Compliance and Legal", code="COMP")
        other_company = Company.objects.create(name="KME", company_code="KME")
        Department.objects.create(company=other_company, name="Finance / Banking", code="FIN")
        platform_admin = User.objects.create_user(
            username="platform-admin",
            email="platform-admin@example.com",
            password="pass1234",
            role=User.Role.SUPER_ADMIN,
        )

        form = QuizBuilderForm(user=platform_admin)

        self.assertQuerySetEqual(
            form.fields["department"].queryset.order_by("name"),
            [demo_department],
            transform=lambda department: department,
        )
        self.assertEqual(form.fields["department"].label_from_instance(demo_department), "Compliance and Legal")

    def test_quiz_list_exposes_attendance_overview_metrics(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Metrics Quiz",
            course=self.course_a,
            status=Quiz.Status.PUBLISHED,
        )
        QuizAssignment.objects.create(quiz=quiz, learner=self.learner_a, assigned_by=self.admin_user)
        QuizAssignment.objects.create(quiz=quiz, learner=self.learner_b, assigned_by=self.admin_user)
        QuizAttempt.objects.create(
            quiz=quiz,
            learner=self.learner_a,
            status=QuizAttempt.Status.GRADED,
            score=8,
            percentage=80,
            is_passed=True,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-list"))

        self.assertEqual(response.status_code, 200)
        overview = response.context["assessment_overview"]
        self.assertEqual(overview["total_assignments"], 2)
        self.assertEqual(overview["total_attendees"], 1)
        self.assertEqual(overview["total_passed"], 1)
        self.assertContains(response, "People Attended")
        self.assertContains(response, "2 assignment")
        self.assertContains(response, "1 People Attended")

    def test_learner_sees_department_quiz_in_assessment_cards(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="IT Department Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        QuizAssignment.objects.create(quiz=quiz, department=self.department_a, assigned_by=self.admin_user)

        self.client.force_login(self.learner_a)
        response = self.client.get(reverse("quiz-list"))

        self.assertEqual(response.status_code, 200)
        quizzes = list(response.context["quizzes"])
        self.assertIn(quiz, quizzes)
        self.assertContains(response, "Open Quiz")
        self.assertContains(response, "Ready")
        self.assertContains(response, self.department_a.name)
        self.assertContains(response, self.course_a.title)
        self.assertContains(response, self.module_a.title)
        self.assertContains(response, quiz.title)

    def test_learner_assessment_card_shows_resume_attempt_when_in_progress(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Resume Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        QuizAssignment.objects.create(quiz=quiz, department=self.department_a, assigned_by=self.admin_user)
        QuizAttempt.objects.create(
            quiz=quiz,
            learner=self.learner_a,
            status=QuizAttempt.Status.IN_PROGRESS,
        )

        self.client.force_login(self.learner_a)
        response = self.client.get(reverse("quiz-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resume Attempt")
        self.assertContains(response, "In Progress")

    def test_learner_assessment_card_links_to_result_when_attempts_used(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Locked Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
            allow_multiple_attempts=False,
        )
        QuizAssignment.objects.create(quiz=quiz, department=self.department_a, assigned_by=self.admin_user)
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            learner=self.learner_a,
            status=QuizAttempt.Status.GRADED,
            score=8,
            percentage=80,
            is_passed=True,
        )

        self.client.force_login(self.learner_a)
        response = self.client.get(reverse("quiz-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View Result")
        self.assertContains(response, reverse("quiz-result", kwargs={"attempt_id": attempt.id}))

    def test_admin_assessment_management_table_shows_department_course_module_and_quiz(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Technical Stuff Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        QuizAssignment.objects.create(quiz=quiz, department=self.department_a, assigned_by=self.admin_user)

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assessment Management")
        self.assertContains(response, self.department_a.name)
        self.assertContains(response, self.course_a.title)
        self.assertContains(response, self.module_a.title)
        self.assertContains(response, quiz.title)

    def test_quiz_create_assignment_also_syncs_department_calendar(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-create"),
            data={
                "title": "Calendar Quiz",
                "assessment_type": Quiz.AssessmentType.QUIZ,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(self.course_a.id),
                "module": str(self.module_a.id),
                "passing_score": "70",
                "time_limit_minutes": "15",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_a.id),
                "assign_due_date": "2026-04-11",
                "questions_payload": "[]",
            },
        )

        self.assertEqual(response.status_code, 302)
        quiz = Quiz.objects.get(title="Calendar Quiz")
        self.assertTrue(
            CalendarEvent.objects.filter(
                company=self.company,
                department=self.department_a,
                title=quiz.title,
                event_type=CalendarEvent.EventType.QUIZ,
            ).exists()
        )

    def test_builder_form_rejects_assignment_to_different_department(self):
        form = QuizBuilderForm(
            data={
                "title": "Department Locked Quiz",
                "assessment_type": Quiz.AssessmentType.QUIZ,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(self.course_a.id),
                "module": "",
                "passing_score": "70",
                "time_limit_minutes": "10",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_b.id),
                "assign_learners": "",
                "assign_due_date": "",
            },
            user=self.admin_user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("assign_department", form.errors)

    def test_builder_form_rejects_learners_from_other_department(self):
        form = QuizBuilderForm(
            data={
                "title": "Department Locked Quiz",
                "assessment_type": Quiz.AssessmentType.QUIZ,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(self.course_a.id),
                "module": "",
                "passing_score": "70",
                "time_limit_minutes": "10",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_a.id),
                "assign_learners": [str(self.learner_b.id)],
                "assign_due_date": "",
            },
            user=self.admin_user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("assign_learners", form.errors)

    def test_create_quiz_links_unassigned_course_to_selected_department(self):
        course_without_department = Course.objects.create(
            company=self.company,
            title="Python Basics",
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-create"),
            data={
                "title": "Python Test",
                "assessment_type": Quiz.AssessmentType.TEST,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(course_without_department.id),
                "module": "",
                "passing_score": "70",
                "time_limit_minutes": "15",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_a.id),
                "assign_due_date": "",
                "questions_payload": "[]",
            },
        )

        self.assertEqual(response.status_code, 302)
        course_without_department.refresh_from_db()
        self.assertEqual(course_without_department.department_id, self.department_a.id)

    def test_create_quiz_persists_selected_course_link(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-create"),
            data={
                "title": "Course Connected Quiz",
                "assessment_type": Quiz.AssessmentType.QUIZ,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(self.course_a.id),
                "module": "",
                "passing_score": "70",
                "time_limit_minutes": "15",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_a.id),
                "assign_due_date": "",
                "questions_payload": "[]",
            },
        )

        self.assertEqual(response.status_code, 302)
        quiz = Quiz.objects.get(title="Course Connected Quiz")
        self.assertEqual(quiz.course_id, self.course_a.id)
        self.assertIsNone(quiz.module_id)

    def test_create_quiz_uses_module_course_as_linked_course(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-create"),
            data={
                "title": "Module Connected Quiz",
                "assessment_type": Quiz.AssessmentType.QUIZ,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": "",
                "module": str(self.module_a.id),
                "passing_score": "70",
                "time_limit_minutes": "15",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_a.id),
                "assign_due_date": "",
                "questions_payload": "[]",
            },
        )

        self.assertEqual(response.status_code, 302)
        quiz = Quiz.objects.get(title="Module Connected Quiz")
        self.assertEqual(quiz.module_id, self.module_a.id)
        self.assertEqual(quiz.course_id, self.course_a.id)

    def test_create_quiz_creates_department_assignment_without_individual_fanout(self):
        second_department_learner = User.objects.create_user(
            username="learner-a-2",
            email="learner-a-2@example.com",
            password="pass1234",
            company=self.company,
            department=self.department_a,
            role=User.Role.LEARNER,
        )
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-create"),
            data={
                "title": "Department Random Quiz",
                "assessment_type": Quiz.AssessmentType.QUIZ,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(self.course_a.id),
                "module": "",
                "passing_score": "70",
                "time_limit_minutes": "15",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_a.id),
                "assign_due_date": "",
                "questions_payload": "[]",
            },
        )

        self.assertEqual(response.status_code, 302)
        quiz = Quiz.objects.get(title="Department Random Quiz")
        self.assertTrue(quiz.assignments.filter(department=self.department_a, learner__isnull=True).exists())
        learner_ids = set(quiz.assignments.exclude(learner__isnull=True).values_list("learner_id", flat=True))
        self.assertEqual(learner_ids, set())
        self.assertEqual(second_department_learner.department_id, self.department_a.id)

    def test_create_quiz_persists_question_sections_from_builder_payload(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-create"),
            data={
                "title": "Sectioned Quiz",
                "assessment_type": Quiz.AssessmentType.TEST,
                "description": "",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(self.course_a.id),
                "module": str(self.module_a.id),
                "passing_score": "70",
                "time_limit_minutes": "15",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": str(self.department_a.id),
                "assign_due_date": "",
                "questions_payload": """
                [
                  {
                    "prompt": "First question",
                    "section_title": "Section A",
                    "question_type": "single_choice",
                    "marks": 1,
                    "negative_marks": 0,
                    "suggested_seconds": 30,
                    "options": [
                      {"text": "A", "is_correct": true},
                      {"text": "B", "is_correct": false}
                    ]
                  },
                  {
                    "prompt": "Second question",
                    "section_title": "Section B",
                    "question_type": "essay",
                    "marks": 5,
                    "negative_marks": 0,
                    "suggested_seconds": 0,
                    "options": []
                  }
                ]
                """,
            },
        )

        self.assertEqual(response.status_code, 302)
        quiz = Quiz.objects.get(title="Sectioned Quiz")
        self.assertEqual(
            list(quiz.questions.order_by("order").values_list("section_title", flat=True)),
            ["Section A", "Section B"],
        )
        self.assertEqual(Question.objects.filter(quiz=quiz).count(), 2)

    def test_quiz_detail_shows_start_quiz_button_clock_and_section_header(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Timed Section Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
            time_limit_minutes=20,
        )
        Question.objects.create(
            quiz=quiz,
            prompt="Timed question",
            section_title="Section A",
            question_type=Question.QuestionType.ESSAY,
            marks=2,
            order=1,
        )

        self.client.force_login(self.learner_a)
        response = self.client.get(reverse("quiz-detail", kwargs={"quiz_id": quiz.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start Quiz")
        self.assertContains(response, "Exam Timer")
        self.assertContains(response, "Section A")
        self.assertContains(response, "Ready To Start")
        self.assertContains(response, "Answers autosave while you type or choose an option.")

    def test_quiz_detail_shows_resume_state_for_in_progress_attempt(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Resume State Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        Question.objects.create(
            quiz=quiz,
            prompt="Resume question",
            question_type=Question.QuestionType.ESSAY,
            marks=2,
            order=1,
        )
        QuizAttempt.objects.create(
            quiz=quiz,
            learner=self.learner_a,
            status=QuizAttempt.Status.IN_PROGRESS,
        )

        self.client.force_login(self.learner_a)
        response = self.client.get(reverse("quiz-detail", kwargs={"quiz_id": quiz.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resume Attempt")
        self.assertContains(response, "1 Active")

    def test_start_quiz_creates_in_progress_attempt_in_sql(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Startable Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        Question.objects.create(
            quiz=quiz,
            prompt="Question one",
            question_type=Question.QuestionType.ESSAY,
            marks=5,
            order=1,
        )

        self.client.force_login(self.learner_a)
        response = self.client.post(reverse("quiz-start", kwargs={"quiz_id": quiz.id}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("?started=1"))
        self.assertTrue(QuizAttempt.objects.filter(quiz=quiz, learner=self.learner_a, status=QuizAttempt.Status.IN_PROGRESS).exists())

    def test_learner_can_submit_single_choice_quiz_with_uuid_choice_ids(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="UUID Submit Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
            passing_score=50,
        )
        question = Question.objects.create(
            quiz=quiz,
            prompt="Choose the correct option",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            marks=2,
            order=1,
        )
        from apps.assessments.models import Choice
        correct_choice = Choice.objects.create(question=question, text="Correct", is_correct=True, order=1)
        Choice.objects.create(question=question, text="Wrong", is_correct=False, order=2)

        self.client.force_login(self.learner_a)
        response = self.client.post(
            reverse("quiz-detail", kwargs={"quiz_id": quiz.id}),
            data={f"question_{question.id}": str(correct_choice.id)},
        )

        self.assertEqual(response.status_code, 302)
        attempt = QuizAttempt.objects.get(quiz=quiz, learner=self.learner_a)
        self.assertEqual(attempt.status, QuizAttempt.Status.GRADED)
        self.assertTrue(attempt.is_passed)
        saved_answer = QuizAnswer.objects.get(attempt=attempt, question=question)
        self.assertEqual(saved_answer.selected_choice_ids, [str(correct_choice.id)])

    def test_draft_quiz_answers_are_saved_in_sql(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Draft Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        question = Question.objects.create(
            quiz=quiz,
            prompt="Explain draft save",
            question_type=Question.QuestionType.ESSAY,
            marks=5,
            order=1,
        )

        self.client.force_login(self.learner_a)
        start_response = self.client.post(reverse("quiz-start", kwargs={"quiz_id": quiz.id}))
        self.assertEqual(start_response.status_code, 302)
        response = self.client.post(
            reverse("quiz-draft-save", kwargs={"quiz_id": quiz.id}),
            data=json.dumps({str(question.id): {"selected_choice_ids": [], "answer_text": "Saved draft answer"}}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        attempt = QuizAttempt.objects.get(quiz=quiz, learner=self.learner_a, status=QuizAttempt.Status.IN_PROGRESS)
        saved_answer = QuizAnswer.objects.get(attempt=attempt, question=question)
        self.assertEqual(saved_answer.answer_text, "Saved draft answer")

    def test_admin_quiz_detail_shows_attendance_department_and_weak_question_analytics(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Analytics Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        question = Question.objects.create(
            quiz=quiz,
            prompt="Hard question",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            marks=1,
            order=1,
        )
        from apps.assessments.models import Choice
        choice_a = Choice.objects.create(question=question, text="A", is_correct=True, order=1)
        choice_b = Choice.objects.create(question=question, text="B", is_correct=False, order=2)
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            learner=self.learner_a,
            status=QuizAttempt.Status.GRADED,
            score=0,
            percentage=0,
            is_passed=False,
        )
        QuizAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_choice_ids=[str(choice_b.id)],
            awarded_marks=0,
            requires_manual_review=False,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-detail", kwargs={"quiz_id": quiz.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics Overview")
        self.assertContains(response, "Attendance By Department")
        self.assertContains(response, "Weak Questions")
        self.assertContains(response, self.department_a.name)
        self.assertContains(response, "HR/admin review workspace")
        self.assertNotContains(response, "Submit Assessment")

    def test_admin_quiz_detail_hides_zero_live_analytics_before_any_attempt(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Fresh Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-detail", kwargs={"quiz_id": quiz.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics will appear after the first learner attends this quiz.")
        self.assertNotContains(response, "Real-Time Results")

    def test_hr_can_finalize_manual_review_marks(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Essay Review Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
            passing_score=70,
        )
        question = Question.objects.create(
            quiz=quiz,
            prompt="Explain the sales process",
            question_type=Question.QuestionType.ESSAY,
            marks=10,
            order=1,
        )
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            learner=self.learner_a,
            status=QuizAttempt.Status.PENDING_EVALUATION,
        )
        answer = QuizAnswer.objects.create(
            attempt=attempt,
            question=question,
            answer_text="Detailed answer",
            awarded_marks=0,
            requires_manual_review=True,
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-attempt-review", kwargs={"attempt_id": attempt.id}),
            data={f"answer_{answer.id}_marks": "8"},
        )

        self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        answer.refresh_from_db()
        self.assertEqual(attempt.status, QuizAttempt.Status.GRADED)
        self.assertTrue(attempt.is_passed)
        self.assertEqual(float(attempt.score), 8.0)
        self.assertEqual(float(answer.awarded_marks), 8.0)
        self.assertFalse(answer.requires_manual_review)

    def test_review_page_is_visible_to_admin_with_pending_attempt(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Pending Review Quiz",
            course=self.course_a,
            status=Quiz.Status.PUBLISHED,
        )
        question = Question.objects.create(
            quiz=quiz,
            prompt="Write a short note",
            question_type=Question.QuestionType.ESSAY,
            marks=5,
            order=1,
        )
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            learner=self.learner_a,
            status=QuizAttempt.Status.PENDING_EVALUATION,
        )
        QuizAnswer.objects.create(
            attempt=attempt,
            question=question,
            answer_text="My note",
            requires_manual_review=True,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-attempt-review", kwargs={"attempt_id": attempt.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finalize Marks")
        self.assertContains(response, "Manual Review Required")
        self.assertContains(response, self.learner_a.email)
        self.assertContains(response, self.department_a.name)

    def test_admin_can_edit_quiz_questions_and_change_question_type(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Editable Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        old_question = Question.objects.create(
            quiz=quiz,
            prompt="Old MCQ",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            marks=1,
            order=1,
        )
        from apps.assessments.models import Choice
        Choice.objects.create(question=old_question, text="A", is_correct=True, order=1)
        Choice.objects.create(question=old_question, text="B", is_correct=False, order=2)

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("quiz-update", kwargs={"quiz_id": quiz.id}),
            data={
                "title": "Editable Quiz",
                "assessment_type": Quiz.AssessmentType.QUIZ,
                "description": "Updated",
                "instructions": "",
                "category": "",
                "department": str(self.department_a.id),
                "course": str(self.course_a.id),
                "module": str(self.module_a.id),
                "passing_score": "70",
                "time_limit_minutes": "15",
                "allow_multiple_attempts": "",
                "max_attempts": "1",
                "allow_continue_on_fail": "",
                "status": Quiz.Status.PUBLISHED,
                "assign_department": "",
                "assign_due_date": "",
                "questions_payload": """
                [
                  {
                    "prompt": "Updated true false",
                    "section_title": "",
                    "question_type": "true_false",
                    "marks": 2,
                    "negative_marks": 0,
                    "suggested_seconds": 20,
                    "explanation": "",
                    "correct_answer_text": "",
                    "style_config": {"font_family": "", "color": "#0f172a", "spacing": 14},
                    "options": [
                      {"text": "True", "is_correct": true},
                      {"text": "False", "is_correct": false}
                    ]
                  },
                  {
                    "prompt": "Explain why",
                    "section_title": "",
                    "question_type": "essay",
                    "marks": 5,
                    "negative_marks": 0,
                    "suggested_seconds": 0,
                    "explanation": "",
                    "correct_answer_text": "",
                    "style_config": {"font_family": "", "color": "#0f172a", "spacing": 14},
                    "options": []
                  }
                ]
                """,
            },
        )

        self.assertEqual(response.status_code, 302)
        quiz.refresh_from_db()
        questions = list(quiz.questions.order_by("order"))
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].prompt, "Updated true false")
        self.assertEqual(questions[0].question_type, Question.QuestionType.TRUE_FALSE)
        self.assertEqual(questions[0].choices.count(), 2)
        self.assertEqual(questions[1].question_type, Question.QuestionType.ESSAY)

    def test_quiz_update_page_preloads_saved_questions_and_options(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Preloaded Quiz",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        question = Question.objects.create(
            quiz=quiz,
            prompt="Which option is correct?",
            section_title="Section A",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            marks=2,
            order=1,
        )
        from apps.assessments.models import Choice
        Choice.objects.create(question=question, text="Option 1", is_correct=True, order=1)
        Choice.objects.create(question=question, text="Option 2", is_correct=False, order=2)
        QuizAssignment.objects.create(
            quiz=quiz,
            department=self.department_a,
            learner=self.learner_a,
            assigned_by=self.admin_user,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-update", kwargs={"quiz_id": quiz.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 saved question loaded below")
        self.assertContains(response, "Which option is correct?")
        self.assertContains(response, "Option 1")
        self.assertContains(response, "Option 2")
        self.assertContains(response, "Section A")

    def test_admin_can_delete_quiz(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Delete Me",
            course=self.course_a,
            module=self.module_a,
            status=Quiz.Status.PUBLISHED,
        )
        Question.objects.create(
            quiz=quiz,
            prompt="Delete question",
            question_type=Question.QuestionType.SINGLE_CHOICE,
            marks=1,
            order=1,
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("quiz-delete", kwargs={"quiz_id": quiz.id}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Quiz.objects.filter(id=quiz.id).exists())


class QuizBadgeCertificateTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Badge Co", company_code="BADGE")
        self.department = Department.objects.create(company=self.company, name="Learning", code="LRN")
        self.admin_user = User.objects.create_user(
            username="badge-admin",
            email="badge-admin@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.COMPANY_ADMIN,
        )
        self.learner = User.objects.create_user(
            username="badge-learner",
            email="badge-learner@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.course = Course.objects.create(
            company=self.company,
            title="Badge Course",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.quiz = Quiz.objects.create(
            company=self.company,
            title="Badge Quiz",
            course=self.course,
            status=Quiz.Status.PUBLISHED,
            passing_score=70,
        )
        self.question = Question.objects.create(
            quiz=self.quiz,
            prompt="Badge question",
            question_type=Question.QuestionType.ESSAY,
            marks=10,
            order=1,
        )

    def test_passed_quiz_result_shows_badge_and_certificate_link(self):
        Certificate.objects.create(
            company=self.company,
            learner=self.learner,
            course=self.course,
            certificate_number="CERT-BADGE-001",
        )
        attempt = QuizAttempt.objects.create(
            quiz=self.quiz,
            learner=self.learner,
            status=QuizAttempt.Status.GRADED,
            score=8,
            percentage=80,
            is_passed=True,
        )
        QuizAnswer.objects.create(
            attempt=attempt,
            question=self.question,
            awarded_marks=8,
            requires_manual_review=False,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("quiz-result", kwargs={"attempt_id": attempt.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quiz Badge Earned")
        self.assertContains(response, "8 / 10")
        self.assertContains(response, "Connected Certificate")
        self.assertContains(response, reverse("certificate-list"))

    def test_quiz_result_shows_question_answer_correct_answer_and_explanation(self):
        self.question.question_type = Question.QuestionType.SINGLE_CHOICE
        self.question.explanation = "Because this is the expected concept."
        self.question.save(update_fields=["question_type", "explanation", "updated_at"])
        from apps.assessments.models import Choice
        correct_choice = Choice.objects.create(question=self.question, text="Correct option", is_correct=True, order=1)
        Choice.objects.create(question=self.question, text="Wrong option", is_correct=False, order=2)
        attempt = QuizAttempt.objects.create(
            quiz=self.quiz,
            learner=self.learner,
            status=QuizAttempt.Status.GRADED,
            score=10,
            percentage=100,
            is_passed=True,
        )
        QuizAnswer.objects.create(
            attempt=attempt,
            question=self.question,
            selected_choice_ids=[str(correct_choice.id)],
            awarded_marks=10,
            requires_manual_review=False,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("quiz-result", kwargs={"attempt_id": attempt.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Answer:")
        self.assertContains(response, "Correct option")
        self.assertContains(response, "Correct Answer:")
        self.assertContains(response, "Explanation:")
        self.assertContains(response, "Because this is the expected concept.")

    def test_certificate_list_shows_passed_quiz_badge_with_marks(self):
        attempt = QuizAttempt.objects.create(
            quiz=self.quiz,
            learner=self.learner,
            status=QuizAttempt.Status.GRADED,
            score=9,
            percentage=90,
            is_passed=True,
        )
        QuizAnswer.objects.create(
            attempt=attempt,
            question=self.question,
            awarded_marks=9,
            requires_manual_review=False,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("certificate-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quiz Badges")
        self.assertContains(response, self.quiz.title)
        self.assertContains(response, "9 / 10")
        self.assertContains(response, reverse("quiz-result", kwargs={"attempt_id": attempt.id}))
