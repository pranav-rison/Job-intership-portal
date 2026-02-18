from django.shortcuts import render

def home(request):
    return render(request, "core/home.html")

def jobs(request):
    return render(request, "core/jobs.html")