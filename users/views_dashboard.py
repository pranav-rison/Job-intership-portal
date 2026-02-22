from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='users:auth')
def dashboard(request):
    """User Dashboard"""
    return render(request, 'users/dashboard/dashboard.html')
