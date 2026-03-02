from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
import json
from .models import InterviewSession, InterviewQuestion


@login_required(login_url='users:auth')
def start_interview(request):
    """Start Interview AI"""
    return render(request, 'interviews/interview.html')


@login_required(login_url='users:auth')
def interview_history(request):
    """Interview History with pagination and filtering"""
    # Get all completed interview sessions for the user
    sessions = InterviewSession.objects.filter(
        user=request.user, 
        is_completed=True
    ).prefetch_related('questions')
    
    # Filter by role if provided
    role_filter = request.GET.get('role')
    if role_filter:
        sessions = sessions.filter(role__icontains=role_filter)
    
    # Calculate statistics
    total_sessions = sessions.count()
    avg_performance = 0
    total_roles = 0
    avg_questions_per_session = 0
    
    if total_sessions > 0:
        # Calculate average performance
        total_score = sum([s.percentage_score or 0 for s in sessions])
        avg_performance = round(total_score / total_sessions, 1)
        
        # Count unique roles
        unique_roles = sessions.values_list('role', flat=True).distinct()
        total_roles = len(unique_roles)
        
        # Calculate average questions per session
        total_questions = sum([s.questions.count() for s in sessions])
        avg_questions_per_session = round(total_questions / total_sessions, 1)
    
    # Pagination
    paginator = Paginator(sessions, 10)  # 10 sessions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique roles for filter dropdown
    all_roles = InterviewSession.objects.filter(
        user=request.user, 
        is_completed=True
    ).values_list('role', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'sessions': page_obj,
        'all_roles': all_roles,
        'current_role_filter': role_filter,
        'total_sessions': total_sessions,
        'avg_performance': avg_performance,
        'total_roles': total_roles,
        'avg_questions_per_session': avg_questions_per_session,
    }
    return render(request, 'interviews/history.html', context)


@csrf_exempt
@login_required(login_url='users:auth') 
def start_new_interview(request):
    """API endpoint to start a new interview session"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role = data.get('role')
            topics = data.get('topics')
            difficulty = data.get('difficulty', 'intermediate')
            
            # Create new interview session
            session = InterviewSession.objects.create(
                user=request.user,
                role=role,
                topics=topics,
                difficulty_level=difficulty,
                stage='interview_started'
            )
            
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'message': 'Interview session started successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
@login_required(login_url='users:auth')
def save_question_answer(request):
    """API endpoint to save question and answer during interview"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            question_text = data.get('question')
            user_answer = data.get('answer')
            question_number = data.get('question_number')
            question_type = data.get('question_type', 'technical')
            score = data.get('score', 0)
            feedback = data.get('feedback', '')
            ai_evaluation = data.get('ai_evaluation', {})
            
            # Get the session
            session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
            
            # Create or update the question
            question, created = InterviewQuestion.objects.get_or_create(
                session=session,
                question_number=question_number,
                defaults={
                    'question_text': question_text,
                    'question_type': question_type,
                    'user_answer': user_answer,
                    'score': score,
                    'feedback': feedback,
                    'ai_evaluation': ai_evaluation,
                    'answered_at': timezone.now()
                }
            )
            
            if not created:
                # Update existing question
                question.user_answer = user_answer
                question.score = score
                question.feedback = feedback
                question.ai_evaluation = ai_evaluation
                question.answered_at = timezone.now()
                question.save()
            
            # Update session current question number
            session.current_question_number = question_number
            session.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Question and answer saved successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
@login_required(login_url='users:auth')
def complete_interview(request):
    """API endpoint to complete interview and calculate final scores"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            duration_minutes = data.get('duration_minutes', 0)
            
            # Get the session
            session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
            
            # Calculate total score
            questions = session.questions.all()
            total_score = sum(q.score or 0 for q in questions)
            max_score = sum(q.max_score or 20 for q in questions)
            
            # Update session with final data
            session.total_score = total_score
            session.max_score = max_score
            session.percentage_score = session.get_score_percentage()
            session.is_completed = True
            session.stage = 'completed'
            session.completed_at = timezone.now()
            session.duration_minutes = duration_minutes
            session.save()
            
            return JsonResponse({
                'success': True,
                'total_score': total_score,
                'max_score': max_score,
                'percentage': session.percentage_score,
                'grade': session.get_performance_grade(),
                'message': 'Interview completed successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required(login_url='users:auth')
def interview_detail(request, session_id):
    """View detailed interview session with all questions and answers"""
    session = get_object_or_404(
        InterviewSession, 
        id=session_id, 
        user=request.user, 
        is_completed=True
    )
    
    questions = session.questions.all().order_by('question_number')
    
    context = {
        'session': session,
        'questions': questions,
    }
    return render(request, 'interviews/interview_detail.html', context)


@login_required(login_url='users:auth')
def cv_interview(request):
    """CV Interview page"""
    return render(request, 'interviews/cv_interview.html')
