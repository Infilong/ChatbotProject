"""
Customer Session Management API
Handles frontend user session tracking for React app (localhost:3000)
"""

import logging
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions

from .models import UserSession

logger = logging.getLogger(__name__)



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  # Require authentication
def start_session(request):
    """
    Start a new customer session for frontend user
    Used when user visits React app (localhost:3000)
    """
    try:
        # Require authenticated user - no demo fallback
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        
        # Check if user already has an active session
        active_session = UserSession.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if active_session:
            # Update existing session
            active_session.started_at = timezone.now()  # Refresh start time
            active_session.save()
            
            response_data = {
                'session_id': active_session.session_id,
                'message': 'Existing session refreshed',
                'started_at': active_session.started_at,
                'user': user.username
            }
            logger.info(f"Refreshed existing Customer Session: {active_session.session_id} for user {user.username}")
        else:
            # Create new session
            session = UserSession.objects.create(
                user=user,
                session_id=str(uuid.uuid4()),
                is_active=True
            )
            
            response_data = {
                'session_id': session.session_id,
                'message': 'New session started',
                'started_at': session.started_at,
                'user': user.username
            }
            logger.info(f"Started new Customer Session: {session.session_id} for user {user.username}")
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error starting Customer Session: {e}")
        return Response(
            {'error': 'Failed to start session', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  # Require authentication
def update_session(request):
    """
    Update customer session activity
    Used when user sends messages or performs actions
    """
    session_id = request.data.get('session_id')
    if not session_id:
        return Response(
            {'error': 'session_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Require authenticated user - no demo fallback
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        
        # Get session
        session = UserSession.objects.filter(
            session_id=session_id,
            user=user,
            is_active=True
        ).first()
        
        if not session:
            return Response(
                {'error': 'Active session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update session activity (last_activity is automatically updated via auto_now=True)
        session.save()
        
        response_data = {
            'session_id': session.session_id,
            'message': 'Session activity updated',
            'last_activity': session.last_activity
        }
        
        logger.info(f"Updated Customer Session {session.session_id} - activity timestamp")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error updating Customer Session {session_id}: {e}")
        return Response(
            {'error': 'Failed to update session', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  # Require authentication
def end_session(request):
    """
    End customer session
    Used when user closes React app or leaves site
    """
    session_id = request.data.get('session_id')
    if not session_id:
        return Response(
            {'error': 'session_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Require authenticated user - no demo fallback
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        
        # Get session
        session = UserSession.objects.filter(
            session_id=session_id,
            user=user,
            is_active=True
        ).first()
        
        if not session:
            return Response(
                {'error': 'Active session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # End session
        session.end_session()
        
        # Calculate session duration
        duration = session.ended_at - session.started_at
        
        response_data = {
            'session_id': session.session_id,
            'message': 'Session ended',
            'started_at': session.started_at,
            'ended_at': session.ended_at,
            'last_activity': session.last_activity,
            'duration_minutes': duration.total_seconds() / 60
        }
        
        logger.info(f"Ended Customer Session {session.session_id} - Duration: {duration}")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error ending Customer Session {session_id}: {e}")
        return Response(
            {'error': 'Failed to end session', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])  # Require authentication
def session_status(request):
    """
    Get current session status
    Used to check if user has an active session
    """
    try:
        # Require authenticated user - no demo fallback
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        
        # Get active session
        active_session = UserSession.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if active_session:
            # Calculate session duration
            duration = timezone.now() - active_session.started_at
            
            response_data = {
                'has_active_session': True,
                'session_id': active_session.session_id,
                'started_at': active_session.started_at,
                'last_activity': active_session.last_activity,
                'duration_minutes': duration.total_seconds() / 60,
                'user': user.username
            }
        else:
            response_data = {
                'has_active_session': False,
                'user': user.username,
                'message': 'No active session found'
            }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return Response(
            {'error': 'Failed to get session status', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])  # Require authentication
def session_history(request):
    """
    Get user's session history
    Shows past sessions for analytics
    """
    try:
        # Require authenticated user - no demo fallback
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        
        # Get recent sessions (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        sessions = UserSession.objects.filter(
            user=user,
            started_at__gte=thirty_days_ago
        ).order_by('-started_at')[:20]  # Limit to 20 most recent
        
        sessions_data = []
        total_duration = 0
        
        for session in sessions:
            duration = 0
            if session.ended_at:
                duration = (session.ended_at - session.started_at).total_seconds() / 60
                total_duration += duration
            elif session.is_active:
                # Calculate current duration for active session
                duration = (timezone.now() - session.started_at).total_seconds() / 60
                total_duration += duration
            
            sessions_data.append({
                'session_id': session.session_id,
                'started_at': session.started_at,
                'ended_at': session.ended_at,
                'last_activity': session.last_activity,
                'is_active': session.is_active,
                'duration_minutes': round(duration, 2)
            })
        
        response_data = {
            'user': user.username,
            'total_sessions': len(sessions_data),
            'sessions': sessions_data,
            'summary': {
                'total_duration_minutes': round(total_duration, 2),
                'average_session_duration': round(total_duration / len(sessions_data), 2) if sessions_data else 0
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        return Response(
            {'error': 'Failed to get session history', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  # Require authentication
def cleanup_expired_sessions(request):
    """
    Clean up expired sessions
    Sessions are considered expired after 1 hour of inactivity
    """
    try:
        # Require authenticated user - no demo fallback
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        
        # Find expired sessions (active for more than 1 hour)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        expired_sessions = UserSession.objects.filter(
            user=user,
            is_active=True,
            started_at__lt=one_hour_ago
        )
        
        cleaned_count = 0
        for session in expired_sessions:
            session.end_session()
            cleaned_count += 1
        
        response_data = {
            'message': f'Cleaned up {cleaned_count} expired sessions',
            'cleaned_sessions': cleaned_count,
            'user': user.username
        }
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired Customer Sessions for user {user.username}")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}")
        return Response(
            {'error': 'Failed to cleanup sessions', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )