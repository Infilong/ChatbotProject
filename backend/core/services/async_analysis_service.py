"""
Asynchronous Analysis Service
Handles background analysis tasks without blocking the Django request-response cycle
"""

import logging
import threading
import time
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction, connections
from django.conf import settings
from chat.models import Conversation, Message

logger = logging.getLogger(__name__)


class AnalysisTaskQueue:
    """Simple database-backed task queue for analysis tasks"""
    
    _instance = None
    _lock = threading.Lock()
    _worker_thread = None
    _shutdown = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.task_storage = {}  # In-memory task storage for simplicity
            self.task_lock = threading.Lock()
            self.start_worker()
    
    def start_worker(self):
        """Start the background worker thread"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._shutdown = False
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            logger.info("Async analysis worker started")
    
    def _worker_loop(self):
        """Main worker loop that processes tasks"""
        logger.info("Async analysis worker loop started")
        
        while not self._shutdown:
            try:
                # Process pending tasks
                self._process_tasks()
                
                # Sleep for a short interval to avoid busy waiting
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in async analysis worker: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _process_tasks(self):
        """Process pending analysis tasks"""
        with self.task_lock:
            current_time = time.time()
            tasks_to_process = []
            
            # Find tasks ready for processing
            for task_id, task in list(self.task_storage.items()):
                if task['status'] == 'pending' and task['execute_at'] <= current_time:
                    task['status'] = 'processing'
                    tasks_to_process.append(task)
            
        # Process tasks outside the lock
        for task in tasks_to_process:
            try:
                self._execute_task(task)
                
                # Remove completed task
                with self.task_lock:
                    if task['id'] in self.task_storage:
                        del self.task_storage[task['id']]
                        
            except Exception as e:
                logger.error(f"Error executing task {task['id']}: {e}")
                
                # Mark task as failed
                with self.task_lock:
                    if task['id'] in self.task_storage:
                        task['status'] = 'failed'
                        task['error'] = str(e)
    
    def _execute_task(self, task: Dict[str, Any]):
        """Execute a specific analysis task"""
        task_type = task['type']
        
        # Close any existing database connections to avoid threading issues
        connections.close_all()
        
        if task_type == 'analyze_message':
            self._analyze_message_task(task)
        elif task_type == 'analyze_conversation':
            self._analyze_conversation_task(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
    
    def _analyze_message_task(self, task: Dict[str, Any]):
        """Execute message analysis task"""
        message_uuid = task['data']['message_uuid']
        
        try:
            # Create new event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                with transaction.atomic():
                    # Re-fetch the message to ensure it still exists
                    try:
                        message = Message.objects.select_for_update().get(uuid=message_uuid)
                    except Message.DoesNotExist:
                        logger.info(f"Message {message_uuid} no longer exists, skipping analysis")
                        return
                    
                    # Skip if already analyzed
                    if message.message_analysis and message.message_analysis != {}:
                        logger.debug(f"Message {message_uuid} already analyzed, skipping")
                        return
                    
                    # Import the analysis service
                    from core.services.hybrid_analysis_service import hybrid_analysis_service
                    
                    # Perform analysis
                    analysis_result = loop.run_until_complete(
                        hybrid_analysis_service.analyze_message_hybrid(message)
                    )
                    
                    if analysis_result and 'error' not in analysis_result:
                        # Add async processing metadata
                        analysis_result.update({
                            "processing_mode": "async_background",
                            "processed_at": timezone.now().isoformat()
                        })
                        
                        # Save analysis
                        message.message_analysis = analysis_result
                        message.save(update_fields=['message_analysis'])
                        
                        analysis_source = analysis_result.get('analysis_source', 'Unknown')
                        logger.info(f"Message {message_uuid} analyzed asynchronously using {analysis_source}")
                        
                    else:
                        logger.warning(f"Async message analysis failed for {message_uuid}: {analysis_result.get('error', 'Unknown error')}")
                        
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error in async message analysis for {message_uuid}: {e}")
    
    def _analyze_conversation_task(self, task: Dict[str, Any]):
        """Execute conversation analysis task"""
        conversation_uuid = task['data']['conversation_uuid']
        
        try:
            # Create new event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                with transaction.atomic():
                    # Re-fetch the conversation to ensure it still exists
                    try:
                        conversation = Conversation.objects.select_for_update().get(uuid=conversation_uuid)
                    except Conversation.DoesNotExist:
                        logger.info(f"Conversation {conversation_uuid} no longer exists, skipping analysis")
                        return
                    
                    # Skip if already analyzed
                    if conversation.langextract_analysis and conversation.langextract_analysis != {}:
                        logger.debug(f"Conversation {conversation_uuid} already analyzed, skipping")
                        return
                    
                    # Import the analysis service
                    from core.services.hybrid_analysis_service import hybrid_analysis_service
                    
                    # Perform analysis
                    analysis_result = loop.run_until_complete(
                        hybrid_analysis_service.analyze_conversation_hybrid(conversation)
                    )
                    
                    if analysis_result and 'error' not in analysis_result:
                        # Add async processing metadata
                        analysis_result.update({
                            "processing_mode": "async_background",
                            "processed_at": timezone.now().isoformat()
                        })
                        
                        # Save analysis
                        conversation.langextract_analysis = analysis_result
                        conversation.save(update_fields=['langextract_analysis'])
                        
                        analysis_source = analysis_result.get('analysis_source', 'Unknown')
                        logger.info(f"Conversation {conversation_uuid} analyzed asynchronously using {analysis_source}")
                        
                    else:
                        logger.warning(f"Async conversation analysis failed for {conversation_uuid}: {analysis_result.get('error', 'Unknown error')}")
                        
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error in async conversation analysis for {conversation_uuid}: {e}")
    
    def queue_message_analysis(self, message_uuid: str, delay_seconds: int = 5):
        """Queue a message for analysis with optional delay"""
        task_id = f"message_{message_uuid}_{int(time.time())}"
        
        task = {
            'id': task_id,
            'type': 'analyze_message',
            'data': {'message_uuid': message_uuid},
            'status': 'pending',
            'created_at': time.time(),
            'execute_at': time.time() + delay_seconds
        }
        
        with self.task_lock:
            self.task_storage[task_id] = task
        
        logger.info(f"Queued message analysis for {message_uuid} (delay: {delay_seconds}s)")
        return task_id
    
    def queue_conversation_analysis(self, conversation_uuid: str, delay_seconds: int = 5):
        """Queue a conversation for analysis with optional delay"""
        task_id = f"conversation_{conversation_uuid}_{int(time.time())}"
        
        task = {
            'id': task_id,
            'type': 'analyze_conversation',
            'data': {'conversation_uuid': conversation_uuid},
            'status': 'pending',
            'created_at': time.time(),
            'execute_at': time.time() + delay_seconds
        }
        
        with self.task_lock:
            self.task_storage[task_id] = task
        
        logger.info(f"Queued conversation analysis for {conversation_uuid} (delay: {delay_seconds}s)")
        return task_id
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with self.task_lock:
            pending_count = sum(1 for task in self.task_storage.values() if task['status'] == 'pending')
            processing_count = sum(1 for task in self.task_storage.values() if task['status'] == 'processing')
            failed_count = sum(1 for task in self.task_storage.values() if task['status'] == 'failed')
        
        return {
            'pending_tasks': pending_count,
            'processing_tasks': processing_count,
            'failed_tasks': failed_count,
            'total_tasks': len(self.task_storage),
            'worker_active': self._worker_thread is not None and self._worker_thread.is_alive(),
            'worker_shutdown': self._shutdown
        }
    
    def shutdown(self):
        """Gracefully shutdown the worker"""
        self._shutdown = True
        logger.info("Async analysis worker shutdown initiated")


# Global task queue instance
task_queue = AnalysisTaskQueue()


class AsyncAnalysisService:
    """Service for managing asynchronous analysis operations"""
    
    def __init__(self):
        self.task_queue = task_queue
    
    def schedule_message_analysis(self, message_instance: Message, delay_seconds: int = 5) -> str:
        """
        Schedule a message for background analysis
        Returns task ID for tracking
        """
        return self.task_queue.queue_message_analysis(
            str(message_instance.uuid),
            delay_seconds
        )
    
    def schedule_conversation_analysis(self, conversation_instance: Conversation, delay_seconds: int = 5) -> str:
        """
        Schedule a conversation for background analysis
        Returns task ID for tracking
        """
        return self.task_queue.queue_conversation_analysis(
            str(conversation_instance.uuid),
            delay_seconds
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'service_name': 'AsyncAnalysisService',
            'queue_status': self.task_queue.get_queue_status(),
            'timestamp': timezone.now().isoformat()
        }


# Global service instance
async_analysis_service = AsyncAnalysisService()