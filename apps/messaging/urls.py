"""Messaging routes for inbox, new message, and conversation detail."""
from django.urls import path

from .views import ConversationCreateView, ConversationDetailView, ConversationListView


urlpatterns = [
    path("new/", ConversationCreateView.as_view(), name="conversation-create"),
    path("", ConversationListView.as_view(), name="conversation-list"),
    path("<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
]
