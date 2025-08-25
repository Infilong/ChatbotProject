"""
Django signals for automatic conversation analysis
"""

import logging
import traceback
import threading
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Message, Conversation

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Conversation)
def debug_conversation_pre_save(sender, instance, **kwargs):
    """Debug signal to catch conversation creation before save"""
    if instance.pk is None:  # New conversation
        print(f"*** SIGNAL PRE_SAVE: Conversation about to be created ***")
        print(f"User: {instance.user.username} (ID: {instance.user.id})")
        print(f"Thread: {threading.current_thread().name}")
        print(f"Stack trace (last 8 frames):")
        for i, line in enumerate(traceback.format_stack()[-8:]):
            print(f"  [{i}] {line.strip()}")
        print(f"*** END SIGNAL PRE_SAVE ***")

@receiver(post_save, sender=Conversation)
def debug_conversation_post_save(sender, instance, created, **kwargs):
    """Debug signal to catch conversation creation after save"""
    if created:
        print(f"*** SIGNAL POST_SAVE: Conversation was created ***")
        print(f"User: {instance.user.username} (ID: {instance.user.id})")
        print(f"UUID: {instance.uuid}")
        print(f"Thread: {threading.current_thread().name}")
        print(f"*** END SIGNAL POST_SAVE ***")


@receiver(post_save, sender=Message)
def message_saved_trigger_analysis(sender, instance, created, **kwargs):
    """
    Signal handler triggered when a message is saved
    Uses async queuing to prevent database locks during concurrent analysis
    Triggers message-level analysis for user messages immediately
    Also checks if the conversation should be analyzed automatically
    """
    if not created:
        # Only process new messages, not updates
        return
    
    try:
        # Use threading to avoid blocking the main request
        import threading
        import time
        from django.db import transaction
        
        def async_analysis_handler():
            """Run analysis in a separate thread with proper database handling"""
            try:
                # Small delay to allow the main transaction to complete first
                time.sleep(0.1)
                
                # Refresh instance from database to get latest state
                with transaction.atomic():
                    instance.refresh_from_db()
                    conversation = instance.conversation
                    conversation.refresh_from_db()
                    
                    _perform_analysis_tasks(instance, conversation)
                    
            except Exception as e:
                logger.error(f"Async analysis handler failed: {e}")
        
        # Start analysis in background thread
        analysis_thread = threading.Thread(
            target=async_analysis_handler,
            name=f"analysis-{instance.uuid}",
            daemon=True
        )
        analysis_thread.start()
        
    except Exception as e:
        logger.error(f"Failed to start async analysis: {e}")


def _perform_analysis_tasks(instance, conversation):
    """Perform the actual analysis tasks in a thread-safe manner"""
    try:
        
        # 1. MESSAGE-LEVEL ANALYSIS (direct processing to ensure reliability)
        if instance.sender_type == 'user':
            logger.debug(f"Starting direct analysis for message {instance.uuid}")
            
            try:
                from core.services.message_analysis_service import message_analysis_service
                
                # Analyze message directly (more reliable than background workers)
                result = message_analysis_service.analyze_message_sync(instance)
                
                if result:
                    logger.info(f"✓ Message {instance.uuid} analyzed successfully")
                else:
                    logger.warning(f"✗ Message {instance.uuid} analysis failed or skipped")
                    
            except Exception as e:
                logger.error(f"Failed to analyze message {instance.uuid}: {e}")
        
        # 2. CONVERSATION-LEVEL ANALYSIS (simplified to prevent locks)
        message_count = conversation.total_messages
        has_analysis = bool(conversation.langextract_analysis and conversation.langextract_analysis != {})
        
        logger.debug(f"Message saved for conversation {conversation.uuid}: "
                    f"{message_count} messages, analyzed: {has_analysis}")
        
        # Trigger conversation analysis for conversations with enough messages
        # Only run analysis if we're processing a user message to avoid double-triggering
        if (message_count >= 3 and not has_analysis and 
            instance.sender_type == 'user'):
            
            logger.info(f"Triggering conversation analysis for {conversation.uuid} "
                       f"({message_count} messages)")
            
            # Run analysis directly but with database lock protection
            try:
                from core.services.langextract_service import langextract_service
                import asyncio
                
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Run the analysis
                    result = loop.run_until_complete(
                        langextract_service.analyze_full_conversation(conversation)
                    )
                    
                    if result:
                        logger.info(f"Conversation analysis completed for {conversation.uuid}")
                    else:
                        logger.warning(f"Conversation analysis returned no results for {conversation.uuid}")
                        
                except Exception as analysis_error:
                    logger.error(f"Conversation analysis failed for {conversation.uuid}: {analysis_error}")
                    
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"Failed to setup analysis for conversation {conversation.uuid}: {e}")
        
        logger.debug(f"Analysis tasks completed for message {instance.uuid}")
        
    except Exception as e:
        logger.error(f"Error in analysis tasks for message {instance.uuid}: {e}")
        # Don't re-raise to avoid breaking the message save operation


@receiver(post_save, sender=Conversation)
def conversation_updated_check_analysis(sender, instance, created, **kwargs):
    """
    Signal handler for when conversation is updated
    This can trigger analysis for conversations that become inactive
    """
    if created:
        # Don't analyze newly created conversations
        return
    
    try:
        # Check if conversation might be ready for analysis
        if not instance.langextract_analysis and instance.total_messages >= 3:
            # Check if conversation has been inactive for a while
            last_message = instance.messages.order_by('-timestamp').first()
            if last_message:
                time_since_last = timezone.now() - last_message.timestamp
                
                # If inactive for more than 5 minutes, it might be ready for analysis
                if time_since_last > timedelta(minutes=5):
                    logger.info(f"Conversation {instance.uuid} appears inactive for {time_since_last} "
                              f"and ready for analysis")
                    
                    # Schedule analysis through the automatic analysis service
                    from core.services.automatic_analysis_service import automatic_analysis_service
                    import asyncio
                    import threading
                    
                    def run_analysis_check():
                        """Run analysis check in background thread"""
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            result = loop.run_until_complete(
                                automatic_analysis_service.trigger_analysis_if_needed(instance)
                            )
                            
                            if result:
                                logger.info(f"Triggered automatic analysis for conversation {instance.uuid}")
                            
                            loop.close()
                            
                        except Exception as e:
                            logger.error(f"Error in background analysis check: {e}")
                    
                    # Start background check
                    thread = threading.Thread(target=run_analysis_check, daemon=True)
                    thread.start()
        
    except Exception as e:
        logger.warning(f"Error in conversation_updated_check_analysis signal: {e}")


# Global dictionaries to track retry timers
_message_retry_timers = {}
_conversation_retry_timers = {}


def start_message_analysis_retry_monitor(message_instance):
    """
    Start a retry monitor for message analysis that checks every 30 seconds
    and attempts to analyze the message if it's still unanalyzed (LLM-only)
    """
    message_uuid = str(message_instance.uuid)
    
    # Don't start multiple timers for the same message
    if message_uuid in _message_retry_timers:
        return
    
    import threading
    import time
    
    def retry_analysis_monitor():
        """Monitor function that runs every 30 seconds to check and retry LLM analysis"""
        max_retries = 40  # Maximum 40 retries (20 minutes total)
        retry_count = 0
        
        logger.info(f"Starting LLM-only analysis retry monitor for message {message_uuid}")
        
        while retry_count < max_retries:
            try:
                # Wait 30 seconds before checking
                time.sleep(30)
                retry_count += 1
                
                # Check if message still exists and needs analysis
                try:
                    from django.db import connections
                    connections.close_all()  # Close stale connections
                    
                    message = Message.objects.get(uuid=message_uuid)
                    
                    # Check if message now has analysis
                    if message.message_analysis and message.message_analysis != {}:
                        logger.info(f"Message {message_uuid} analysis completed successfully (retry {retry_count})")
                        break
                    
                    # Message still needs analysis - attempt retry
                    logger.info(f"Message {message_uuid} still unanalyzed, attempting retry {retry_count}/{max_retries}")
                    
                    # Attempt analysis again
                    import asyncio
                    from core.services.hybrid_analysis_service import hybrid_analysis_service
                    from django.db import transaction
                    
                    # Create new event loop for this retry
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        with transaction.atomic():
                            # Re-fetch message with lock
                            fresh_message = Message.objects.select_for_update().get(uuid=message_uuid)
                            
                            # Double-check it still needs analysis
                            if not fresh_message.message_analysis or fresh_message.message_analysis == {}:
                                # Analyze this specific message using hybrid approach
                                analysis_result = loop.run_until_complete(
                                    hybrid_analysis_service.analyze_message_hybrid(fresh_message)
                                )
                                
                                if analysis_result and 'error' not in analysis_result:
                                    # Add retry information to the analysis
                                    analysis_result.update({
                                        "retry_count": retry_count,
                                        "retry_successful": True,
                                        "retry_timestamp": timezone.now().isoformat()
                                    })
                                    
                                    # Save analysis to message
                                    fresh_message.message_analysis = analysis_result
                                    fresh_message.save(update_fields=['message_analysis'])
                                    
                                    # Log success
                                    analysis_source = analysis_result.get('analysis_source', 'Unknown')
                                    logger.info(f"Message {message_uuid} retry analysis successful using {analysis_source} (attempt {retry_count})")
                                    
                                    # TRIGGER AUTOMATIC SUMMARY CHECK AFTER RETRY SUCCESS
                                    importance_level = analysis_result.get('importance_level', {}).get('level', 'low')
                                    if importance_level in ['critical', 'high']:
                                        logger.info(f"Retry analysis complete - checking summary trigger for {importance_level} message: {message_uuid}")
                                        
                                        def trigger_summary_check_retry():
                                            """Trigger summary check after retry analysis completion"""
                                            try:
                                                import asyncio
                                                import time
                                                from django.db import connections
                                                from chat.services.automatic_summary_service import AutomaticSummaryService
                                                
                                                # Small delay
                                                time.sleep(1)
                                                
                                                # Close database connections for threading
                                                connections.close_all()
                                                
                                                # Create new event loop
                                                loop = asyncio.new_event_loop()
                                                asyncio.set_event_loop(loop)
                                                
                                                try:
                                                    # Check and generate summary if conditions are met
                                                    summary = loop.run_until_complete(
                                                        AutomaticSummaryService.check_and_generate_summary()
                                                    )
                                                    
                                                    if summary:
                                                        logger.info(f"✅ AUTOMATIC SUMMARY GENERATED by retry message {message_uuid}: {summary.uuid}")
                                                    else:
                                                        logger.debug(f"No summary triggered by retry {message_uuid}")
                                                        
                                                finally:
                                                    loop.close()
                                                    
                                            except Exception as e:
                                                logger.error(f"Error in retry summary trigger: {e}")
                                        
                                        # Start summary check in background thread
                                        import threading
                                        summary_thread = threading.Thread(target=trigger_summary_check_retry, daemon=True)
                                        summary_thread.start()
                                    
                                    break
                                else:
                                    logger.warning(f"Message {message_uuid} retry analysis failed (attempt {retry_count}): {analysis_result.get('error', 'Unknown error')}")
                            else:
                                logger.info(f"Message {message_uuid} was analyzed by another process during retry {retry_count}")
                                break
                                
                    finally:
                        loop.close()
                        
                except Message.DoesNotExist:
                    logger.info(f"Message {message_uuid} no longer exists, stopping retry monitor")
                    break
                    
            except Exception as e:
                logger.error(f"Error in retry analysis monitor for {message_uuid} (attempt {retry_count}): {e}")
                
        # Clean up - remove from retry timers
        if message_uuid in _message_retry_timers:
            del _message_retry_timers[message_uuid]
            
        if retry_count >= max_retries:
            logger.warning(f"Message {message_uuid} retry analysis gave up after {max_retries} attempts")
        else:
            logger.info(f"Message {message_uuid} retry monitor completed successfully")
    
    # Start the retry monitor in a background thread
    retry_thread = threading.Thread(target=retry_analysis_monitor, daemon=True)
    retry_thread.start()
    
    # Track this timer
    _message_retry_timers[message_uuid] = retry_thread


def stop_message_analysis_retry_monitor(message_uuid):
    """
    Stop the retry monitor for a specific message (if needed)
    """
    if message_uuid in _message_retry_timers:
        logger.info(f"Stopping retry monitor for message {message_uuid}")
        del _message_retry_timers[message_uuid]


def start_conversation_analysis_retry_monitor(conversation_instance):
    """
    Start a retry monitor for conversation analysis that checks every 30 seconds
    and attempts to analyze the conversation if it's still unanalyzed (LLM-only)
    """
    conversation_uuid = str(conversation_instance.uuid)
    
    # Don't start multiple timers for the same conversation
    if conversation_uuid in _conversation_retry_timers:
        return
    
    import threading
    import time
    
    def retry_conversation_analysis_monitor():
        """Monitor function that runs every 30 seconds to check and retry LLM conversation analysis"""
        max_retries = 40  # Maximum 40 retries (20 minutes total)
        retry_count = 0
        
        logger.info(f"Starting LLM-only conversation analysis retry monitor for conversation {conversation_uuid}")
        
        while retry_count < max_retries:
            try:
                # Wait 30 seconds before checking
                time.sleep(30)
                retry_count += 1
                
                # Check if conversation still exists and needs analysis
                try:
                    from django.db import connections
                    connections.close_all()  # Close stale connections
                    
                    conversation = Conversation.objects.get(uuid=conversation_uuid)
                    
                    # Check if conversation now has analysis
                    if conversation.langextract_analysis and conversation.langextract_analysis != {}:
                        logger.info(f"Conversation {conversation_uuid} analysis completed successfully (retry {retry_count})")
                        break
                    
                    # Conversation still needs analysis - attempt retry
                    logger.info(f"Conversation {conversation_uuid} still unanalyzed, attempting retry {retry_count}/{max_retries}")
                    
                    # Attempt conversation analysis again
                    import asyncio
                    from core.services.hybrid_analysis_service import hybrid_analysis_service
                    from django.db import transaction
                    
                    # Create new event loop for this retry
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        with transaction.atomic():
                            # Re-fetch conversation with lock
                            fresh_conversation = Conversation.objects.select_for_update().get(uuid=conversation_uuid)
                            
                            # Double-check it still needs analysis
                            if not fresh_conversation.langextract_analysis or fresh_conversation.langextract_analysis == {}:
                                # Analyze this conversation using hybrid approach
                                analysis_result = loop.run_until_complete(
                                    hybrid_analysis_service.analyze_conversation_hybrid(fresh_conversation)
                                )
                                
                                if analysis_result and 'error' not in analysis_result:
                                    # Add retry information to the analysis
                                    analysis_result.update({
                                        "retry_count": retry_count,
                                        "retry_successful": True,
                                        "retry_timestamp": timezone.now().isoformat()
                                    })
                                    
                                    # Save analysis to conversation
                                    fresh_conversation.langextract_analysis = analysis_result
                                    fresh_conversation.save(update_fields=['langextract_analysis'])
                                    
                                    # Log success
                                    analysis_source = analysis_result.get('analysis_source', 'Unknown')
                                    logger.info(f"Conversation {conversation_uuid} retry analysis successful using {analysis_source} (attempt {retry_count})")
                                    break
                                else:
                                    logger.warning(f"Conversation {conversation_uuid} retry analysis failed (attempt {retry_count}): {analysis_result.get('error', 'Unknown error')}")
                            else:
                                logger.info(f"Conversation {conversation_uuid} was analyzed by another process during retry {retry_count}")
                                break
                                
                    finally:
                        loop.close()
                        
                except Conversation.DoesNotExist:
                    logger.info(f"Conversation {conversation_uuid} no longer exists, stopping retry monitor")
                    break
                    
            except Exception as e:
                logger.error(f"Error in conversation retry analysis monitor for {conversation_uuid} (attempt {retry_count}): {e}")
                
        # Clean up - remove from retry timers
        if conversation_uuid in _conversation_retry_timers:
            del _conversation_retry_timers[conversation_uuid]
            
        if retry_count >= max_retries:
            logger.warning(f"Conversation {conversation_uuid} retry analysis gave up after {max_retries} attempts")
        else:
            logger.info(f"Conversation {conversation_uuid} retry monitor completed successfully")
    
    # Start the retry monitor in a background thread
    retry_thread = threading.Thread(target=retry_conversation_analysis_monitor, daemon=True)
    retry_thread.start()
    
    # Track this timer
    _conversation_retry_timers[conversation_uuid] = retry_thread


def stop_conversation_analysis_retry_monitor(conversation_uuid):
    """
    Stop the retry monitor for a specific conversation (if needed)
    """
    if conversation_uuid in _conversation_retry_timers:
        logger.info(f"Stopping retry monitor for conversation {conversation_uuid}")
        del _conversation_retry_timers[conversation_uuid]