from django.urls import path
from . import views

app_name = "application"

urlpatterns = [
    path("apply/", views.apply_for_job, name="apply"),
    path("apply/<int:job_id>/", views.apply_for_job, name="apply_job"),
]