from django.db import models
from django.contrib.auth.models import User


class InterviewSession(models.Model):
    STAGE_CHOICES = [
        ("waiting_for_start", "Waiting For Start"),
        ("waiting_for_role", "Waiting For Role"),
        ("waiting_for_topics", "Waiting For Topics"),
        ("interview_started", "Interview Started"),
        ("waiting_for_answer", "Waiting For Answer"),
        ("completed", "Completed"),
    ]

    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, null=True, blank=True)
    topics = models.TextField(null=True, blank=True)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="intermediate")

    current_question_number = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    total_score = models.FloatField(default=0)
    max_score = models.FloatField(default=100)
    percentage_score = models.FloatField(default=0)

    stage = models.CharField(
        max_length=50,
        choices=STAGE_CHOICES,
        default="waiting_for_start"
    )

    is_completed = models.BooleanField(default=False)
    duration_minutes = models.IntegerField(default=0)  # Interview duration
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.role} ({self.created_at.strftime('%Y-%m-%d')})"

    def get_score_percentage(self):
        if self.max_score > 0:
            return round((self.total_score / self.max_score) * 100, 1)
        return 0

    def get_performance_grade(self):
        percentage = self.get_score_percentage()
        if percentage >= 90:
            return "Excellent"
        elif percentage >= 80:
            return "Good"
        elif percentage >= 70:
            return "Average"
        elif percentage >= 60:
            return "Below Average"
        else:
            return "Needs Improvement"


class InterviewQuestion(models.Model):
    QUESTION_TYPES = [
        ("technical", "Technical"),
        ("behavioral", "Behavioral"),
        ("situational", "Situational"),
        ("coding", "Coding"),
    ]

    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    question_number = models.IntegerField(default=1)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default="technical")
    question_text = models.TextField()
    user_answer = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True, default=0)
    max_score = models.FloatField(default=20)  # Each question out of 20
    feedback = models.TextField(null=True, blank=True)
    ai_evaluation = models.JSONField(null=True, blank=True)  # Store AI evaluation details

    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['question_number']

    def __str__(self):
        return f"Q{self.question_number}: {self.question_text[:50]}..."

    def get_score_percentage(self):
        if self.max_score > 0:
            return round((self.score / self.max_score) * 100, 1)
        return 0


# CV Interview Models
class Resume(models.Model):
    """Stores uploaded resume files and their vector store data"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to='resumes/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()  # in bytes
    
    # Vector store information
    vector_store_path = models.CharField(max_length=500, null=True, blank=True)
    total_chunks = models.IntegerField(default=0)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('uploading', 'Uploading'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='uploading'
    )
    error_message = models.TextField(null=True, blank=True)
    
    # Extracted information
    extracted_text = models.TextField(null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.original_filename}"


class CVInterviewSession(models.Model):
    """CV-based interview session using RAG"""
    STAGE_CHOICES = [
        ('waiting_for_start', 'Waiting For Start'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cv_interview_sessions')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='interview_sessions')
    
    current_question_number = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    total_score = models.FloatField(default=0)
    max_score = models.FloatField(default=100)
    
    stage = models.CharField(
        max_length=50,
        choices=STAGE_CHOICES,
        default='waiting_for_start'
    )
    
    is_completed = models.BooleanField(default=False)
    duration_minutes = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - CV Interview ({self.created_at.strftime('%Y-%m-%d')})"
    
    def get_score_percentage(self):
        if self.max_score > 0:
            return round((self.total_score / self.max_score) * 100, 1)
        return 0
    
    def get_performance_grade(self):
        percentage = self.get_score_percentage()
        if percentage >= 90:
            return "Excellent"
        elif percentage >= 80:
            return "Good"
        elif percentage >= 70:
            return "Average"
        elif percentage >= 60:
            return "Below Average"
        else:
            return "Needs Improvement"


class CVInterviewQuestion(models.Model):
    """Questions generated from resume using RAG + Groq LLM"""
    session = models.ForeignKey(
        CVInterviewSession,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    
    question_number = models.IntegerField(default=1)
    question_text = models.TextField()
    
    # Context from resume used to generate this question
    relevant_context = models.TextField(null=True, blank=True)
    
    # User's answer
    user_answer = models.TextField(null=True, blank=True)
    
    # Evaluation
    score = models.FloatField(null=True, blank=True, default=0)
    max_score = models.FloatField(default=20)
    feedback = models.TextField(null=True, blank=True)
    
    # AI evaluation details (JSON)
    ai_evaluation = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['question_number']
    
    def __str__(self):
        return f"CV Q{self.question_number}: {self.question_text[:50]}..."
    
    def get_score_percentage(self):
        if self.max_score > 0:
            return round((self.score / self.max_score) * 100, 1)
        return 0

