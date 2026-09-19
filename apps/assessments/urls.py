"""Assessment routes for list, attempt, assign, and result pages."""
from django.urls import path

from .views import (
    QuizAssignmentCreateView,
    QuizAttemptReviewView,
    QuizCreateView,
    QuizDeleteView,
    QuizDetailView,
    QuizDraftSaveView,
    QuizListView,
    QuizLiveInsightsView,
    QuizResultView,
    QuizStartView,
    QuizUpdateView,
)


urlpatterns = [
    path("", QuizListView.as_view(), name="quiz-list"),
    path("manage/new/", QuizCreateView.as_view(), name="quiz-create"),
    path("manage/<uuid:quiz_id>/edit/", QuizUpdateView.as_view(), name="quiz-update"),
    path("manage/<uuid:quiz_id>/delete/", QuizDeleteView.as_view(), name="quiz-delete"),
    path("assign/", QuizAssignmentCreateView.as_view(), name="quiz-assignment-create"),
    path("<uuid:quiz_id>/", QuizDetailView.as_view(), name="quiz-detail"),
    path("<uuid:quiz_id>/start/", QuizStartView.as_view(), name="quiz-start"),
    path("<uuid:quiz_id>/draft/", QuizDraftSaveView.as_view(), name="quiz-draft-save"),
    path("<uuid:quiz_id>/live-insights/", QuizLiveInsightsView.as_view(), name="quiz-live-insights"),
    path("results/<uuid:attempt_id>/", QuizResultView.as_view(), name="quiz-result"),
    path("results/<uuid:attempt_id>/review/", QuizAttemptReviewView.as_view(), name="quiz-attempt-review"),
]
