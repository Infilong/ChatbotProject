"""
REST API views for authentication application
"""

import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile
from .serializers import UserRegistrationSerializer, LoginSerializer

logger = logging.getLogger(__name__)


class RegisterAPIView(APIView):
    """
    User registration endpoint
    Creates new user account with profile
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Register a new user"""
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid registration data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            username = serializer.validated_data['username']
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            first_name = serializer.validated_data.get('first_name', '')
            last_name = serializer.validated_data.get('last_name', '')
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create user profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': f"{first_name} {last_name}".strip() or username
                }
            )
            
            # Generate JWT tokens for immediate login
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            logger.info(f"New user registered: {username}")
            
            return Response({
                'message': 'User registered successfully',
                'access': str(access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'display_name': profile.display_name
                }
            }, status=status.HTTP_201_CREATED)
            
        except IntegrityError:
            return Response(
                {'error': 'User with this information already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return Response(
                {'error': 'Registration failed', 'message': 'Please try again'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginAPIView(APIView):
    """
    API endpoint for user authentication
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Authenticate user and return token"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    # Login user
                    login(request, user)
                    
                    # Get or create token
                    token, created = Token.objects.get_or_create(user=user)
                    
                    return Response({
                        'success': True,
                        'message': 'Login successful',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'is_staff': user.is_staff,
                            'is_superuser': user.is_superuser,
                            'date_joined': user.date_joined.isoformat()
                        },
                        'token': token.key,
                        'login_time': timezone.now().isoformat()
                    })
                else:
                    return Response(
                        {'error': 'Account is disabled'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Invalid username or password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return Response(
                {'error': 'Login failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutAPIView(APIView):
    """
    API endpoint for user logout
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Logout user and invalidate token"""
        try:
            # Delete user's token
            try:
                token = Token.objects.get(user=request.user)
                token.delete()
            except Token.DoesNotExist:
                pass
            
            # Logout user
            logout(request)
            
            return Response({
                'success': True,
                'message': 'Logout successful',
                'logout_time': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response(
                {'error': 'Logout failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileAPIView(APIView):
    """
    API endpoint for user profile management
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current user profile"""
        try:
            user = request.user
            
            profile_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active
            }
            
            return Response(profile_data)
            
        except Exception as e:
            logger.error(f"Profile retrieval error: {e}")
            return Response(
                {'error': 'Failed to retrieve profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request):
        """Update user profile"""
        try:
            user = request.user
            
            # Update allowed fields
            allowed_fields = ['first_name', 'last_name', 'email']
            updated_fields = []
            
            for field in allowed_fields:
                if field in request.data:
                    setattr(user, field, request.data[field])
                    updated_fields.append(field)
            
            if updated_fields:
                user.save(update_fields=updated_fields)
            
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'updated_fields': updated_fields,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            })
            
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return Response(
                {'error': 'Failed to update profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """
    Change user password
    """
    try:
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            return Response(
                {'error': 'All password fields are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != confirm_password:
            return Response(
                {'error': 'New passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify current password
        user = request.user
        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Invalidate existing token and create new one
        try:
            token = Token.objects.get(user=user)
            token.delete()
        except Token.DoesNotExist:
            pass
        
        new_token = Token.objects.create(user=user)
        
        return Response({
            'success': True,
            'message': 'Password changed successfully',
            'token': new_token.key
        })
        
    except Exception as e:
        logger.error(f"Password change error: {e}")
        return Response(
            {'error': 'Failed to change password'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_token(request):
    """
    Validate authentication token
    """
    try:
        token_key = request.data.get('token')
        
        if not token_key:
            return Response(
                {'valid': False, 'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            token = Token.objects.get(key=token_key)
            user = token.user
            
            if user.is_active:
                return Response({
                    'valid': True,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'is_staff': user.is_staff,
                        'is_superuser': user.is_superuser
                    }
                })
            else:
                return Response({
                    'valid': False,
                    'error': 'User account is disabled'
                })
                
        except Token.DoesNotExist:
            return Response({
                'valid': False,
                'error': 'Invalid token'
            })
            
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return Response(
            {'valid': False, 'error': 'Token validation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def auth_status(request):
    """
    Get authentication status
    """
    try:
        if request.user.is_authenticated:
            return Response({
                'authenticated': True,
                'user': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email,
                    'is_staff': request.user.is_staff,
                    'is_superuser': request.user.is_superuser
                }
            })
        else:
            return Response({
                'authenticated': False,
                'message': 'Not authenticated'
            })
            
    except Exception as e:
        logger.error(f"Auth status error: {e}")
        return Response(
            {'error': 'Failed to check auth status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AuthHealthCheck(APIView):
    """
    Authentication service health check
    """
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Check authentication service health"""
        try:
            # Test database connection
            user_count = User.objects.count()
            
            # Test token system
            token_count = Token.objects.count()
            
            health_data = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'services': {
                    'database': 'connected',
                    'token_system': 'operational'
                },
                'stats': {
                    'total_users': user_count,
                    'active_tokens': token_count
                }
            }
            
            return Response(health_data)
            
        except Exception as e:
            logger.error(f"Auth health check failed: {e}")
            return Response(
                {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )