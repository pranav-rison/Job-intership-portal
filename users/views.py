from django.shortcuts import render

# def register(request):
#     return render(request, "users/register.html")

# def login_view(request):
#     return render(request, "users/login.html")

def auth_view(request):
    """Combined authentication view for both login and signup"""
    return render(request, "users/auth.html")