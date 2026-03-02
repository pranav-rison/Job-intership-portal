from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from interviews.models import CVInterviewSession

@login_required(login_url='users:auth')
def dashboard(request):
    """User Dashboard with CV Interview Results"""
    # Fetch completed CV interview sessions for the logged-in user
    cv_sessions = CVInterviewSession.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('resume').order_by('created_at')
    
    # Prepare data for the graph
    resume_labels = []
    resume_scores = []
    
    for index, session in enumerate(cv_sessions, start=1):
        resume_labels.append(f"Resume {index}")
        resume_scores.append(session.get_score_percentage())
    
    context = {
        'resume_labels': resume_labels,
        'resume_scores': resume_scores,
        'total_interviews': cv_sessions.count(),
    }
    
    return render(request, 'users/dashboard/dashboard.html', context)
