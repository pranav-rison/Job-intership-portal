"""
Views for CV Interview feature
Handles resume upload, RAG-based question generation, and answer evaluation
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
from django.db.models import Avg
from django.utils import timezone
import json
import os

from interviews.models import Resume, CVInterviewSession, CVInterviewQuestion
from interviews.services.cv_rag_service import CVRAGService


@login_required
def cv_interview_page(request):
    """Main CV Interview page"""
    # Get user's resumes
    resumes = Resume.objects.filter(user=request.user, processing_status='completed')
    
    # Get recent interview sessions
    recent_sessions = CVInterviewSession.objects.filter(user=request.user)[:5]
    
    # Get statistics
    total_sessions = CVInterviewSession.objects.filter(user=request.user, is_completed=True).count()
    avg_score = CVInterviewSession.objects.filter(
        user=request.user,
        is_completed=True
    ).aggregate(Avg('total_score'))['total_score__avg'] or 0
    
    context = {
        'resumes': resumes,
        'recent_sessions': recent_sessions,
        'total_sessions': total_sessions,
        'average_score': round(avg_score, 1),
    }
    
    return render(request, 'interviews/cv_interview.html', context)


@login_required
@require_http_methods(["POST"])
def upload_resume(request):
    """Handle resume upload and processing"""
    try:
        if 'resume' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        resume_file = request.FILES['resume']
        
        # Validate file type
        if not resume_file.name.endswith('.pdf'):
            return JsonResponse({'error': 'Only PDF files are allowed'}, status=400)
        
        # Validate file size (max 10MB)
        if resume_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File size must be less than 10MB'}, status=400)
        
        # Save file
        file_path = default_storage.save(
            f'resumes/{request.user.id}/{resume_file.name}',
            resume_file
        )
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # Create Resume record
        resume = Resume.objects.create(
            user=request.user,
            file=file_path,
            original_filename=resume_file.name,
            file_size=resume_file.size,
            processing_status='processing'
        )
        
        try:
            # Process resume using RAG service
            rag_service = CVRAGService()
            extracted_text, total_chunks, vector_store_path = rag_service.process_resume(
                full_path,
                request.user.id
            )
            
            # Update resume record
            resume.extracted_text = extracted_text
            resume.total_chunks = total_chunks
            resume.vector_store_path = vector_store_path
            resume.processing_status = 'completed'
            resume.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Resume processed successfully',
                'resume_id': resume.id,
                'total_chunks': total_chunks
            })
            
        except Exception as e:
            # Update resume status to failed
            resume.processing_status = 'failed'
            resume.error_message = str(e)
            resume.save()
            
            return JsonResponse({
                'error': f'Failed to process resume: {str(e)}'
            }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'error': f'Upload failed: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def start_cv_interview(request):
    """Start a new CV interview session"""
    try:
        data = json.loads(request.body)
        resume_id = data.get('resume_id')
        num_questions = data.get('num_questions', 5)
        
        if not resume_id:
            return JsonResponse({'error': 'Resume ID is required'}, status=400)
        
        # Get resume
        resume = get_object_or_404(Resume, id=resume_id, user=request.user)
        
        if resume.processing_status != 'completed':
            return JsonResponse({'error': 'Resume is not processed yet'}, status=400)
        
        # Create interview session
        session = CVInterviewSession.objects.create(
            user=request.user,
            resume=resume,
            total_questions=num_questions,
            max_score=num_questions * 20,  # 20 points per question
            stage='in_progress'
        )
        
        # Generate questions
        try:
            rag_service = CVRAGService()
            questions_data = rag_service.generate_multiple_questions(
                resume.vector_store_path,
                num_questions
            )
            
            # Save questions to database
            for idx, q_data in enumerate(questions_data, start=1):
                CVInterviewQuestion.objects.create(
                    session=session,
                    question_number=idx,
                    question_text=q_data['question'],
                    relevant_context=q_data['context']
                )
            
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'total_questions': num_questions,
                'message': 'Interview session started successfully'
            })
            
        except Exception as e:
            # Delete session if question generation fails
            session.delete()
            return JsonResponse({
                'error': f'Failed to generate questions: {str(e)}'
            }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to start interview: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_next_question(request, session_id):
    """Get the next question in the interview"""
    try:
        session = get_object_or_404(CVInterviewSession, id=session_id, user=request.user)
        
        if session.is_completed:
            return JsonResponse({'error': 'Interview already completed'}, status=400)
        
        # Get next unanswered question
        next_question = CVInterviewQuestion.objects.filter(
            session=session,
            user_answer__isnull=True
        ).order_by('question_number').first()
        
        if not next_question:
            # All questions answered, complete the session
            session.is_completed = True
            session.stage = 'completed'
            session.completed_at = timezone.now()
            session.save()
            
            return JsonResponse({
                'completed': True,
                'message': 'Interview completed',
                'session_id': session.id
            })
        
        # Update current question number
        session.current_question_number = next_question.question_number
        session.save()
        
        return JsonResponse({
            'success': True,
            'question_id': next_question.id,
            'question_number': next_question.question_number,
            'question_text': next_question.question_text,
            'total_questions': session.total_questions,
            'current_score': session.total_score,
            'max_score': session.max_score
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to get question: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def submit_answer(request):
    """Submit answer for a question"""
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        answer = data.get('answer')
        
        if not question_id or not answer:
            return JsonResponse({'error': 'Question ID and answer are required'}, status=400)
        
        # Get question
        question = get_object_or_404(CVInterviewQuestion, id=question_id)
        session = question.session
        
        # Verify ownership
        if session.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        if question.user_answer:
            return JsonResponse({'error': 'Question already answered'}, status=400)
        
        # Save answer
        question.user_answer = answer
        question.answered_at = timezone.now()
        
        # Evaluate answer using RAG service
        try:
            rag_service = CVRAGService()
            evaluation = rag_service.evaluate_answer(
                session.resume.vector_store_path,
                question.question_text,
                answer,
                question.relevant_context
            )
            
            # Save evaluation
            question.score = evaluation['score']
            question.feedback = evaluation['feedback']
            question.ai_evaluation = evaluation['evaluation_details']
            question.save()
            
            # Update session score
            session.total_score += evaluation['score']
            session.save()
            
            return JsonResponse({
                'success': True,
                'score': evaluation['score'],
                'max_score': question.max_score,
                'feedback': evaluation['feedback'],
                'total_score': session.total_score,
                'session_max_score': session.max_score
            })
            
        except Exception as e:
            # Save answer even if evaluation fails
            question.score = 0
            question.feedback = f"Evaluation failed: {str(e)}"
            question.save()
            
            return JsonResponse({
                'error': f'Failed to evaluate answer: {str(e)}'
            }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to submit answer: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_interview_results(request, session_id):
    """Get complete interview results"""
    try:
        session = get_object_or_404(CVInterviewSession, id=session_id, user=request.user)
        
        # Get all questions with answers
        questions = CVInterviewQuestion.objects.filter(session=session).order_by('question_number')
        
        questions_data = [{
            'question_number': q.question_number,
            'question': q.question_text,
            'answer': q.user_answer,
            'score': q.score,
            'max_score': q.max_score,
            'feedback': q.feedback,
            'score_percentage': q.get_score_percentage()
        } for q in questions]
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'is_completed': session.is_completed,
            'total_score': session.total_score,
            'max_score': session.max_score,
            'score_percentage': session.get_score_percentage(),
            'performance_grade': session.get_performance_grade(),
            'total_questions': session.total_questions,
            'answered_questions': questions.filter(user_answer__isnull=False).count(),
            'questions': questions_data,
            'created_at': session.created_at.strftime('%Y-%m-%d %H:%M'),
            'completed_at': session.completed_at.strftime('%Y-%m-%d %H:%M') if session.completed_at else None
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to get results: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_cv_interview_history(request):
    """Get all CV interview sessions for the user"""
    try:
        sessions = CVInterviewSession.objects.filter(user=request.user).order_by('-created_at')
        
        sessions_data = [{
            'session_id': s.id,
            'resume_name': s.resume.original_filename,
            'total_questions': s.total_questions,
            'answered_questions': s.questions.filter(user_answer__isnull=False).count(),
            'total_score': s.total_score,
            'max_score': s.max_score,
            'score_percentage': s.get_score_percentage(),
            'performance_grade': s.get_performance_grade(),
            'is_completed': s.is_completed,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'completed_at': s.completed_at.strftime('%Y-%m-%d %H:%M') if s.completed_at else None
        } for s in sessions]
        
        return JsonResponse({
            'success': True,
            'total_sessions': sessions.count(),
            'sessions': sessions_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to get history: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_resume(request, resume_id):
    """Delete a resume and its associated data"""
    try:
        resume = get_object_or_404(Resume, id=resume_id, user=request.user)
        
        # Delete file
        if resume.file:
            default_storage.delete(resume.file.name)
        
        # Delete vector store directory
        if resume.vector_store_path and os.path.exists(resume.vector_store_path):
            import shutil
            shutil.rmtree(resume.vector_store_path, ignore_errors=True)
        
        # Delete resume record (will cascade delete interview sessions)
        resume.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Resume deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to delete resume: {str(e)}'
        }, status=500)
