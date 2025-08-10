"""Database optimization indexes and query improvements"""

from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex, GistIndex


class DatabaseIndexOptimization:
    """Recommended database indexes for performance optimization"""
    
    @staticmethod
    def get_document_indexes():
        """Indexes for Document model performance"""
        return [
            # File hash index for duplicate detection (already exists in model)
            models.Index(fields=['file_hash'], name='documents_file_hash_idx'),
            
            # Category and active status for filtered queries
            models.Index(fields=['category', 'is_active'], name='documents_category_active_idx'),
            
            # Upload date for chronological queries
            models.Index(fields=['-created_at'], name='documents_created_desc_idx'),
            
            # User and date for admin queries
            models.Index(fields=['uploaded_by', '-created_at'], name='documents_user_date_idx'),
            
            # File type and size for analytics
            models.Index(fields=['file_type', 'file_size'], name='documents_type_size_idx'),
            
            # Reference count for popularity sorting
            models.Index(fields=['-reference_count'], name='documents_ref_count_idx'),
            
            # Effectiveness score for quality sorting
            models.Index(fields=['-effectiveness_score'], name='documents_effectiveness_idx'),
            
            # Full text search (if using PostgreSQL)
            # GinIndex(fields=['search_vector'], name='documents_search_gin_idx'),
        ]
    
    @staticmethod
    def get_conversation_indexes():
        """Indexes for Conversation model performance"""
        return [
            # User and date for conversation history
            models.Index(fields=['user', '-started_at'], name='conversations_user_date_idx'),
            
            # Status and date for active conversations
            models.Index(fields=['status', '-started_at'], name='conversations_status_date_idx'),
            
            # Satisfaction score for analytics
            models.Index(fields=['satisfaction_score'], name='conversations_satisfaction_idx'),
            
            # Session ID for session management
            models.Index(fields=['session_id'], name='conversations_session_idx'),
            
            # Updated date for recent activity
            models.Index(fields=['-updated_at'], name='conversations_updated_desc_idx'),
        ]
    
    @staticmethod
    def get_message_indexes():
        """Indexes for Message model performance"""
        return [
            # Conversation and timestamp for message history
            models.Index(fields=['conversation', 'timestamp'], name='messages_conv_time_idx'),
            
            # Sender type for bot/user filtering
            models.Index(fields=['sender', 'timestamp'], name='messages_sender_time_idx'),
            
            # Response time for performance analytics
            models.Index(fields=['response_time_seconds'], name='messages_response_time_idx'),
            
            # Issue category for analytics
            models.Index(fields=['issue_category'], name='messages_issue_category_idx'),
            
            # Token usage for cost tracking
            models.Index(fields=['tokens_used'], name='messages_tokens_idx'),
        ]
    
    @staticmethod
    def get_user_session_indexes():
        """Indexes for UserSession model performance"""
        return [
            # User and activity for session management
            models.Index(fields=['user', '-last_activity'], name='sessions_user_activity_idx'),
            
            # Session ID for unique identification
            models.Index(fields=['session_id'], name='sessions_session_id_idx'),
            
            # Active sessions filtering
            models.Index(fields=['is_active', '-last_activity'], name='sessions_active_idx'),
            
            # Device type for analytics
            models.Index(fields=['device_type'], name='sessions_device_idx'),
        ]
    
    @staticmethod
    def get_api_configuration_indexes():
        """Indexes for APIConfiguration model performance"""
        return [
            # Provider and active status for configuration lookups
            models.Index(fields=['provider', 'is_active'], name='api_config_provider_active_idx'),
            
            # Model name for specific model queries
            models.Index(fields=['model_name'], name='api_config_model_idx'),
            
            # Usage stats for monitoring
            models.Index(fields=['-usage_count'], name='api_config_usage_idx'),
        ]


class QueryOptimizations:
    """Common query patterns and optimizations"""
    
    @staticmethod
    def get_active_documents_query():
        """Optimized query for active documents with select_related"""
        from documents.models import Document
        return Document.objects.select_related('uploaded_by').filter(
            is_active=True
        ).order_by('-created_at')
    
    @staticmethod
    def get_user_conversations_query(user, limit=50):
        """Optimized query for user conversations with prefetch"""
        from chat.models import Conversation
        return Conversation.objects.select_related('user').prefetch_related(
            'messages'
        ).filter(
            user=user
        ).order_by('-updated_at')[:limit]
    
    @staticmethod
    def get_document_analytics_query():
        """Optimized query for document analytics"""
        from documents.models import Document
        from django.db.models import Avg, Count, Sum
        
        return Document.objects.filter(is_active=True).aggregate(
            total_count=Count('id'),
            avg_file_size=Avg('file_size'),
            total_references=Sum('reference_count'),
            avg_effectiveness=Avg('effectiveness_score')
        )
    
    @staticmethod
    def get_conversation_metrics_query(days=7):
        """Optimized query for conversation metrics"""
        from chat.models import Conversation, Message
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        return {
            'conversations': Conversation.objects.filter(
                started_at__gte=cutoff_date
            ).count(),
            'messages': Message.objects.filter(
                timestamp__gte=cutoff_date
            ).count(),
            'avg_satisfaction': Conversation.objects.filter(
                satisfaction_score__isnull=False,
                started_at__gte=cutoff_date
            ).aggregate(
                avg_score=Avg('satisfaction_score')
            )['avg_score']
        }


# Migration to create indexes
def create_database_indexes(apps, schema_editor):
    """Create database indexes for performance optimization"""
    
    # Get models
    Document = apps.get_model('documents', 'Document')
    
    # Create indexes using raw SQL for complex indexes
    with schema_editor.connection.cursor() as cursor:
        
        # Document indexes
        cursor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS documents_file_hash_unique_idx 
            ON documents_document (file_hash) WHERE file_hash != '';
        """)
        
        cursor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS documents_search_text_idx 
            ON documents_document USING gin(to_tsvector('english', 
                coalesce(name, '') || ' ' || 
                coalesce(description, '') || ' ' || 
                coalesce(extracted_text, '')
            ));
        """)
        
        # Conversation analytics indexes  
        cursor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS conversations_date_trunc_idx
            ON chat_conversation (date_trunc('day', started_at));
        """)


def reverse_database_indexes(apps, schema_editor):
    """Remove database indexes"""
    
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS documents_file_hash_unique_idx;")
        cursor.execute("DROP INDEX IF EXISTS documents_search_text_idx;")
        cursor.execute("DROP INDEX IF EXISTS conversations_date_trunc_idx;")


# Django migration class
class Migration(migrations.Migration):
    """Database index optimization migration"""
    
    dependencies = [
        ('documents', '0007_add_knowledge_base_fields_simple'),
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_database_indexes,
            reverse_database_indexes
        ),
    ]