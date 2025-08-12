"""
Custom middleware for timezone handling in Django admin.
"""
import pytz
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class UserTimezoneMiddleware:
    """
    Middleware to automatically detect and set the user's timezone for Django admin.
    
    This middleware:
    1. Detects browser timezone via JavaScript on first admin access
    2. Stores user timezone preference in session
    3. Activates the correct timezone for each request
    4. Falls back to system timezone if detection fails
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only process timezone for authenticated admin users
        if request.user.is_authenticated and request.user.is_staff:
            # Get timezone from session or default to UTC
            user_timezone = request.session.get('django_timezone')
            
            if user_timezone:
                try:
                    # Activate the user's timezone
                    timezone.activate(pytz.timezone(user_timezone))
                    logger.debug(f"Activated timezone {user_timezone} for user {request.user.username}")
                except pytz.exceptions.UnknownTimeZoneError:
                    logger.warning(f"Unknown timezone {user_timezone} for user {request.user.username}, using UTC")
                    timezone.activate(pytz.UTC)
            else:
                # No timezone set yet - use UTC until JavaScript detection completes
                timezone.activate(pytz.UTC)
        
        response = self.get_response(request)
        
        # Deactivate timezone after request
        timezone.deactivate()
        
        return response


class TimezoneDetectionMiddleware:
    """
    Middleware to handle timezone detection API calls.
    
    Intercepts POST requests to /api/timezone/detect/ and stores
    the browser-detected timezone in the user's session.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle timezone detection API calls
        if (request.method == 'POST' and 
            request.path == '/api/timezone/detect/' and 
            request.user.is_authenticated):
            
            return self.handle_timezone_detection(request)
        
        return self.get_response(request)
    
    def handle_timezone_detection(self, request):
        """Handle browser timezone detection and storage."""
        try:
            import json
            
            # Parse the JSON body
            if hasattr(request, 'body'):
                data = json.loads(request.body.decode('utf-8'))
                detected_timezone = data.get('timezone')
                
                if detected_timezone:
                    # Validate the timezone
                    try:
                        pytz.timezone(detected_timezone)
                        
                        # Store in session
                        request.session['django_timezone'] = detected_timezone
                        request.session.save()
                        
                        logger.info(f"Timezone {detected_timezone} detected and saved for user {request.user.username}")
                        
                        return JsonResponse({
                            'success': True,
                            'timezone': detected_timezone,
                            'message': f'Timezone set to {detected_timezone}'
                        })
                        
                    except pytz.exceptions.UnknownTimeZoneError:
                        logger.warning(f"Invalid timezone {detected_timezone} detected for user {request.user.username}")
                        return JsonResponse({
                            'success': False,
                            'error': 'Invalid timezone detected'
                        })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'No timezone provided'
                    })
                    
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
            logger.error(f"Error processing timezone detection: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid request format'
            })
        
        return JsonResponse({
            'success': False,
            'error': 'Request processing failed'
        })