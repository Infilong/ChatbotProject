from django.db import models
from django.contrib.auth.models import User
from chat.models import Conversation, Message


class ConversationAnalysis(models.Model):
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    
    RESOLUTION_CHOICES = [
        ('resolved', 'Resolved'),
        ('pending', 'Pending'),
        ('escalated', 'Escalated'),
    ]
    
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='analysis')
    analyzed_at = models.DateTimeField(auto_now=True)
    
    # LangExtract analysis results
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    satisfaction_level = models.IntegerField()  # 1-10 scale
    issues_raised = models.JSONField(default=list)  # List of categorized problems
    urgency_indicators = models.JSONField(default=list)  # Urgent phrases with source
    resolution_status = models.CharField(max_length=10, choices=RESOLUTION_CHOICES)
    customer_intent = models.CharField(max_length=50)  # support/inquiry/complaint
    key_insights = models.JSONField(default=list)  # Actionable business intelligence
    
    # Source grounding data from LangExtract
    source_spans = models.JSONField(default=list)  # Text spans with exact locations
    confidence_score = models.FloatField(default=0.0)  # Analysis confidence
    
    # Processing metadata
    langextract_model_used = models.CharField(max_length=50)
    processing_time = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-analyzed_at']
        
    def __str__(self):
        return f"Analysis for Conversation {self.conversation.id} - {self.sentiment}"


class UserFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='feedback_entries')
    feedback_type = models.CharField(max_length=10, choices=Message.FEEDBACK_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Optional feedback details
    comment = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True)  # 1-5 star rating
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['user', 'message']  # One feedback per user per message
        
    def __str__(self):
        return f"{self.feedback_type} feedback by {self.user.username}"


class AnalyticsSummary(models.Model):
    date = models.DateField(unique=True)
    
    # Daily metrics
    total_conversations = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    unique_users = models.IntegerField(default=0)
    average_satisfaction = models.FloatField(default=0.0)
    
    # Sentiment distribution
    positive_conversations = models.IntegerField(default=0)
    negative_conversations = models.IntegerField(default=0)
    neutral_conversations = models.IntegerField(default=0)
    
    # Issue tracking
    total_issues_raised = models.IntegerField(default=0)
    resolved_issues = models.IntegerField(default=0)
    escalated_issues = models.IntegerField(default=0)
    
    # Performance metrics
    average_response_time = models.FloatField(default=0.0)
    bot_vs_human_ratio = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        
    def __str__(self):
        return f"Analytics Summary for {self.date}"


class DocumentUsage(models.Model):
    document = models.ForeignKey('documents.CompanyDocument', on_delete=models.CASCADE, related_name='usage_stats')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    
    # Usage details
    referenced_at = models.DateTimeField(auto_now_add=True)
    effectiveness_score = models.FloatField(null=True, blank=True)  # Based on user feedback
    search_query = models.CharField(max_length=200)  # What user searched for
    
    class Meta:
        ordering = ['-referenced_at']
        
    def __str__(self):
        return f"Document {self.document.title} used in Conversation {self.conversation.id}"
