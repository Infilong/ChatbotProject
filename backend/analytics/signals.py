"""
Django signals for automatic analytics summary generation
Triggers when conversations are analyzed with LangExtract
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from chat.models import Conversation
from .services import automatic_analytics_service

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Conversation)
def track_langextract_analysis_changes(sender, instance, **kwargs):
    """Track if langextract_analysis field is being updated"""
    if instance.pk:
        try:
            # Get the previous state
            old_instance = Conversation.objects.get(pk=instance.pk)
            instance._previous_analysis = old_instance.langextract_analysis
        except Conversation.DoesNotExist:
            instance._previous_analysis = {}
    else:
        instance._previous_analysis = {}


@receiver(post_save, sender=Conversation)
def auto_generate_analytics_summary(sender, instance, created, **kwargs):
    """Automatically generate analytics summary when conversation analysis is updated"""
    
    # Skip if this is a new conversation without analysis
    if created and not instance.langextract_analysis:
        return
    
    # Check if langextract_analysis was updated
    previous_analysis = getattr(instance, '_previous_analysis', {})
    current_analysis = instance.langextract_analysis or {}
    
    # If analysis data changed (added or updated)
    if current_analysis != previous_analysis and current_analysis:
        logger.info(f"LangExtract analysis updated for conversation {instance.uuid}, triggering analytics summary")
        
        try:
            # Trigger automatic analytics summary generation
            summary = automatic_analytics_service.trigger_summary_update(instance)
            
            if summary:
                logger.info(f"Analytics summary updated for date {summary.date}: "
                          f"{summary.total_conversations} conversations, "
                          f"{summary.average_satisfaction} avg satisfaction")
            else:
                logger.warning(f"Failed to generate analytics summary for conversation {instance.uuid}")
                
        except Exception as e:
            logger.error(f"Error generating analytics summary for conversation {instance.uuid}: {e}")
    
    # Clean up the tracking attribute
    if hasattr(instance, '_previous_analysis'):
        delattr(instance, '_previous_analysis')


@receiver(post_save, sender=Conversation)
def ensure_analytics_summaries_exist(sender, instance, created, **kwargs):
    """Ensure analytics summaries exist for all dates when new analyzed conversations are saved"""
    
    # Only process if conversation has analysis data
    if not instance.langextract_analysis:
        return
    
    try:
        # Generate any missing summaries in the background
        # This catches cases where signals might have been missed
        missing_count = automatic_analytics_service.generate_missing_summaries()
        
        if missing_count > 0:
            logger.info(f"Generated {missing_count} missing analytics summaries")
            
    except Exception as e:
        logger.error(f"Error ensuring analytics summaries exist: {e}")