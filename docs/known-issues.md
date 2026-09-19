# Known issues

The full Django suite currently runs 92 tests with seven failures. These failures were observed during the open-source cleanup on 2026-09-19 and are not caused by repository-documentation changes.

## Assessment behavior

1. `apps.assessments.tests.QuizDepartmentAlignmentTests.test_builder_form_rejects_learners_from_other_department`
2. `apps.assessments.tests.QuizDepartmentAlignmentTests.test_quiz_detail_shows_resume_state_for_in_progress_attempt`
3. `apps.assessments.tests.QuizDepartmentAlignmentTests.test_quiz_list_exposes_attendance_overview_metrics`

## Course and calendar behavior

4. `apps.courses.tests.CalendarHolidayTests.test_creating_published_course_notifies_relevant_learners`
5. `apps.courses.tests.CalendarHolidayTests.test_india_holiday_helper_contains_january_hindu_regional_festivals`
6. `apps.courses.tests.CalendarHolidayTests.test_updating_published_course_creates_course_updated_notification`
7. `apps.courses.tests.LessonAuthoringTests.test_quiz_builder_shows_question_section_and_connection_guidance`

Run the suite with `python manage.py test`. When addressing one of these failures, add a GitHub issue with expected behavior, reproduction steps, and acceptance criteria before applying the `good first issue` label.
