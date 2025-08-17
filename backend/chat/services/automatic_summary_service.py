"""
Automatic LLM-Driven Summary Service
Generates intelligent conversation summaries automatically using pure LLM analysis
"""

import json
from datetime import datetime, timedelta
from django.db.models import Q, Count
from django.utils import timezone
from typing import Dict, List, Any, Optional
import logging

from ..models import Message, Conversation, ConversationSummary
from ..llm_services import LLMManager

logger = logging.getLogger(__name__)


class AutomaticSummaryService:
    """Service for automatic LLM-driven conversation summaries"""
    
    @classmethod
    async def generate_automatic_summary(cls, trigger_reason: str = "manual") -> Optional[ConversationSummary]:
        """
        Generate automatic summary using pure LLM intelligence
        LLM decides what to analyze and how to present it
        """
        try:
            # Step 1: Get recent meaningful messages
            recent_messages = await cls._get_recent_messages_async()
            
            if not recent_messages:
                logger.info("No recent messages found for summary generation")
                return None
            
            # Step 2: Let LLM analyze and decide what's important
            llm_service = await LLMManager.get_active_service()
            analysis_result = await cls._generate_llm_summary(llm_service, recent_messages)
            
            if not analysis_result:
                logger.warning("LLM failed to generate summary")
                return None
            
            # Step 3: Create summary record with LLM content
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def create_summary():
                return ConversationSummary.objects.create(
                    llm_analysis=analysis_result['analysis'],
                    analysis_period=analysis_result['period'],
                    messages_analyzed_count=len(recent_messages),
                    critical_issues_found=analysis_result['critical_count'],
                    trigger_reason=trigger_reason,
                    llm_model_used=analysis_result.get('model', 'unknown'),
                    llm_response_time=analysis_result.get('response_time', 0)
                )
            
            summary = await create_summary()
            
            logger.info(f"Automatic summary generated: {summary.uuid}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate automatic summary: {e}")
            return None
    
    @classmethod
    async def _get_recent_messages_async(cls, hours: int = 24) -> List[Message]:
        """Get recent messages with LangExtract analysis (async version)"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_messages():
            try:
                cutoff_time = timezone.now() - timedelta(hours=hours)
                
                # Get messages with analysis data, prioritizing user messages
                messages = Message.objects.filter(
                    timestamp__gte=cutoff_time,
                    message_analysis__isnull=False
                ).exclude(
                    message_analysis={}
                ).select_related('conversation').order_by('-timestamp')[:50]  # Limit for LLM processing
                
                return list(messages)
            except Exception as e:
                logger.error(f"Error fetching recent messages: {e}")
                return []
        
        return await get_messages()
    
    @classmethod
    async def _generate_llm_summary(cls, llm_service, messages: List[Message]) -> Optional[Dict[str, Any]]:
        """
        Let LLM analyze messages and generate intelligent summary
        Pure LLM decision-making on what's important and how to present it
        """
        import time
        start_time = time.time()
        
        try:
            # Prepare message data for LLM analysis
            message_data = []
            critical_count = 0
            
            for msg in messages:
                analysis = msg.message_analysis or {}
                importance = analysis.get('importance_level', {})
                
                # Count critical issues
                if importance.get('level') == 'critical':
                    critical_count += 1
                
                message_info = {
                    'content': msg.content,
                    'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'sender': msg.sender_type,
                    'importance': importance.get('level', 'unknown'),
                    'urgency_score': importance.get('urgency_score', 0),
                    'escalation_needed': importance.get('escalation_needed', False),
                    'issues_raised': analysis.get('issues_raised', []),
                    'faq_potential': analysis.get('faq_potential', {}),
                    'satisfaction': analysis.get('satisfaction_level', {})
                }
                message_data.append(message_info)
            
            # Create shorter, focused LLM prompt to avoid token limits
            # Get top 3 most important messages for analysis
            sorted_messages = sorted(message_data, key=lambda x: x.get('urgency_score', 0), reverse=True)[:3]
            
            analysis_prompt = f"""Analyze {len(messages)} customer service messages. Focus on business-critical insights.

TOP ISSUES:
{json.dumps(sorted_messages, indent=1)}

Provide:
1. Critical issues requiring immediate action
2. Customer satisfaction summary
3. Key recommendations
4. FAQ/documentation gaps

Keep response under 400 words, executive-friendly format."""

            # Generate LLM analysis
            response, metadata = await llm_service.generate_response(
                messages=[{'role': 'user', 'content': analysis_prompt}],
                max_tokens=1500,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            
            response_time = time.time() - start_time
            
            # Determine analysis period
            if messages:
                oldest_msg = min(msg.timestamp for msg in messages)
                newest_msg = max(msg.timestamp for msg in messages)
                time_diff = newest_msg - oldest_msg
                
                if time_diff.days > 0:
                    period = f"Last {time_diff.days + 1} days"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    period = f"Last {hours + 1} hours"
                else:
                    period = "Recent activity"
            else:
                period = "Today"
            
            return {
                'analysis': response,
                'period': period,
                'critical_count': critical_count,
                'model': metadata.get('provider', 'unknown'),
                'response_time': response_time
            }
            
        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
            return None
    
    @classmethod
    async def check_and_generate_summary(cls) -> Optional[ConversationSummary]:
        """
        Check if automatic summary should be generated based on conditions
        DEVELOPMENT MODE: Generate summary when 2+ critical/important messages exist
        """
        from django.db.models import Q
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def count_important_messages():
            # Count critical and high importance messages in last 24 hours
            cutoff_time = timezone.now() - timedelta(hours=24)
            return Message.objects.filter(
                timestamp__gte=cutoff_time,
                message_analysis__importance_level__level__in=['critical', 'high']
            ).count()
        
        important_count = await count_important_messages()
        
        # DEVELOPMENT TRIGGER: 2+ critical/important messages
        if important_count >= 2:
            logger.info(f"DEVELOPMENT MODE: Found {important_count} critical/important messages, generating automatic summary")
            return await cls.generate_automatic_summary("dev_critical_threshold_reached")
        
        # Fallback: Check for recent critical messages (original logic)
        @sync_to_async  
        def check_recent_critical():
            return Message.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=2),
                message_analysis__importance_level__level='critical'
            ).exists()
            
        if await check_recent_critical():
            logger.info("Found recent critical messages, generating automatic summary")
            return await cls.generate_automatic_summary("critical_messages_detected")
        
        # Check if it's been a while since last summary (reduced for dev)
        @sync_to_async
        def check_last_summary():
            last_summary = ConversationSummary.objects.first()
            if not last_summary:
                return True
            hours_since = (timezone.now() - last_summary.generated_at).total_seconds() / 3600
            return hours_since >= 1  # Reduced to 1 hour for development
            
        if await check_last_summary():
            logger.info("1+ hours since last summary, generating automatic summary (dev mode)")
            return await cls.generate_automatic_summary("scheduled_dev_hourly")
        
        return None
    
    @classmethod
    async def generate_summary_for_critical_message(cls, message: Message) -> Optional[ConversationSummary]:
        """
        Generate focused summary when a critical message is detected
        """
        try:
            # Get LLM service
            llm_service = await LLMManager.get_active_service()
            
            # Create focused prompt for critical message
            critical_prompt = f"""
CRITICAL MESSAGE DETECTED:
Content: "{message.content}"
Timestamp: {message.timestamp.strftime('%Y-%m-%d %H:%M')}
Analysis: {json.dumps(message.message_analysis, indent=2)}

As a customer service AI analyst, provide immediate insights:

1. URGENCY ASSESSMENT: How critical is this issue?
2. IMMEDIATE ACTIONS: What should the team do right now?
3. BUSINESS IMPACT: What are the potential consequences?
4. ESCALATION PATH: Who should be notified immediately?
5. CONTEXT: Are there related issues in recent conversations?

Provide a concise but comprehensive analysis that helps management respond effectively to this critical situation.
"""
            
            response, metadata = await llm_service.generate_response(
                messages=[{'role': 'user', 'content': critical_prompt}],
                max_tokens=800,
                temperature=0.2  # Very low temperature for critical analysis
            )
            
            # Create focused summary
            summary = ConversationSummary.objects.create(
                llm_analysis=response,
                analysis_period="Critical Issue Alert",
                messages_analyzed_count=1,
                critical_issues_found=1,
                trigger_reason="critical_message_alert",
                llm_model_used=metadata.get('provider', 'unknown'),
                llm_response_time=metadata.get('response_time', 0)
            )
            
            logger.info(f"Critical message summary generated: {summary.uuid}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate critical message summary: {e}")
            return None