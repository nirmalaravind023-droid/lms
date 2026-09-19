from django.urls import path

from .views import AdminAnalyticsView


urlpatterns = [
    path("", AdminAnalyticsView.as_view(), name="analytics-dashboard"),
]

