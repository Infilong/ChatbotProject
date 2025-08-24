"""
Django signals for automatic document processing
"""

import asyncio
import logging
import json
import threading
import time
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from .models import Document, DocumentationImprovement
from .document_processor import DocumentProcessor
from chat.models import Message, Conversation

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def auto_process_document(sender, instance, created, **kwargs):
    """
    Automatically process document when uploaded or file changes
    """
    # Only process if document is new or file has changed
    should_process = (
        created or  # New document
        (instance.file and not instance.extracted_text) or  # Has file but no text
        instance._file_has_changed()  # File has been updated
    )
    
    if should_process and instance.file:
        logger.info(f"Triggering automatic processing for document: {instance.name}")
        
        # Process document in background thread to avoid blocking admin interface
        def async_document_processing():
            try:
                # Small delay to allow main transaction to complete
                time.sleep(0.2)
                
                with transaction.atomic():
                    # Refresh instance from database
                    document = Document.objects.get(id=instance.id)
                    
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Run document processing
                    success = loop.run_until_complete(
                        DocumentProcessor.process_document(document)
                    )
                    
                    if success:
                        logger.info(f"Successfully auto-processed document: {document.name}")
                    else:
                        logger.warning(f"Auto-processing failed for document: {document.name}")
                        
            except Exception as e:
                logger.error(f"Error in background document processing: {e}")
            finally:
                if 'loop' in locals():
                    loop.close()
        
        # Start processing in background thread
        processing_thread = threading.Thread(target=async_document_processing, daemon=True)
        processing_thread.start()
        logger.info(f"Started background processing for document: {instance.name}")
    else:
        logger.debug(f"Skipping processing for document: {instance.name} (no changes or no file)")


@receiver(post_save, sender=Document)
def update_knowledge_base_stats(sender, instance, created, **kwargs):
    """
    Update knowledge base statistics and rebuild search indexes when documents change
    """
    if created:
        logger.info(f"New document added to knowledge base: {instance.name}")
    
    # Automatically rebuild search indexes when document has extracted text
    if instance.extracted_text and instance.is_active:
        logger.info(f"Scheduling search index rebuild for document: {instance.name}")
        
        # Rebuild indexes in background thread to avoid blocking admin interface
        def async_index_rebuild():
            try:
                # Small delay to allow main transaction to complete
                time.sleep(0.3)
                
                with transaction.atomic():
                    # Refresh instance from database
                    document = Document.objects.get(id=instance.id)
                    
                    if document.extracted_text and document.is_active:
                        logger.info(f"Rebuilding search indexes for document: {document.name}")
                        
                        # Import here to avoid circular imports
                        from .hybrid_search import HybridSearchService
                        
                        # Rebuild indexes
                        search_service = HybridSearchService()
                        success = search_service.build_indexes(force_rebuild=False)
                        
                        if success:
                            logger.info(f"Search indexes updated successfully for document: {document.name}")
                        else:
                            logger.warning(f"Failed to update search indexes for document: {document.name}")
                    else:
                        logger.debug(f"Document no longer has extracted text or is inactive: {document.name}")
                        
            except Exception as e:
                logger.error(f"Error in background search index rebuild: {e}")
        
        # Start index rebuild in background thread
        rebuild_thread = threading.Thread(target=async_index_rebuild, daemon=True)
        rebuild_thread.start()
        logger.info(f"Started background search index rebuild for document: {instance.name}")
    else:
        logger.debug(f"Document with extracted text available: {instance.name}")


def analyze_documentation_potential(message_content):
    """
    Analyze message content for documentation/FAQ potential
    Returns score from 0-100 and analysis data
    """
    content_lower = message_content.lower().strip()
    
    # High-potential keywords and phrases
    high_potential_keywords = [
        # Account management
        'delete account', 'close account', 'deactivate account', 'cancel account',
        'how to delete', 'how to close', 'remove my account', 'account deletion',
        
        # Authentication issues
        'password reset', 'forgot password', 'can\'t login', 'login problem',
        'reset password', 'password not working', 'login issues', 'access denied',
        
        # Billing and subscription
        'billing question', 'subscription', 'charges', 'payment', 'invoice',
        'cancel subscription', 'upgrade plan', 'pricing', 'refund',
        
        # Feature requests and how-to
        'how to', 'how do i', 'how can i', 'is it possible to', 'can you help me',
        'tutorial', 'guide', 'instructions', 'step by step',
        
        # Common support issues
        'not working', 'error message', 'bug', 'issue with', 'problem with',
        'missing feature', 'feature request', 'improvement suggestion'
    ]
    
    # Question indicators (higher FAQ potential)
    question_indicators = [
        '?', 'how', 'what', 'where', 'when', 'why', 'who', 'which',
        'can i', 'could i', 'should i', 'would it', 'is there a way'
    ]
    
    # Calculate base score
    score = 0
    matched_keywords = []
    
    # Check for high-potential keywords (30 points each, max 60)
    for keyword in high_potential_keywords:
        if keyword in content_lower:
            score += 30
            matched_keywords.append(keyword)
            if score >= 60:  # Cap at 60 from keywords
                break
    
    # Check for question indicators (10 points each, max 30)
    question_score = 0
    for indicator in question_indicators:
        if indicator in content_lower:
            question_score += 10
            if question_score >= 30:
                break
    
    score += question_score
    
    # Length bonus for detailed questions (up to 20 points)
    if len(message_content) > 50:
        length_bonus = min(20, len(message_content) // 25)
        score += length_bonus
    
    # Multiple sentence bonus (suggests complex issue)
    if content_lower.count('.') + content_lower.count('?') + content_lower.count('!') > 1:
        score += 15
    
    # Cap at 100
    score = min(100, score)
    
    # Determine category based on keywords
    category = 'general_inquiry'
    if any(kw in content_lower for kw in ['delete', 'close', 'cancel', 'account']):
        category = 'account_management'
    elif any(kw in content_lower for kw in ['password', 'login', 'access']):
        category = 'authentication_issues'
    elif any(kw in content_lower for kw in ['billing', 'payment', 'subscription', 'charge']):
        category = 'billing_support'
    elif any(kw in content_lower for kw in ['how to', 'tutorial', 'guide', 'step']):
        category = 'user_guidance'
    
    # Determine priority based on keywords and score
    if score >= 85 or any(kw in content_lower for kw in ['urgent', 'immediately', 'asap', 'critical']):
        priority = 'urgent'
    elif score >= 70 or any(kw in content_lower for kw in ['important', 'need help', 'problem']):
        priority = 'high'
    elif score >= 60:
        priority = 'medium'
    else:
        priority = 'low'
    
    analysis_data = {
        'documentation_potential_score': score,
        'matched_keywords': matched_keywords,
        'category': category,
        'priority': priority,
        'has_question_indicators': question_score > 0,
        'message_length': len(message_content),
        'analysis_timestamp': str(timezone.now())
    }
    
    return score, analysis_data


def extract_issues_from_content(message_content):
    """Extract specific issues from message content"""
    content_lower = message_content.lower()
    issues = []
    
    issue_patterns = {
        'Account deletion request': ['delete account', 'close account', 'remove account'],
        'Password reset failure': ['password reset', 'forgot password', 'password not working'],
        'Login difficulties': ['can\'t login', 'login problem', 'access denied', 'login error'],
        'Billing confusion': ['billing question', 'charges', 'subscription cost', 'payment issue'],
        'Feature not working': ['not working', 'doesn\'t work', 'broken feature', 'error message'],
        'Missing documentation': ['how to', 'no instructions', 'unclear process', 'need help with'],
        'Process unclear': ['confused about', 'don\'t understand', 'unclear how to', 'what does this mean']
    }
    
    for issue_type, patterns in issue_patterns.items():
        if any(pattern in content_lower for pattern in patterns):
            issues.append(issue_type)
    
    return issues


def generate_improvement_summary(message_content, analysis_data, issues):
    """Generate human-friendly analysis summary"""
    score = analysis_data['documentation_potential_score']
    category = analysis_data['category']
    
    summary_parts = []
    
    # Opening based on score
    if score >= 85:
        summary_parts.append("High-priority documentation opportunity identified.")
    elif score >= 70:
        summary_parts.append("Significant documentation improvement potential detected.")
    else:
        summary_parts.append("Moderate documentation enhancement opportunity found.")
    
    # Add specific issues
    if issues:
        issues_text = ', '.join(issues[:3])  # Limit to first 3 issues
        summary_parts.append(f"Specific issues: {issues_text}.")
    
    # Add category context
    category_contexts = {
        'account_management': 'This relates to account management processes that users frequently ask about.',
        'authentication_issues': 'This involves authentication problems that could be addressed with better documentation.',
        'billing_support': 'This concerns billing and subscription topics that would benefit from clearer FAQ entries.',
        'user_guidance': 'This represents a need for better user guidance and step-by-step instructions.',
        'general_inquiry': 'This is a general inquiry that could be addressed in documentation.'
    }
    
    if category in category_contexts:
        summary_parts.append(category_contexts[category])
    
    # Add recommendation
    if score >= 80:
        summary_parts.append("Strongly recommended for FAQ/documentation update.")
    elif score >= 70:
        summary_parts.append("Recommended for documentation improvement.")
    else:
        summary_parts.append("Consider for documentation enhancement.")
    
    return ' '.join(summary_parts)


@receiver(post_save, sender=Message)
def analyze_message_for_documentation_potential(sender, instance, created, **kwargs):
    """
    Automatically analyze new user messages for documentation potential
    Create DocumentationImprovement record if potential > 60%
    """
    # Only analyze new user messages (not bot responses)
    if not created or instance.sender_type != 'user':
        return
    
    # Skip if message is too short to be meaningful
    if len(instance.content.strip()) < 10:
        return
    
    # Skip if DocumentationImprovement already exists for this conversation
    if DocumentationImprovement.objects.filter(conversation=instance.conversation).exists():
        return
    
    try:
        # Analyze the message content
        score, analysis_data = analyze_documentation_potential(instance.content)
        
        logger.info(f"Analyzed message '{instance.content[:30]}...' - Score: {score}%")
        
        # Only create DocumentationImprovement if score > 60%
        if score > 60:
            # Extract specific issues
            issues = extract_issues_from_content(instance.content)
            issues_text = '; '.join(issues) if issues else 'General inquiry requiring documentation'
            
            # Generate analysis summary
            summary = generate_improvement_summary(instance.content, analysis_data, issues)
            
            # Create DocumentationImprovement record
            improvement = DocumentationImprovement.objects.create(
                conversation=instance.conversation,
                conversation_title=instance.conversation.get_title(),
                issues_detected=issues_text,
                priority=analysis_data['priority'],
                langextract_analysis_summary=summary,
                langextract_full_analysis=analysis_data,
                category=analysis_data['category'],
                satisfaction_level=None,  # Will be updated when conversation ends
                analysis_completed=True
            )
            
            logger.info(f"✅ Created DocumentationImprovement (ID: {improvement.id}) for message: '{instance.content[:50]}...' (Score: {score}%)")
        else:
            logger.debug(f"Message score too low for documentation improvement: {score}%")
            
    except Exception as e:
        logger.error(f"Error analyzing message for documentation potential: {e}")


@receiver(post_save, sender=Conversation)
def update_documentation_improvement_satisfaction(sender, instance, created, **kwargs):
    """
    Update satisfaction level when conversation gets a satisfaction score
    """
    if not created and instance.satisfaction_score is not None:
        # Update any related DocumentationImprovement records
        improvements = DocumentationImprovement.objects.filter(
            conversation=instance,
            satisfaction_level__isnull=True
        )
        
        if improvements.exists():
            # Convert satisfaction score to 1-5 scale
            if instance.satisfaction_score >= 4.5:
                satisfaction_level = 5
            elif instance.satisfaction_score >= 3.5:
                satisfaction_level = 4
            elif instance.satisfaction_score >= 2.5:
                satisfaction_level = 3
            elif instance.satisfaction_score >= 1.5:
                satisfaction_level = 2
            else:
                satisfaction_level = 1
            
            count = improvements.update(satisfaction_level=satisfaction_level)
            logger.info(f"Updated satisfaction level to {satisfaction_level} for {count} DocumentationImprovement records")