"""Course routes.

Beginner map:
- normal learner pages: course list, course detail, lesson detail
- authoring pages: manage/, builder/, module/lesson create/edit/delete
- small JSON endpoints: reorder and playback tracking
"""
from django.urls import path

from .views import (
    CalendarBoardDataView,
    CalendarBoardView,
    CalendarEventCreateView,
    CalendarEventDeleteView,
    CalendarEventUpdateView,
    CalendarManageListView,
    CourseBuilderView,
    CourseCommentCreateView,
    CourseCompletionView,
    CourseCreateView,
    CourseDeleteView,
    CourseDetailView,
    CourseListView,
    CourseManageListView,
    CourseUpdateView,
    LessonAttentionEventView,
    LessonCreateView,
    LessonDeleteView,
    LessonDetailView,
    LessonPlaybackEventView,
    LessonReorderView,
    LessonUpdateView,
    ModuleCreateView,
    ModuleDeleteView,
    ModuleReorderView,
    ModuleUpdateView,
    NotificationListView,
    NotificationOpenView,
)


urlpatterns = [
    path("", CourseListView.as_view(), name="course-list"),
    path("manage/", CourseManageListView.as_view(), name="course-manage-list"),
    path("manage/new/", CourseCreateView.as_view(), name="course-create"),
    path("manage/<slug:slug>/edit/", CourseUpdateView.as_view(), name="course-edit"),
    path("manage/<slug:slug>/delete/", CourseDeleteView.as_view(), name="course-delete"),
    path("manage/<slug:slug>/modules/new/", ModuleCreateView.as_view(), name="module-create"),
    path("manage/modules/<uuid:module_id>/edit/", ModuleUpdateView.as_view(), name="module-edit"),
    path("manage/modules/<uuid:module_id>/delete/", ModuleDeleteView.as_view(), name="module-delete"),
    path("manage/modules/<uuid:module_id>/lessons/new/", LessonCreateView.as_view(), name="lesson-create"),
    path("manage/lessons/<uuid:lesson_id>/edit/", LessonUpdateView.as_view(), name="lesson-edit"),
    path("manage/lessons/<uuid:lesson_id>/delete/", LessonDeleteView.as_view(), name="lesson-delete"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/<uuid:notification_id>/open/", NotificationOpenView.as_view(), name="notification-open"),
    path("calendar/view/", CalendarBoardView.as_view(), name="calendar-board"),
    path("calendar/data/", CalendarBoardDataView.as_view(), name="calendar-board-data"),
    path("calendar/", CalendarManageListView.as_view(), name="calendar-manage-list"),
    path("calendar/new/", CalendarEventCreateView.as_view(), name="calendar-event-create"),
    path("calendar/<uuid:event_id>/edit/", CalendarEventUpdateView.as_view(), name="calendar-event-edit"),
    path("calendar/<uuid:event_id>/delete/", CalendarEventDeleteView.as_view(), name="calendar-event-delete"),
    path("reorder/modules/", ModuleReorderView.as_view(), name="module-reorder"),
    path("reorder/lessons/", LessonReorderView.as_view(), name="lesson-reorder"),
    path("lessons/<uuid:lesson_id>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("lessons/<uuid:lesson_id>/playback/", LessonPlaybackEventView.as_view(), name="lesson-playback-event"),
    path("lessons/<uuid:lesson_id>/attention/", LessonAttentionEventView.as_view(), name="lesson-attention-event"),
    path("<slug:slug>/completed/", CourseCompletionView.as_view(), name="course-complete"),
    path("<slug:slug>/comments/", CourseCommentCreateView.as_view(), name="course-comment-create"),
    path("<slug:slug>/builder/", CourseBuilderView.as_view(), name="course-builder"),
    path("<slug:slug>/", CourseDetailView.as_view(), name="course-detail"),
]
