from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='users:auth')
def applied_companies(request):
    """Applied Companies List"""
    return render(request, 'application/applied.html')
