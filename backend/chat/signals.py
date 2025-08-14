"""
Django signals for automatic conversation analysis
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Message, Conversation

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def message_saved_trigger_analysis(sender, instance, created, **kwargs):
    """
    Signal handler triggered when a message is saved
    Triggers message-level analysis for user messages immediately
    Also checks if the conversation should be analyzed automatically
    """
    if not created:
        # Only process new messages, not updates
        return
    
    try:
        conversation = instance.conversation
        
        # 1. IMMEDIATE MESSAGE-LEVEL ANALYSIS for user messages
        if instance.sender_type == 'user' and not instance.message_analysis:
            logger.info(f"Triggering immediate message-level analysis for user message {instance.uuid}")
            
            def analyze_message_async():
                """Analyze individual message in background using hybrid approach"""
                try:
                    import time
                    import asyncio
                    from core.services.hybrid_analysis_service import hybrid_analysis_service
                    from django.db import transaction, connections
                    
                    # Small delay to ensure message is fully committed
                    time.sleep(0.1)
                    
                    # Close any existing database connections to avoid threading issues
                    connections.close_all()
                    
                    # Create new event loop for async analysis
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # Use atomic transaction to ensure data consistency
                        with transaction.atomic():
                            # Re-fetch the message to avoid potential conflicts
                            try:
                                fresh_message = Message.objects.select_for_update().get(uuid=instance.uuid)
                            except Message.DoesNotExist:
                                logger.warning(f"Message {instance.uuid} not found during analysis")
                                return
                            
                            # Skip if already analyzed (check for non-empty dict)
                            if fresh_message.message_analysis and fresh_message.message_analysis != {}:
                                logger.debug(f"Message {fresh_message.uuid} already has analysis, skipping")
                                return
                            
                            # Analyze this specific message using hybrid approach
                            analysis_result = loop.run_until_complete(
                                hybrid_analysis_service.analyze_message_hybrid(fresh_message)
                            )
                            
                            if analysis_result and 'error' not in analysis_result:
                                # Save analysis to message
                                fresh_message.message_analysis = analysis_result
                                fresh_message.save(update_fields=['message_analysis'])
                                
                                # Log which method was used
                                analysis_source = analysis_result.get('analysis_source', 'Unknown')
                                logger.info(f"Message {fresh_message.uuid} analyzed successfully using {analysis_source}")
                                
                                # Verify the save worked
                                verification = Message.objects.get(uuid=fresh_message.uuid)
                                if not verification.message_analysis or verification.message_analysis == {}:
                                    logger.error(f"Analysis save verification failed for {fresh_message.uuid}")
                                else:
                                    logger.debug(f"Analysis save verified for {fresh_message.uuid}")
                            else:
                                logger.warning(f"Hybrid message analysis failed for {fresh_message.uuid}: {analysis_result.get('error', 'Unknown error')}")
                                
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.error(f"Error in hybrid message analysis {instance.uuid}: {e}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    
                    # Fallback: Try local analysis directly if hybrid fails
                    try:
                        logger.info(f"Attempting fallback local analysis for {instance.uuid}")
                        from core.services.message_analysis_service import message_analysis_service
                        from django.db import transaction
                        with transaction.atomic():
                            msg = Message.objects.get(uuid=instance.uuid)
                            if not msg.message_analysis or msg.message_analysis == {}:
                                result = message_analysis_service.analyze_user_message(msg)
                                if result and 'error' not in result:
                                    # Add fallback source labeling
                                    result.update({
                                        "analysis_source": "Local Analysis (Fallback)",
                                        "analysis_method": "emergency_fallback",
                                        "hybrid_failed": True
                                    })
                                    msg.message_analysis = result
                                    msg.save(update_fields=['message_analysis'])
                                    logger.info(f"Emergency fallback analysis successful for {instance.uuid}")
                    except Exception as fallback_error:
                        logger.error(f"Emergency fallback analysis also failed for {instance.uuid}: {fallback_error}")
            
            # Start message analysis in background thread
            import threading
            analysis_thread = threading.Thread(target=analyze_message_async, daemon=True)
            analysis_thread.start()
        
        # 2. CONVERSATION-LEVEL ANALYSIS (enhanced)
        message_count = conversation.total_messages
        has_analysis = bool(conversation.langextract_analysis and conversation.langextract_analysis != {})
        
        logger.debug(f"Message saved for conversation {conversation.uuid}: "
                    f"{message_count} messages, analyzed: {has_analysis}")
        
        # Trigger conversation analysis for conversations with enough messages
        if message_count >= 3 and not has_analysis:
            logger.info(f"Conversation {conversation.uuid} has {message_count} messages and no analysis - "
                       f"scheduling conversation analysis")
            
            def analyze_conversation_async():
                """Analyze conversation in background using hybrid approach"""
                try:
                    import time
                    import asyncio
                    from core.services.hybrid_analysis_service import hybrid_analysis_service
                    from django.db import transaction, connections
                    
                    # Wait a moment for the message to be committed
                    time.sleep(1)
                    
                    # Close database connections for threading
                    connections.close_all()
                    
                    # Create new event loop for async analysis
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # Use atomic transaction for conversation analysis
                        with transaction.atomic():
                            # Re-fetch conversation to ensure we have latest data
                            fresh_conversation = Conversation.objects.select_for_update().get(uuid=conversation.uuid)
                            
                            # Skip if already analyzed
                            if fresh_conversation.langextract_analysis and fresh_conversation.langextract_analysis != {}:
                                logger.debug(f"Conversation {fresh_conversation.uuid} already analyzed, skipping")
                                return
                            
                            # Perform hybrid conversation analysis (LLM preferred, local fallback)
                            analysis_result = loop.run_until_complete(
                                hybrid_analysis_service.analyze_conversation_hybrid(fresh_conversation)
                            )
                            
                            if analysis_result and 'error' not in analysis_result:
                                # Save analysis to conversation
                                fresh_conversation.langextract_analysis = analysis_result
                                fresh_conversation.save(update_fields=['langextract_analysis'])
                                
                                # Log which method was used
                                analysis_source = analysis_result.get('analysis_source', 'Unknown')
                                logger.info(f"Conversation {fresh_conversation.uuid} analyzed successfully using {analysis_source}")
                                
                                # Verify the save worked
                                verification = Conversation.objects.get(uuid=fresh_conversation.uuid)
                                if not verification.langextract_analysis or verification.langextract_analysis == {}:
                                    logger.error(f"Conversation analysis save verification failed for {fresh_conversation.uuid}")
                                else:
                                    logger.debug(f"Conversation analysis save verified for {fresh_conversation.uuid}")
                            else:
                                logger.warning(f"Hybrid conversation analysis failed for {fresh_conversation.uuid}: {analysis_result.get('error', 'Unknown error')}")
                                
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.error(f"Error in hybrid conversation analysis for {conversation.uuid}: {e}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    
                    # Emergency fallback to simple analysis
                    try:
                        logger.info(f"Attempting emergency fallback conversation analysis for {conversation.uuid}")
                        from core.services.simple_conversation_analysis_service import simple_conversation_analysis_service
                        from django.db import transaction
                        with transaction.atomic():
                            conv = Conversation.objects.get(uuid=conversation.uuid)
                            if not conv.langextract_analysis or conv.langextract_analysis == {}:
                                result = simple_conversation_analysis_service.analyze_conversation(conv)
                                if result and 'error' not in result:
                                    # Add emergency fallback labeling
                                    result.update({
                                        "analysis_source": "Local Analysis (Emergency Fallback)",
                                        "analysis_method": "emergency_conversation_fallback",
                                        "hybrid_failed": True
                                    })
                                    conv.langextract_analysis = result
                                    conv.save(update_fields=['langextract_analysis'])
                                    logger.info(f"Emergency conversation fallback successful for {conversation.uuid}")
                    except Exception as emergency_error:
                        logger.error(f"Emergency conversation fallback failed for {conversation.uuid}: {emergency_error}")
            
            # Start conversation analysis in background thread
            import threading
            conv_analysis_thread = threading.Thread(target=analyze_conversation_async, daemon=True)
            conv_analysis_thread.start()
        
    except Exception as e:
        logger.warning(f"Error in message_saved_trigger_analysis signal: {e}")


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