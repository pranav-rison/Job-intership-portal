from django.urls import path
from .views_dashboard import dashboard

urlpatterns = [
    path('dashboard/', dashboard, name='user_dashboard'),
]
