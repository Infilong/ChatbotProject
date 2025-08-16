from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from chat.models import Conversation, Message


class ConversationAnalysis(models.Model):
    SENTIMENT_CHOICES = [
        ('positive', _('Positive')),
        ('negative', _('Negative')),
        ('neutral', _('Neutral')),
    ]
    
    RESOLUTION_CHOICES = [
        ('resolved', _('Resolved')),
        ('pending', _('Pending')),
        ('escalated', _('Escalated')),
    ]
    
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='analysis', verbose_name=_('Conversation'))
    analyzed_at = models.DateTimeField(auto_now=True, verbose_name=_('Analyzed At'))
    
    # LangExtract analysis results
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, verbose_name=_('Sentiment'))
    satisfaction_level = models.IntegerField(verbose_name=_('Satisfaction Level'))  # 1-10 scale
    issues_raised = models.JSONField(default=list, verbose_name=_('Issues Raised'))  # List of categorized problems
    urgency_indicators = models.JSONField(default=list, verbose_name=_('Urgency Indicators'))  # Urgent phrases with source
    resolution_status = models.CharField(max_length=10, choices=RESOLUTION_CHOICES, verbose_name=_('Resolution Status'))
    customer_intent = models.CharField(max_length=50, verbose_name=_('Customer Intent'))  # support/inquiry/complaint
    key_insights = models.JSONField(default=list, verbose_name=_('Key Insights'))  # Actionable business intelligence
    
    # Source grounding data from LangExtract
    source_spans = models.JSONField(default=list, verbose_name=_('Source Spans'))  # Text spans with exact locations
    confidence_score = models.FloatField(default=0.0, verbose_name=_('Confidence Score'))  # Analysis confidence
    
    # Processing metadata
    langextract_model_used = models.CharField(max_length=50, verbose_name=_('LangExtract Model Used'))
    processing_time = models.FloatField(null=True, blank=True, verbose_name=_('Processing Time'))
    
    class Meta:
        ordering = ['-analyzed_at']
        verbose_name = _('Analysis')
        verbose_name_plural = _('Analysis')
        
    def __str__(self):
        return f"Analysis for Conversation {self.conversation.id} - {self.sentiment}"


class UserFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback', verbose_name=_('User'))
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='feedback_entries', verbose_name=_('Message'))
    feedback_type = models.CharField(max_length=10, choices=Message.FEEDBACK_CHOICES, verbose_name=_('Feedback Type'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))
    
    # Optional feedback details
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    rating = models.IntegerField(null=True, blank=True, verbose_name=_('Rating'))  # 1-5 star rating
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['user', 'message']  # One feedback per user per message
        verbose_name = _('User Feedback')
        verbose_name_plural = _('User Feedback')
        
    def __str__(self):
        return f"{self.feedback_type} feedback by {self.user.username}"


class AnalyticsSummary(models.Model):
    date = models.DateField(unique=True, verbose_name=_('Date'))
    
    # Daily metrics
    total_conversations = models.IntegerField(default=0, verbose_name=_('Total Conversations'))
    total_messages = models.IntegerField(default=0, verbose_name=_('Total Messages'))
    unique_users = models.IntegerField(default=0, verbose_name=_('Unique Users'))
    average_satisfaction = models.FloatField(default=0.0, verbose_name=_('Average Satisfaction'))
    
    # Sentiment distribution
    positive_conversations = models.IntegerField(default=0, verbose_name=_('Positive Conversations'))
    negative_conversations = models.IntegerField(default=0, verbose_name=_('Negative Conversations'))
    neutral_conversations = models.IntegerField(default=0, verbose_name=_('Neutral Conversations'))
    
    # Issue tracking
    total_issues_raised = models.IntegerField(default=0, verbose_name=_('Total Issues Raised'))
    resolved_issues = models.IntegerField(default=0, verbose_name=_('Resolved Issues'))
    escalated_issues = models.IntegerField(default=0, verbose_name=_('Escalated Issues'))
    
    # Performance metrics
    average_response_time = models.FloatField(default=0.0, verbose_name=_('Average Response Time'))
    bot_vs_human_ratio = models.FloatField(default=0.0, verbose_name=_('Bot vs Human Ratio'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        ordering = ['-date']
        verbose_name = _('Analytics Summary')
        verbose_name_plural = _('Analytics Summaries')
        
    def __str__(self):
        return f"Analytics Summary for {self.date}"


class DocumentUsage(models.Model):
    """Enhanced model for tracking detailed document usage by chatbot"""
    
    USAGE_TYPE_CHOICES = [
        ('full_context', _('Full Context')),
        ('excerpt', _('Excerpt')),
        ('summary', _('Summary')),
        ('keyword_match', _('Keyword Match')),
    ]
    
    # Basic references
    document = models.ForeignKey('documents.Document', on_delete=models.CASCADE, related_name='usage_stats', verbose_name=_('Document'))
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, verbose_name=_('Conversation'))
    message = models.ForeignKey(Message, on_delete=models.CASCADE, verbose_name=_('Message'))
    
    # Usage details
    referenced_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Referenced At'))
    search_query = models.CharField(max_length=500, verbose_name=_('Search Query'))  # User's original question
    relevance_score = models.FloatField(default=0.0, verbose_name=_('Relevance Score'))  # How relevant document was
    usage_type = models.CharField(max_length=20, choices=USAGE_TYPE_CHOICES, default='excerpt', verbose_name=_('Usage Type'))
    
    # Content tracking - what parts were used
    excerpt_used = models.TextField(blank=True, verbose_name=_('Excerpt Used'))  # Exact text used from document
    excerpt_start_position = models.IntegerField(null=True, blank=True, verbose_name=_('Start Position'))  # Character position in document
    excerpt_length = models.IntegerField(null=True, blank=True, verbose_name=_('Excerpt Length'))  # Length of excerpt
    keywords_matched = models.JSONField(default=list, verbose_name=_('Keywords Matched'))  # List of keywords that matched
    
    # Context information
    context_category = models.CharField(max_length=100, blank=True, verbose_name=_('Context Category'))  # From document category
    user_intent = models.CharField(max_length=100, blank=True, verbose_name=_('User Intent'))  # What user was asking about
    
    # Feedback and effectiveness
    user_feedback = models.CharField(
        max_length=10, 
        choices=Message.FEEDBACK_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name=_('User Feedback')
    )
    effectiveness_score = models.FloatField(null=True, blank=True, verbose_name=_('Effectiveness Score'))  # Based on user feedback
    response_helpful = models.BooleanField(null=True, blank=True, verbose_name=_('Response Helpful'))  # Did this help answer the question
    
    # AI model information
    llm_model_used = models.CharField(max_length=50, blank=True, verbose_name=_('LLM Model Used'))
    processing_time = models.FloatField(null=True, blank=True, verbose_name=_('Processing Time'))
    
    class Meta:
        ordering = ['-referenced_at']
        verbose_name = _('Document Usage')
        verbose_name_plural = _('Document Usage')
        indexes = [
            models.Index(fields=['document', '-referenced_at']),
            models.Index(fields=['search_query']),
            models.Index(fields=['relevance_score']),
        ]
        
    def __str__(self):
        return f"Document {self.document.name} used in Conversation {self.conversation.id}"
    
    def get_excerpt_preview(self, max_length=100):
        """Get a preview of the excerpt used"""
        if not self.excerpt_used:
            return _('No excerpt available')
        if len(self.excerpt_used) <= max_length:
            return self.excerpt_used
        return self.excerpt_used[:max_length] + "..."
    
    def get_usage_summary(self):
        """Get a human-readable summary of how the document was used"""
        summary_parts = []
        
        if self.relevance_score:
            summary_parts.append(f"Relevance: {self.relevance_score:.2f}")
        
        if self.keywords_matched:
            keywords = ', '.join(self.keywords_matched[:3])  # Show first 3 keywords
            if len(self.keywords_matched) > 3:
                keywords += f" (and {len(self.keywords_matched) - 3} more)"
            summary_parts.append(f"Keywords: {keywords}")
        
        if self.user_feedback:
            summary_parts.append(f"Feedback: {self.get_user_feedback_display()}")
        
        return " | ".join(summary_parts) if summary_parts else _('Basic usage')
    
    def calculate_effectiveness(self):
        """Calculate effectiveness based on feedback and usage patterns"""
        score = 0.0
        
        # Base score from relevance
        if self.relevance_score:
            score += min(self.relevance_score * 10, 50)  # Max 50 points from relevance
        
        # Feedback scoring
        if self.user_feedback == 'positive':
            score += 40
        elif self.user_feedback == 'negative':
            score -= 20
        
        # Response helpfulness
        if self.response_helpful is True:
            score += 30
        elif self.response_helpful is False:
            score -= 15
        
        # Bonus for keyword matches
        if self.keywords_matched:
            score += min(len(self.keywords_matched) * 2, 20)  # Max 20 points for keywords
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
