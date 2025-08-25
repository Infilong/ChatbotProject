"""
Message Analysis Service
Production-ready message analysis with reliable database connections
Uses direct signal-based processing with proper async/sync handling
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from chat.models import Message
from .hybrid_analysis_service import hybrid_analysis_service

logger = logging.getLogger(__name__)


class MessageAnalysisService:
    """
    Production-ready message analysis service
    Processes messages directly in signal handlers with proper database handling
    """
    
    @classmethod
    async def analyze_message_now(cls, message: Message) -> Optional[Dict[str, Any]]:
        """
        Analyze a message immediately and save the results
        This method works reliably with Django's database connections
        """
        try:
            # Skip if already analyzed
            if message.message_analysis and message.message_analysis != {}:
                logger.debug(f"Message {message.uuid} already analyzed, skipping")
                return message.message_analysis
            
            # Only analyze user messages
            if message.sender_type != 'user':
                logger.debug(f"Message {message.uuid} is not a user message, skipping")
                return None
            
            logger.info(f"Analyzing message {message.uuid}: {message.content[:50]}...")
            
            # Run analysis using hybrid service
            analysis_result = await hybrid_analysis_service.analyze_message_hybrid(message)
            
            if analysis_result and 'error' not in analysis_result:
                # Add metadata but preserve the analysis_source from hybrid service
                # The hybrid service already sets proper source like "LangExtract Simple (gemini-2.5-flash)"
                additional_metadata = {
                    'service_handler': 'direct_analysis_service', 
                    'processed_at': timezone.now().isoformat(),
                    'message_uuid': str(message.uuid)
                }
                
                # Only add analysis_source if it's missing (shouldn't happen with hybrid service)
                if 'analysis_source' not in analysis_result:
                    additional_metadata['analysis_source'] = 'LangExtract (Unknown Model)'
                
                analysis_result.update(additional_metadata)
                
                logger.info(f"Analysis completed for message {message.uuid}, saving...")
                
                # Save using async-safe database operations
                @sync_to_async
                def save_analysis():
                    with transaction.atomic():
                        fresh_message = Message.objects.select_for_update().get(uuid=message.uuid)
                        fresh_message.message_analysis = analysis_result
                        fresh_message.save(update_fields=['message_analysis'])
                        return True
                
                @sync_to_async
                def verify_save():
                    verification = Message.objects.get(uuid=message.uuid)
                    return bool(verification.message_analysis and verification.message_analysis != {})
                
                # Execute save and verification
                await save_analysis()
                save_successful = await verify_save()
                
                if save_successful:
                    logger.info(f"✓ Successfully analyzed and saved message {message.uuid}")
                    return analysis_result
                else:
                    logger.error(f"✗ Save verification failed for message {message.uuid}")
                    return None
            else:
                logger.warning(f"Analysis failed for message {message.uuid}: {analysis_result}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing message {message.uuid}: {e}")
            return None
    
    @classmethod
    def analyze_message_sync(cls, message: Message) -> Optional[Dict[str, Any]]:
        """
        Synchronous wrapper for message analysis
        Used in Django signal handlers
        """
        try:
            # Create event loop for async analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(cls.analyze_message_now(message))
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error in sync message analysis for {message.uuid}: {e}")
            return None
    
    @classmethod
    def get_analysis_stats(cls) -> Dict[str, Any]:
        """Get current analysis statistics"""
        try:
            total_messages = Message.objects.filter(sender_type='user').count()
            analyzed_messages = Message.objects.filter(
                sender_type='user',
                message_analysis__isnull=False
            ).exclude(message_analysis={}).count()
            pending_messages = total_messages - analyzed_messages
            
            return {
                'total_user_messages': total_messages,
                'analyzed_messages': analyzed_messages,
                'pending_messages': pending_messages,
                'analysis_percentage': round((analyzed_messages / total_messages * 100) if total_messages > 0 else 0, 1),
                'service_type': 'direct_analysis'
            }
        except Exception as e:
            logger.error(f"Error getting analysis stats: {e}")
            return {
                'error': str(e),
                'service_type': 'direct_analysis'
            }


# Global service instance
message_analysis_service = MessageAnalysisService()