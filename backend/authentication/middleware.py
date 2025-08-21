"""
Session Tracking Middleware
"""

import logging
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from .session_models import UserSession, SessionActivity

logger = logging.getLogger(__name__)


class SessionTrackingMiddleware:
    """
    Middleware to automatically track user sessions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Track session before processing the request
        self.track_user_session(request)
        
        # Process the request
        response = self.get_response(request)
        
        return response

    def track_user_session(self, request):
        """Track user session activity"""
        
        # Skip tracking for anonymous users
        if not request.user or isinstance(request.user, AnonymousUser):
            return
        
        try:
            # Get or create user session
            session = UserSession.get_user_active_session(request.user)
            
            if not session:
                # Create new session
                session = self.create_new_session(request)
                logger.info(f"Created new session for user {request.user.username}: {session.session_id}")
            else:
                # Update existing session
                activity_type = self.get_activity_type(request)
                session.update_activity(activity_type=activity_type)
                
                # Log activity if it's significant
                if activity_type in ['chat', 'api', 'upload', 'admin']:
                    self.log_session_activity(session, request, activity_type)
        
        except Exception as e:
            logger.error(f"Error tracking session for user {request.user.username}: {e}")

    def create_new_session(self, request):
        """Create a new user session"""
        
        # Get client information
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
        device_type = self.detect_device_type(user_agent)
        
        # Create session
        session = UserSession.objects.create(
            user=request.user,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            last_activity_type='login'
        )
        
        # Log login activity
        SessionActivity.objects.create(
            session=session,
            activity_type='login',
            description=f'User logged in from {device_type}',
            metadata={
                'ip_address': ip_address,
                'user_agent': user_agent[:100]  # Store truncated version
            }
        )
        
        return session

    def get_activity_type(self, request):
        """Determine activity type based on request"""
        
        path = request.path.lower()
        method = request.method.upper()
        
        # Admin activities
        if '/admin/' in path:
            if method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                return 'admin'
            return 'view'
        
        # API activities
        if '/api/' in path:
            if 'chat' in path:
                return 'chat'
            elif 'upload' in path or method == 'POST':
                return 'api'
            return 'api'
        
        # File operations
        if any(keyword in path for keyword in ['upload', 'download', 'file']):
            if 'upload' in path:
                return 'upload'
            elif 'download' in path:
                return 'download'
            return 'view'
        
        # Default to view for GET requests, general for others
        return 'view' if method == 'GET' else 'general'

    def log_session_activity(self, session, request, activity_type):
        """Log detailed session activity"""
        
        try:
            description = f"{activity_type.title()} activity on {request.path}"
            
            # Create activity metadata
            metadata = {
                'path': request.path,
                'method': request.method,
                'timestamp': timezone.now().isoformat()
            }
            
            # Add specific metadata based on activity type
            if activity_type == 'chat':
                metadata['endpoint'] = 'chat_api'
            elif activity_type == 'admin':
                metadata['admin_action'] = request.path.split('/')[-2] if len(request.path.split('/')) > 2 else 'unknown'
            
            SessionActivity.objects.create(
                session=session,
                activity_type=activity_type,
                description=description[:200],  # Limit description length
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error logging session activity: {e}")

    def get_client_ip(self, request):
        """Get client IP address from request"""
        
        # Check for forwarded IP (behind proxy/load balancer)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        return ip

    def detect_device_type(self, user_agent):
        """Detect device type from user agent string"""
        
        if not user_agent:
            return 'unknown'
        
        user_agent = user_agent.lower()
        
        # Mobile devices
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'phone', 'tablet']
        if any(keyword in user_agent for keyword in mobile_keywords):
            if 'tablet' in user_agent or 'ipad' in user_agent:
                return 'tablet'
            return 'mobile'
        
        # Desktop browsers
        if any(browser in user_agent for browser in ['chrome', 'firefox', 'safari', 'edge', 'opera']):
            return 'desktop'
        
        # API clients or bots
        if any(keyword in user_agent for keyword in ['bot', 'crawler', 'spider', 'curl', 'postman']):
            return 'bot'
        
        return 'unknown'


class SessionCleanupMiddleware:
    """
    Middleware to periodically clean up expired sessions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cleanup_counter = 0

    def __call__(self, request):
        response = self.get_response(request)
        
        # Clean up expired sessions every 100 requests
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            self.cleanup_counter = 0
            self.cleanup_expired_sessions()
        
        return response

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        
        try:
            count = UserSession.cleanup_expired_sessions(timeout_minutes=60)  # 1 hour timeout
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")