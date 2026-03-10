"""
URL configuration for CV Interview feature
"""

from django.urls import path
from interviews import views_cv_interview

urlpatterns = [
    # Main CV Interview page
    path('', views_cv_interview.cv_interview_page, name='cv_interview'),
    
    # Resume management
    path('upload-resume/', views_cv_interview.upload_resume, name='upload_resume'),
    path('delete-resume/<int:resume_id>/', views_cv_interview.delete_resume, name='delete_resume'),
    
    # Interview session management
    path('start-interview/', views_cv_interview.start_cv_interview, name='cv_start_interview'),
    path('session/<int:session_id>/next-question/', views_cv_interview.get_next_question, name='cv_next_question'),
    path('submit-answer/', views_cv_interview.submit_answer, name='cv_submit_answer'),
    
    # Results and history
    path('session/<int:session_id>/results/', views_cv_interview.get_interview_results, name='cv_interview_results'),
    path('history/', views_cv_interview.get_cv_interview_history, name='cv_interview_history'),
]




