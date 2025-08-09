"""
Django signals for automatic document processing
"""

import asyncio
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Document
from .document_processor import DocumentProcessor

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
        
        # Process document asynchronously
        try:
            # Create new event loop for async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run document processing
            success = loop.run_until_complete(
                DocumentProcessor.process_document(instance)
            )
            
            if success:
                logger.info(f"Successfully auto-processed document: {instance.name}")
            else:
                logger.warning(f"Auto-processing failed for document: {instance.name}")
                
        except Exception as e:
            logger.error(f"Error in auto-processing document {instance.name}: {e}")
        finally:
            loop.close()
    else:
        logger.debug(f"Skipping processing for document: {instance.name} (no changes or no file)")


@receiver(post_save, sender=Document)
def update_knowledge_base_stats(sender, instance, created, **kwargs):
    """
    Update knowledge base statistics when documents change
    """
    if created:
        logger.info(f"New document added to knowledge base: {instance.name}")
    
    # Could trigger knowledge base reindexing here if needed
    # For now, just log the update
    if instance.extracted_text:
        logger.debug(f"Document with extracted text available: {instance.name}")