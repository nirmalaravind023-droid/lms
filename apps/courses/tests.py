import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.models import Quiz, QuizAssignment
from apps.common.holidays import get_india_holidays
from apps.courses.forms import CalendarEventForm, LessonForm
from apps.courses.video import normalize_subtitle_file
from apps.courses.models import CalendarEvent, Course, CourseComment, CourseNotification, Enrollment, Lesson, LessonProgress, Module
from apps.certificates.models import Certificate
from apps.organizations.models import Company, Department


class CourseReorderAuthorizationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Primary Co", company_code="PRICO")
        self.department = Department.objects.create(company=self.company, name="Training", code="TRN")
        self.admin_user = User.objects.create_user(
            username="primary-admin",
            email="primary-admin@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.COMPANY_ADMIN,
        )
        self.course = Course.objects.create(
            company=self.company,
            title="Primary Course",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.module = Module.objects.create(course=self.course, title="Allowed Module", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Allowed Lesson", order=1)

        self.other_company = Company.objects.create(name="Other Co", company_code="OTHCO")
        self.other_department = Department.objects.create(company=self.other_company, name="Other", code="OTH")
        self.other_admin = User.objects.create_user(
            username="other-admin",
            email="other-admin@example.com",
            password="pass1234",
            company=self.other_company,
            department=self.other_department,
            role=User.Role.COMPANY_ADMIN,
        )
        self.other_course = Course.objects.create(
            company=self.other_company,
            title="Other Course",
            department=self.other_department,
            status=Course.Status.PUBLISHED,
            created_by=self.other_admin,
        )
        self.other_module = Module.objects.create(course=self.other_course, title="Foreign Module", order=7)
        self.other_lesson = Lesson.objects.create(module=self.other_module, title="Foreign Lesson", order=8)

    def test_module_reorder_rejects_module_from_other_company(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("module-reorder"),
            data=json.dumps([{"id": str(self.other_module.id), "order": 1}]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.other_module.refresh_from_db()
        self.assertEqual(self.other_module.order, 7)

    def test_lesson_reorder_rejects_lesson_from_other_company(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("lesson-reorder"),
            data=json.dumps([{"id": str(self.other_lesson.id), "order": 1}]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.other_lesson.refresh_from_db()
        self.assertEqual(self.other_lesson.order, 8)


class CalendarHolidayTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Calendar Co", company_code="CALCO")
        self.department = Department.objects.create(company=self.company, name="Finance", code="FIN")
        self.admin_user = User.objects.create_user(
            username="calendar-admin",
            email="calendar-admin@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.COMPANY_ADMIN,
        )
        self.learner = User.objects.create_user(
            username="calendar-learner",
            email="calendar-learner@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.course = Course.objects.create(
            company=self.company,
            title="Finance Calendar Course",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )

    def test_india_holiday_helper_contains_republic_day(self):
        holidays = get_india_holidays(2026)
        self.assertIn(
            {
                "date": "2026-01-26",
                "label": "Republic Day",
                "scope": "India National",
                "calendar_key": "india_national",
                "calendar_label": "India National",
                "color": "#2563eb",
                "estimated": "false",
                "source": "Google Calendar",
            },
            holidays,
        )

    def test_india_holiday_helper_contains_january_hindu_regional_festivals(self):
        holidays = get_india_holidays(2026)
        holiday_pairs = {(item["date"], item["label"], item["calendar_key"]) for item in holidays}
        self.assertIn(("2026-01-13", "Lohri", "hinduism"), holiday_pairs)
        self.assertIn(("2026-01-14", "Makar Sankranti", "hinduism"), holiday_pairs)
        self.assertIn(("2026-01-14", "Pongal", "hinduism"), holiday_pairs)
        self.assertIn(("2026-01-15", "Thiruvalluvar Day / Mattu Pongal", "hinduism"), holiday_pairs)

    def test_calendar_board_data_includes_holiday_item(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("calendar-board-data"),
            {"month": 1, "year": 2026},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        january_26 = None
        for week in payload["weeks"]:
            for cell in week:
                if cell["iso_date"] == "2026-01-26":
                    january_26 = cell
                    break
            if january_26:
                break

        self.assertIsNotNone(january_26)
        self.assertTrue(
            any(
                item["kind"] == "holiday"
                and item["title"] == "Republic Day"
                and item["holiday_calendar_key"] == "india_national"
                for item in january_26["events"]
            )
        )
        self.assertIn("calendar_summary", payload)
        self.assertIn("display_month", payload)
        self.assertIn("departments", payload)
        self.assertIn("previous_month", payload)
        self.assertIn("next_month", payload)
        self.assertIn("holiday_items", payload["calendar_summary"])

    def test_learner_calendar_board_data_keeps_company_holidays(self):
        self.client.force_login(self.learner)
        response = self.client.get(
            reverse("calendar-board-data"),
            {"month": 1, "year": 2026},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        january_14 = None
        for week in payload["weeks"]:
            for cell in week:
                if cell["iso_date"] == "2026-01-14":
                    january_14 = cell
                    break
            if january_14:
                break

        self.assertIsNotNone(january_14)
        self.assertTrue(any(item["kind"] == "holiday" for item in january_14["events"]))
        self.assertTrue(payload["is_learner"])
        self.assertEqual(payload["selected_department"], str(self.department.id))
        self.assertEqual(len(payload["departments"]), 1)
        self.assertGreater(payload["calendar_summary"]["holiday_items"], 0)

    def test_calendar_event_form_filters_courses_to_selected_department(self):
        other_department = Department.objects.create(company=self.company, name="Support", code="SUP")
        matching_course = Course.objects.create(
            company=self.company,
            title="Finance Course",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        other_course = Course.objects.create(
            company=self.company,
            title="Support Course",
            department=other_department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        form = CalendarEventForm(
            data={
                "title": "Training",
                "event_type": CalendarEvent.EventType.ASSIGNMENT,
                "department": str(self.department.id),
                "course": str(matching_course.id),
                "start_at": "2026-04-10T09:00",
                "end_at": "2026-04-10T10:00",
                "color": "#2563eb",
            }
        )

        self.assertIn(matching_course, form.fields["course"].queryset)
        self.assertIn(self.course, form.fields["course"].queryset)
        self.assertFalse(form.fields["course"].queryset.filter(id=other_course.id).exists())

    def test_calendar_event_form_rejects_course_from_other_department(self):
        other_department = Department.objects.create(company=self.company, name="Support", code="SUP")
        other_course = Course.objects.create(
            company=self.company,
            title="Support Course",
            department=other_department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )

        form = CalendarEventForm(
            data={
                "title": "Wrong Match",
                "event_type": CalendarEvent.EventType.ASSIGNMENT,
                "department": str(self.department.id),
                "course": str(other_course.id),
                "start_at": "2026-04-10T09:00",
                "end_at": "2026-04-10T10:00",
                "color": "#2563eb",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("course", form.errors)

    def test_calendar_event_form_requires_meeting_link_and_type_for_meeting(self):
        form = CalendarEventForm(
            data={
                "title": "Department Sync",
                "event_type": CalendarEvent.EventType.MEETING,
                "department": str(self.department.id),
                "course": "",
                "meeting_type": "",
                "meeting_url": "",
                "start_at": "2026-04-10T09:00",
                "end_at": "2026-04-10T10:00",
                "color": "#2563eb",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("meeting_type", form.errors)
        self.assertIn("meeting_url", form.errors)

    def test_notification_list_marks_notifications_as_read(self):
        comment = CourseComment.objects.create(course=self.course, author=self.admin_user, body="Please review this")
        CourseNotification.objects.create(
            recipient=self.admin_user,
            actor=self.learner,
            course=self.course,
            comment=comment,
            message="You have a new course comment.",
            is_read=False,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("notification-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourseNotification.objects.filter(recipient=self.admin_user, is_read=False).count(), 0)

    def test_notification_open_redirects_to_specific_comment_anchor(self):
        comment = CourseComment.objects.create(course=self.course, author=self.admin_user, body="Open this comment")
        notification = CourseNotification.objects.create(
            recipient=self.admin_user,
            actor=self.learner,
            course=self.course,
            comment=comment,
            message="You have a new course comment.",
            is_read=False,
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("notification-open", kwargs={"notification_id": notification.id}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'{reverse("course-detail", kwargs={"slug": self.course.slug})}#comment-{comment.id}')

    def test_notification_list_shows_type_specific_badges_and_actions(self):
        CourseNotification.objects.create(
            recipient=self.learner,
            actor=self.admin_user,
            course=self.course,
            message=f"New course added: {self.course.title} is now available for you.",
        )
        CourseNotification.objects.create(
            recipient=self.learner,
            actor=self.admin_user,
            course=self.course,
            message=f"Course updated: {self.course.title} has new changes. Open it to review the latest content.",
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("notification-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New Course Added")
        self.assertContains(response, "Open New Course")
        self.assertContains(response, "Course Updated")
        self.assertContains(response, "View Update")

    def test_creating_published_course_notifies_relevant_learners(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("course-create"),
            data={
                "title": "New Finance Launch",
                "description": "Fresh learning content",
                "department": str(self.department.id),
                "status": Course.Status.PUBLISHED,
                "mandatory": "on",
                "estimated_minutes": 30,
                "certificate_enabled": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        notification = CourseNotification.objects.filter(recipient=self.learner).order_by("-created_at").first()
        self.assertIsNotNone(notification)
        self.assertIn("New course added", notification.message)
        self.assertEqual(notification.badge_label, "New Course Added")
        self.assertEqual(notification.action_label, "Open New Course")

    def test_updating_published_course_creates_course_updated_notification(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("course-edit", kwargs={"slug": self.course.slug}),
            data={
                "title": "Finance Calendar Course Revised",
                "description": "Updated learning path",
                "department": str(self.department.id),
                "status": Course.Status.PUBLISHED,
                "mandatory": "on",
                "estimated_minutes": 45,
                "certificate_enabled": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        notification = CourseNotification.objects.filter(
            recipient=self.learner,
            message__icontains="Course updated",
        ).order_by("-created_at").first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.badge_label, "Course Updated")
        self.assertEqual(notification.action_label, "View Update")

    def test_video_lesson_notification_uses_learning_update_action(self):
        notification = CourseNotification.objects.create(
            recipient=self.learner,
            actor=self.admin_user,
            course=self.course,
            message="New video lesson 'Video 2' is available in Basics.",
        )

        self.assertEqual(notification.notification_kind, "learning_update")
        self.assertEqual(notification.badge_label, "Learning Update")
        self.assertEqual(notification.action_label, "Open Course")

    def test_sector_course_update_notification_uses_view_update_action(self):
        notification = CourseNotification.objects.create(
            recipient=self.learner,
            actor=self.admin_user,
            course=self.course,
            message="Course 'Basics' was updated for your sector: Sales and Marketing.",
        )

        self.assertEqual(notification.notification_kind, "course_updated")
        self.assertEqual(notification.badge_label, "Course Updated")
        self.assertEqual(notification.action_label, "View Update")


class LessonAuthoringTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Lessons Co", company_code="LESSON")
        self.department = Department.objects.create(company=self.company, name="Learning", code="LRN")
        self.admin_user = User.objects.create_user(
            username="lesson-admin",
            email="lesson-admin@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.COMPANY_ADMIN,
        )
        self.learner = User.objects.create_user(
            username="lesson-learner",
            email="lesson-learner@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.course = Course.objects.create(
            company=self.company,
            title="PDF Course",
            department=self.department,
            status=Course.Status.PUBLISHED,
            created_by=self.admin_user,
        )
        self.module = Module.objects.create(course=self.course, title="Reference Pack")

    def test_lesson_form_only_shows_supported_authoring_types(self):
        form = LessonForm()
        self.assertEqual(
            [value for value, _label in form.fields["lesson_type"].choices],
            [Lesson.LessonType.ARTICLE, Lesson.LessonType.PDF, Lesson.LessonType.VIDEO, Lesson.LessonType.LINK],
        )

    def test_lesson_form_rejects_invalid_subtitle_without_uploaded_video(self):
        subtitle_file = SimpleUploadedFile("captions.srt", b"1\n00:00:00,000 --> 00:00:02,000\nHello", content_type="text/plain")
        form = LessonForm(
            data={
                "title": "Video Lesson",
                "lesson_type": Lesson.LessonType.VIDEO,
                "summary": "Video with subtitle only",
                "content": "",
                "external_url": "",
                "transcript": "",
            },
            files={"subtitle_file": subtitle_file},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("subtitle_file", form.errors)

    def test_lesson_form_rejects_non_subtitle_file_extension(self):
        video_file = SimpleUploadedFile("clip.mp4", b"video", content_type="video/mp4")
        subtitle_file = SimpleUploadedFile("notes.pdf", b"%PDF-1.4", content_type="application/pdf")
        form = LessonForm(
            data={
                "title": "Tracked Video",
                "lesson_type": Lesson.LessonType.VIDEO,
                "summary": "Bad subtitle extension",
                "content": "",
                "external_url": "",
                "transcript": "",
            },
            files={"media_file": video_file, "subtitle_file": subtitle_file},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("subtitle_file", form.errors)

    def test_uploaded_srt_subtitle_is_normalized_to_vtt_for_learner_playback(self):
        video_file = SimpleUploadedFile("clip.mp4", b"video", content_type="video/mp4")
        subtitle_file = SimpleUploadedFile(
            "captions.srt",
            b"1\n00:00:00,000 --> 00:00:02,000\nHello learner\n",
            content_type="text/plain",
        )
        lesson = Lesson.objects.create(
            module=self.module,
            title="Video With Subtitle",
            lesson_type=Lesson.LessonType.VIDEO,
            media_file=video_file,
            subtitle_file=subtitle_file,
            order=1,
        )

        normalize_subtitle_file(lesson)
        lesson.save(update_fields=["subtitle_file", "updated_at"])
        lesson.refresh_from_db()

        self.assertTrue(lesson.subtitle_file.name.endswith(".vtt"))

    def test_lesson_form_rejects_video_file_for_non_video_lesson(self):
        video_file = SimpleUploadedFile("clip.mp4", b"video", content_type="video/mp4")
        form = LessonForm(
            data={
                "title": "PDF Lesson",
                "lesson_type": Lesson.LessonType.PDF,
                "summary": "Wrong file type",
                "content": "",
                "external_url": "",
                "transcript": "",
            },
            files={"media_file": video_file},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("media_file", form.errors)

    def test_invalid_lesson_submit_shows_error_popup_copy(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("lesson-create", kwargs={"module_id": self.module.id}),
            data={
                "title": "Broken Video",
                "lesson_type": Lesson.LessonType.VIDEO,
                "summary": "Missing real video source",
                "content": "",
                "external_url": "",
                "transcript": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lesson Upload Error")
        self.assertContains(response, "Check the file type, lesson name, and upload fields below before saving again.")

    def test_course_detail_opens_pdf_lessons_in_new_tab_for_learners(self):
        pdf_file = SimpleUploadedFile("handbook.pdf", b"%PDF-1.4 handbook", content_type="application/pdf")
        lesson = Lesson.objects.create(
            module=self.module,
            title="Employee Handbook",
            lesson_type=Lesson.LessonType.PDF,
            summary="Open the handbook",
            media_file=pdf_file,
            order=1,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("course-detail", kwargs={"slug": self.course.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("lesson-detail", kwargs={"lesson_id": lesson.id}))
        self.assertContains(response, 'target="_blank"', html=False)

    def test_quiz_builder_shows_question_section_and_connection_guidance(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("quiz-create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Question Section")
        self.assertContains(response, "Course Connection Status")
        self.assertContains(response, "This builder reads from the courses and modules you already created.")

    def test_course_slug_is_made_globally_unique_across_companies(self):
        other_company = Company.objects.create(name="Other Co", company_code="OTHCO")
        other_department = Department.objects.create(company=other_company, name="Other Learning", code="OTH")
        other_admin = User.objects.create_user(
            username="other-admin",
            email="other-admin@example.com",
            password="pass1234",
            company=other_company,
            department=other_department,
            role=User.Role.COMPANY_ADMIN,
        )

        duplicate_course = Course.objects.create(
            company=other_company,
            title="PDF Course",
            department=other_department,
            status=Course.Status.PUBLISHED,
            created_by=other_admin,
        )

        self.assertEqual(self.course.slug, "pdf-course")
        self.assertEqual(duplicate_course.slug, "pdf-course-2")

    def test_course_detail_renders_module_quiz_inside_flow(self):
        lesson = Lesson.objects.create(
            module=self.module,
            title="Intro Article",
            lesson_type=Lesson.LessonType.ARTICLE,
            summary="Start here",
            content="Welcome",
            order=1,
        )
        quiz = Quiz.objects.create(
            company=self.company,
            title="Reference Pack Quiz",
            course=self.course,
            module=self.module,
            status=Quiz.Status.PUBLISHED,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("course-detail", kwargs={"slug": self.course.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, lesson.title)
        self.assertContains(response, quiz.title)
        self.assertContains(response, reverse("quiz-detail", kwargs={"quiz_id": quiz.id}))

    def test_last_lesson_offers_module_quiz_as_next_step(self):
        lesson = Lesson.objects.create(
            module=self.module,
            title="Final Lesson",
            lesson_type=Lesson.LessonType.ARTICLE,
            summary="Complete then take quiz",
            content="Finish this section",
            order=1,
        )
        quiz = Quiz.objects.create(
            company=self.company,
            title="End Module Quiz",
            course=self.course,
            module=self.module,
            status=Quiz.Status.PUBLISHED,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("lesson-detail", kwargs={"lesson_id": lesson.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Module Quiz")
        self.assertContains(response, reverse("quiz-detail", kwargs={"quiz_id": quiz.id}))

    def test_course_complete_pushes_assigned_course_quiz(self):
        quiz = Quiz.objects.create(
            company=self.company,
            title="Assigned Final Quiz",
            course=self.course,
            module=self.module,
            status=Quiz.Status.PUBLISHED,
        )
        QuizAssignment.objects.create(quiz=quiz, learner=self.learner)
        Enrollment.objects.create(
            learner=self.learner,
            course=self.course,
            status=Enrollment.Status.COMPLETED,
        )

        self.client.force_login(self.learner)
        response = self.client.get(reverse("course-complete", kwargs={"slug": self.course.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quiz Ready For This Course")
        self.assertContains(response, reverse("quiz-detail", kwargs={"quiz_id": quiz.id}))
        self.assertContains(response, "Certificate Ready")
        self.assertTrue(Certificate.objects.filter(learner=self.learner, course=self.course).exists())

    def test_certificate_list_creates_one_certificate_per_completed_module(self):
        lesson = Lesson.objects.create(
            module=self.module,
            title="Module Completion Lesson",
            lesson_type=Lesson.LessonType.ARTICLE,
            summary="Finish this lesson",
            content="Completed content",
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
        self.assertTrue(Certificate.objects.filter(learner=self.learner, course=self.course, module=self.module).exists())
        self.assertContains(response, self.module.title)
