from django.contrib import admin
from .models import (
    InterviewSession, 
    InterviewQuestion, 
    Resume, 
    CVInterviewSession, 
    CVInterviewQuestion
)


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'stage', 'total_score', 'is_completed', 'created_at']
    list_filter = ['stage', 'is_completed', 'difficulty_level']
    search_fields = ['user__username', 'role']
    date_hierarchy = 'created_at'


@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ['session', 'question_number', 'question_type', 'score', 'created_at']
    list_filter = ['question_type']
    search_fields = ['question_text', 'user_answer']


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['user', 'original_filename', 'file_size', 'processing_status', 'total_chunks', 'uploaded_at']
    list_filter = ['processing_status', 'uploaded_at']
    search_fields = ['user__username', 'original_filename']
    date_hierarchy = 'uploaded_at'
    readonly_fields = ['file_size', 'total_chunks', 'extracted_text', 'vector_store_path']


@admin.register(CVInterviewSession)
class CVInterviewSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'resume', 'stage', 'current_question_number', 'total_score', 'is_completed', 'created_at']
    list_filter = ['stage', 'is_completed']
    search_fields = ['user__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['total_score', 'created_at', 'completed_at']


@admin.register(CVInterviewQuestion)
class CVInterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ['session', 'question_number', 'score', 'created_at', 'answered_at']
    search_fields = ['question_text', 'user_answer']
    readonly_fields = ['relevant_context', 'ai_evaluation', 'created_at', 'answered_at']

