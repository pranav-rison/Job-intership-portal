from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='users:auth')
def start_interview(request):
    """Start Interview AI"""
    return render(request, 'interviews/interview.html')

@login_required(login_url='users:auth')
def interview_history(request):
    """Interview History"""
    return render(request, 'interviews/history.html')
