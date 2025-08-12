"""
Serializers for User Authentication System
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, UserPreferences
import re


class UserRegistrationSerializer(serializers.Serializer):
    """Serializer for user registration"""
    username = serializers.CharField(
        max_length=150,
        min_length=3,
        required=True,
        help_text=_("Username (3-150 characters)")
    )
    email = serializers.EmailField(
        required=True,
        help_text=_("Valid email address")
    )
    password = serializers.CharField(
        min_length=8,
        required=True,
        write_only=True,
        help_text=_("Password (minimum 8 characters)")
    )
    password_confirm = serializers.CharField(
        min_length=8,
        required=True,
        write_only=True,
        help_text=_("Confirm password")
    )
    first_name = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        help_text=_("First name")
    )
    last_name = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        help_text=_("Last name")
    )

    def validate_username(self, value):
        """Validate username format"""
        if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
            raise serializers.ValidationError(
                _("Username can only contain letters, numbers, dots, hyphens and underscores")
            )
        return value

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("Email is already registered"))
        return value

    def validate(self, data):
        """Validate password confirmation and strength"""
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': _("Passwords do not match")
            })
        
        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })
        
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField(
        required=True,
        help_text=_("Username or email address")
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        help_text=_("Password")
    )


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    display_name = serializers.ReadOnlyField()
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'display_name', 'role', 'phone_number', 'company', 'job_title',
            'preferred_language', 'email_notifications', 'total_conversations',
            'total_messages_sent', 'average_satisfaction', 'last_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'display_name',
            'total_conversations', 'total_messages_sent', 'average_satisfaction',
            'last_active', 'created_at', 'updated_at'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'profile']
        read_only_fields = ['id', 'username']


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user preferences"""
    
    class Meta:
        model = UserPreferences
        fields = [
            'chat_theme', 'show_timestamps', 'enable_sound_notifications',
            'preferred_response_style', 'enable_proactive_suggestions',
            'allow_conversation_analysis', 'share_data_for_improvements',
            'updated_at'
        ]
        read_only_fields = ['updated_at']


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        help_text=_("Current password")
    )
    new_password = serializers.CharField(
        min_length=8,
        required=True,
        write_only=True,
        help_text=_("New password (minimum 8 characters)")
    )
    new_password_confirm = serializers.CharField(
        min_length=8,
        required=True,
        write_only=True,
        help_text=_("Confirm new password")
    )

    def validate(self, data):
        """Validate password confirmation and strength"""
        new_password = data.get('new_password')
        new_password_confirm = data.get('new_password_confirm')
        
        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                'new_password_confirm': _("New passwords do not match")
            })
        
        # Validate password strength
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return data