from django.urls import include, path
from .views import (
    start_interview, 
    interview_history, 
    start_new_interview,
    save_question_answer,
    complete_interview,
    interview_detail
)

app_name = "interviews"

urlpatterns = [
    path('interview/', start_interview, name='start_interview'),
    path('history/', interview_history, name='interview_history'),
    path('history/<int:session_id>/', interview_detail, name='interview_detail'),
    
    # CV Interview feature (RAG-based)
    path('cv-interview/', include('interviews.urls_cv_interview')),
    
    # API endpoints for interview functionality
    path('api/start-interview/', start_new_interview, name='start_new_interview'),
    path('api/save-answer/', save_question_answer, name='save_question_answer'),
    path('api/complete-interview/', complete_interview, name='complete_interview'),
    
    path("interview-api/", include("interviews.api.urls_api")),
]
