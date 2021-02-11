from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('hook/', views.talkin_to_me_bruh),
]