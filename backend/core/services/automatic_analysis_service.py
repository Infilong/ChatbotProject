"""
Automatic Analysis Service
Handles automatic triggering of LangExtract analysis for conversations
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from chat.models import Conversation, Message
from .langextract_service import langextract_service

logger = logging.getLogger(__name__)


class AutomaticAnalysisService:
    """Service for automatically triggering conversation analysis"""
    
    # Configuration
    MIN_MESSAGES_FOR_ANALYSIS = 3  # Minimum messages before analysis
    ANALYSIS_DELAY_MINUTES = 0.5  # Wait 0.5 minutes after last message before analysis
    MAX_ANALYSIS_DELAY_HOURS = 24  # Force analysis after 24 hours regardless
    
    @classmethod
    async def trigger_analysis_if_needed(cls, conversation: Conversation) -> Optional[Dict[str, Any]]:
        """
        Check if conversation needs analysis and trigger if appropriate
        
        Args:
            conversation: Conversation to potentially analyze
            
        Returns:
            Analysis results if analysis was triggered, None otherwise
        """
        try:
            # Check if conversation meets criteria for analysis
            should_analyze, reason = await cls._should_analyze_conversation(conversation)
            
            if not should_analyze:
                logger.debug(f"Skipping analysis for conversation {conversation.uuid}: {reason}")
                return None
            
            logger.info(f"Triggering automatic analysis for conversation {conversation.uuid}: {reason}")
            
            # Run the analysis
            analysis_result = await langextract_service.analyze_full_conversation(conversation)
            
            # Mark that analysis has been completed
            await cls._mark_analysis_completed(conversation, analysis_result)
            
            logger.info(f"Automatic analysis completed for conversation {conversation.uuid}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed to trigger automatic analysis for conversation {conversation.uuid}: {e}")
            return None
    
    @classmethod
    async def _should_analyze_conversation(cls, conversation: Conversation) -> tuple[bool, str]:
        """
        Determine if a conversation should be analyzed
        
        Args:
            conversation: Conversation to check
            
        Returns:
            Tuple of (should_analyze, reason)
        """
        # Convert to async-safe operations
        @sync_to_async
        def get_conversation_data():
            conversation.refresh_from_db()
            messages_count = conversation.messages.count()
            last_message = conversation.messages.order_by('-timestamp').first()
            has_analysis = bool(conversation.langextract_analysis)
            return messages_count, last_message, has_analysis
        
        try:
            messages_count, last_message, has_analysis = await get_conversation_data()
            
            # Skip if already analyzed
            if has_analysis:
                return False, "Already analyzed"
            
            # Skip if too few messages
            if messages_count < cls.MIN_MESSAGES_FOR_ANALYSIS:
                return False, f"Only {messages_count} messages (minimum {cls.MIN_MESSAGES_FOR_ANALYSIS})"
            
            # Skip if no messages found
            if not last_message:
                return False, "No messages found"
            
            # Calculate time since last message
            time_since_last = timezone.now() - last_message.timestamp
            
            # Force analysis if conversation is very old
            if time_since_last > timedelta(hours=cls.MAX_ANALYSIS_DELAY_HOURS):
                return True, f"Conversation inactive for {time_since_last} (forcing analysis)"
            
            # Analyze if conversation seems complete (inactive for delay period)
            if time_since_last > timedelta(minutes=cls.ANALYSIS_DELAY_MINUTES):
                return True, f"Conversation inactive for {time_since_last} (likely complete)"
            
            # Don't analyze yet - conversation might still be active
            return False, f"Too recent (last message {time_since_last} ago)"
            
        except Exception as e:
            logger.error(f"Error checking conversation analysis criteria: {e}")
            return False, f"Error checking criteria: {e}"
    
    @classmethod
    async def _mark_analysis_completed(cls, conversation: Conversation, analysis_result: Dict[str, Any]) -> None:
        """
        Mark that analysis has been completed for a conversation
        
        Args:
            conversation: Conversation that was analyzed
            analysis_result: Results of the analysis
        """
        try:
            @sync_to_async
            def update_conversation():
                with transaction.atomic():
                    conversation.refresh_from_db()
                    
                    # Store analysis results if not already stored by langextract_service
                    if not conversation.langextract_analysis:
                        conversation.langextract_analysis = analysis_result
                    
                    # Add metadata about automatic analysis
                    if 'metadata' not in conversation.langextract_analysis:
                        conversation.langextract_analysis['metadata'] = {}
                    
                    conversation.langextract_analysis['metadata'].update({
                        'automatic_analysis': True,
                        'analysis_triggered_at': timezone.now().isoformat(),
                        'analysis_trigger_reason': 'Automatic analysis after conversation completion'
                    })
                    
                    conversation.save(update_fields=['langextract_analysis'])
            
            await update_conversation()
            
        except Exception as e:
            logger.error(f"Failed to mark analysis as completed: {e}")
    
    @classmethod
    async def force_analysis(cls, conversation_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Force analysis of a specific conversation regardless of criteria
        
        Args:
            conversation_uuid: UUID of conversation to analyze
            
        Returns:
            Analysis results if successful, None otherwise
        """
        try:
            @sync_to_async
            def get_conversation():
                return Conversation.objects.get(uuid=conversation_uuid)
            
            conversation = await get_conversation()
            
            logger.info(f"Forcing analysis for conversation {conversation_uuid}")
            
            # Run the analysis
            analysis_result = await langextract_service.analyze_full_conversation(conversation)
            
            # Mark as manually triggered
            await cls._mark_analysis_completed(conversation, analysis_result)
            
            # Update metadata to indicate manual trigger
            @sync_to_async
            def update_metadata():
                conversation.refresh_from_db()
                if 'metadata' not in conversation.langextract_analysis:
                    conversation.langextract_analysis['metadata'] = {}
                conversation.langextract_analysis['metadata'].update({
                    'manual_analysis': True,
                    'forced_analysis': True
                })
                conversation.save(update_fields=['langextract_analysis'])
            
            await update_metadata()
            
            logger.info(f"Forced analysis completed for conversation {conversation_uuid}")
            return analysis_result
            
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {conversation_uuid} not found for forced analysis")
            return None
        except Exception as e:
            logger.error(f"Failed to force analysis for conversation {conversation_uuid}: {e}")
            return None
    
    @classmethod
    async def analyze_pending_conversations(cls) -> Dict[str, Any]:
        """
        Find and analyze all conversations that meet analysis criteria
        
        Returns:
            Summary of analysis operations
        """
        try:
            @sync_to_async
            def get_pending_conversations():
                # Get conversations that haven't been analyzed yet
                return list(Conversation.objects.filter(
                    langextract_analysis__isnull=True
                ).prefetch_related('messages'))
            
            conversations = await get_pending_conversations()
            
            results = {
                'total_conversations': len(conversations),
                'analyzed_count': 0,
                'skipped_count': 0,
                'error_count': 0,
                'analysis_results': []
            }
            
            for conversation in conversations:
                try:
                    analysis_result = await cls.trigger_analysis_if_needed(conversation)
                    
                    if analysis_result:
                        results['analyzed_count'] += 1
                        results['analysis_results'].append({
                            'conversation_id': str(conversation.uuid),
                            'status': 'success',
                            'message_count': conversation.total_messages
                        })
                    else:
                        results['skipped_count'] += 1
                        
                except Exception as e:
                    results['error_count'] += 1
                    logger.error(f"Error analyzing conversation {conversation.uuid}: {e}")
                    results['analysis_results'].append({
                        'conversation_id': str(conversation.uuid),
                        'status': 'error',
                        'error': str(e)
                    })
            
            logger.info(f"Batch analysis completed: {results['analyzed_count']} analyzed, "
                       f"{results['skipped_count']} skipped, {results['error_count']} errors")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to analyze pending conversations: {e}")
            return {
                'total_conversations': 0,
                'analyzed_count': 0,
                'skipped_count': 0,
                'error_count': 1,
                'error': str(e)
            }


# Global service instance
automatic_analysis_service = AutomaticAnalysisService()