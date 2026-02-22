from django.urls import path
from .views_applied import applied_companies

urlpatterns = [
    path('applied/', applied_companies, name='applied_companies'),
]
