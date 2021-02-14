from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('hook/', views.webhook_request),
]
