from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

def auth_view(request):
    """Combined authentication view for both login and signup"""
    
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('users:user_dashboard')
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        # SIGNUP LOGIC
        if form_type == 'signup':
            name = request.POST.get('name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validation
            if password != confirm_password:
                messages.error(request, "Passwords don't match!")
                return render(request, "users/auth.html")
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, "This email is already registered!")
                return render(request, "users/auth.html")
            
            # Create user (name can be same, but email must be unique)
            user = User.objects.create_user(
                username=email,  # Use email as unique identifier for username
                email=email,
                password=password,
                first_name=name
            )
            
            # Show success message
            messages.success(request, f"✅ Account created successfully! Welcome {name}. Please login with your credentials.")
            return render(request, "users/auth.html")
        
        # LOGIN LOGIC
        elif form_type == 'signin':
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            # Authenticate using email as username
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name}!")
                return redirect('users:user_dashboard')
            else:
                messages.error(request, "❌ Invalid email or password!")
                return render(request, "users/auth.html")
    
    return render(request, "users/auth.html")