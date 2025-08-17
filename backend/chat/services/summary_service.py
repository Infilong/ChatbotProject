"""
Summary Service for AI-powered conversation analysis and insights generation.
Leverages LangExtract analysis data and LLM APIs to create comprehensive summaries.
"""

import json
from datetime import datetime, timedelta
from django.db.models import Q, Count
from django.utils import timezone
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter

from ..models import Message, Conversation, ConversationSummary
from ..llm_services import LLMManager


class ConversationSummaryService:
    """Service for generating AI-powered conversation summaries"""
    
    def __init__(self):
        # LLM service will be initialized when needed using LLMManager
        pass
    
    async def generate_summary(
        self, 
        date_from: datetime, 
        date_to: datetime,
        min_importance_level: str = 'medium',
        title: str = None,
        user = None
    ) -> ConversationSummary:
        """
        Generate comprehensive summary of conversations using LangExtract data and LLM analysis
        """
        # Filter meaningful messages based on importance and content quality
        meaningful_messages = self._get_meaningful_messages(date_from, date_to, min_importance_level)
        
        # Extract structured data from LangExtract analysis
        analysis_data = self._extract_analysis_data(meaningful_messages)
        
        # Generate LLM-powered insights
        llm_insights = await self._generate_llm_insights(analysis_data, meaningful_messages)
        
        # Create summary title if not provided
        if not title:
            title = f"Conversation Analysis - {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}"
        
        # Create summary object
        summary = ConversationSummary.objects.create(
            title=title,
            description=f"AI-powered analysis of {len(meaningful_messages)} meaningful messages from {analysis_data['total_conversations']} conversations",
            date_from=date_from,
            date_to=date_to,
            min_importance_level=min_importance_level,
            total_conversations_analyzed=analysis_data['total_conversations'],
            total_messages_analyzed=analysis_data['total_messages'],
            meaningful_messages_count=len(meaningful_messages),
            important_topics=analysis_data['important_topics'],
            faq_gaps=analysis_data['faq_gaps'],
            doc_improvement_suggestions=analysis_data['doc_improvements'],
            user_satisfaction_trends=analysis_data['satisfaction_trends'],
            bot_performance_metrics=analysis_data['bot_performance'],
            topic_frequency_analysis=analysis_data['topic_frequency'],
            urgency_distribution=analysis_data['urgency_distribution'],
            question_types_analysis=analysis_data['question_types'],
            escalation_patterns=analysis_data['escalation_patterns'],
            executive_summary=llm_insights['executive_summary'],
            key_recommendations=llm_insights['recommendations'],
            generated_by=user,
            analysis_config={
                'min_importance_level': min_importance_level,
                'analysis_version': 'v1.0',
                'langextract_based': True,
                'llm_enhanced': True
            }
        )
        
        return summary
    
    def _get_meaningful_messages(self, date_from: datetime, date_to: datetime, min_importance_level: str) -> List[Message]:
        """Filter messages to include only meaningful ones based on importance and content quality"""
        
        # Map importance levels to filter criteria
        importance_hierarchy = {
            'low': ['low', 'medium', 'high', 'critical'],
            'medium': ['medium', 'high', 'critical'], 
            'high': ['high', 'critical'],
            'critical': ['critical']
        }
        
        allowed_importance_levels = importance_hierarchy.get(min_importance_level, ['medium', 'high', 'critical'])
        
        # Base query for user messages in date range with analysis data
        messages = Message.objects.filter(
            sender_type='user',
            timestamp__gte=date_from,
            timestamp__lte=date_to,
            message_analysis__isnull=False
        ).exclude(message_analysis={})
        
        meaningful_messages = []
        
        for message in messages:
            analysis = message.message_analysis
            
            # Skip if no proper analysis
            if not analysis or not analysis.get('importance_level'):
                continue
            
            importance_level = analysis.get('importance_level', {}).get('level', 'low')
            
            # Filter by importance level
            if importance_level not in allowed_importance_levels:
                continue
            
            # Skip meaningless content (very low importance with specific patterns)
            if self._is_meaningless_content(message.content, analysis):
                continue
            
            meaningful_messages.append(message)
        
        return meaningful_messages
    
    def _is_meaningless_content(self, content: str, analysis: Dict) -> bool:
        """Determine if message content is meaningless based on patterns and analysis"""
        
        # Check for very low importance with specific indicators
        importance = analysis.get('importance_level', {})
        if importance.get('level') == 'low' and importance.get('urgency_score', 0) <= 1:
            
            # Common meaningless patterns
            meaningless_patterns = [
                'who are you', 'hello', 'hi', 'hey', 'hahaha', 'lol', 'ok', 'okay',
                'test', 'testing', '123', 'abc', 'fdagr', 'asdf', 'qwerty'
            ]
            
            content_lower = content.lower().strip()
            
            # Check for gibberish (random characters)
            if len(content_lower) > 3 and any(pattern in content_lower for pattern in meaningless_patterns):
                return True
            
            # Check for very short messages with low FAQ potential
            faq_potential = analysis.get('faq_potential', {})
            if len(content.strip()) < 10 and faq_potential.get('score', 0) < 30:
                return True
        
        return False
    
    def _extract_analysis_data(self, messages: List[Message]) -> Dict[str, Any]:
        """Extract and aggregate structured data from LangExtract analysis"""
        
        # Initialize data structures
        topic_counter = Counter()
        satisfaction_levels = []
        urgency_levels = []
        question_types = []
        faq_candidates = []
        doc_improvements = []
        escalation_needed = []
        
        conversations = set()
        
        for message in messages:
            analysis = message.message_analysis
            conversations.add(message.conversation_id)
            
            # Extract topics from issues raised
            for issue in analysis.get('issues_raised', []):
                issue_type = issue.get('issue_type', 'unknown')
                confidence = issue.get('confidence', 0)
                if confidence > 50:  # Only high-confidence topics
                    topic_counter[issue_type] += 1
            
            # Satisfaction analysis
            satisfaction = analysis.get('satisfaction_level', {})
            if satisfaction.get('level'):
                satisfaction_levels.append({
                    'level': satisfaction.get('level'),
                    'score': satisfaction.get('score', 0),
                    'confidence': satisfaction.get('confidence', 0)
                })
            
            # Urgency analysis
            importance = analysis.get('importance_level', {})
            if importance.get('level'):
                urgency_levels.append({
                    'level': importance.get('level'),
                    'urgency_score': importance.get('urgency_score', 0),
                    'escalation_needed': importance.get('escalation_needed', False)
                })
            
            # FAQ potential analysis
            faq_data = analysis.get('faq_potential', {})
            if faq_data.get('score', 0) > 60:  # High FAQ potential
                faq_candidates.append({
                    'question': message.content,
                    'score': faq_data.get('score', 0),
                    'question_type': faq_data.get('question_type', 'general'),
                    'recommended_title': faq_data.get('recommended_faq_title', ''),
                    'should_add': faq_data.get('should_add_to_faq', False)
                })
            
            # Documentation improvement potential
            doc_potential = analysis.get('doc_improvement_potential', {})
            if doc_potential.get('score', 0) > 50:
                doc_improvements.append({
                    'question': message.content,
                    'score': doc_potential.get('score', 0),
                    'improvement_areas': doc_potential.get('improvement_areas', []),
                    'suggested_actions': doc_potential.get('suggested_actions', [])
                })
            
            # Escalation patterns
            if importance.get('escalation_needed', False):
                escalation_needed.append({
                    'content': message.content,
                    'urgency_score': importance.get('urgency_score', 0),
                    'business_impact': importance.get('business_impact', 'unknown')
                })
        
        # Process and rank topics
        important_topics = [
            {
                'topic': topic,
                'frequency': count,
                'percentage': round((count / len(messages)) * 100, 1)
            }
            for topic, count in topic_counter.most_common(10)
        ]
        
        # Calculate satisfaction trends
        satisfaction_trends = self._calculate_satisfaction_trends(satisfaction_levels)
        
        # Calculate urgency distribution
        urgency_distribution = self._calculate_urgency_distribution(urgency_levels)
        
        # Rank FAQ gaps by importance
        faq_gaps = sorted(faq_candidates, key=lambda x: x['score'], reverse=True)[:10]
        
        # Rank documentation improvements
        doc_improvements = sorted(doc_improvements, key=lambda x: x['score'], reverse=True)[:10]
        
        # Bot performance metrics (placeholder for now)
        bot_performance = {
            'total_user_messages': len(messages),
            'escalation_rate': len(escalation_needed) / len(messages) * 100 if messages else 0,
            'avg_satisfaction_score': sum(s['score'] for s in satisfaction_levels) / len(satisfaction_levels) if satisfaction_levels else 0
        }
        
        return {
            'total_conversations': len(conversations),
            'total_messages': len(messages),
            'important_topics': important_topics,
            'faq_gaps': faq_gaps,
            'doc_improvements': doc_improvements,
            'satisfaction_trends': satisfaction_trends,
            'bot_performance': bot_performance,
            'topic_frequency': dict(topic_counter.most_common(20)),
            'urgency_distribution': urgency_distribution,
            'question_types': self._analyze_question_types(messages),
            'escalation_patterns': {
                'total_escalations': len(escalation_needed),
                'escalation_rate': len(escalation_needed) / len(messages) * 100 if messages else 0,
                'escalation_details': escalation_needed[:5]  # Top 5 escalation cases
            }
        }
    
    def _calculate_satisfaction_trends(self, satisfaction_levels: List[Dict]) -> Dict:
        """Calculate satisfaction trends and distribution"""
        if not satisfaction_levels:
            return {}
        
        level_counts = Counter(s['level'] for s in satisfaction_levels)
        avg_score = sum(s['score'] for s in satisfaction_levels) / len(satisfaction_levels)
        
        return {
            'average_score': round(avg_score, 2),
            'distribution': dict(level_counts),
            'total_responses': len(satisfaction_levels),
            'positive_percentage': round((level_counts.get('positive', 0) + level_counts.get('very_positive', 0)) / len(satisfaction_levels) * 100, 1),
            'negative_percentage': round((level_counts.get('negative', 0) + level_counts.get('very_negative', 0)) / len(satisfaction_levels) * 100, 1)
        }
    
    def _calculate_urgency_distribution(self, urgency_levels: List[Dict]) -> Dict:
        """Calculate urgency level distribution"""
        if not urgency_levels:
            return {}
        
        level_counts = Counter(u['level'] for u in urgency_levels)
        avg_urgency_score = sum(u['urgency_score'] for u in urgency_levels) / len(urgency_levels)
        
        return {
            'distribution': dict(level_counts),
            'average_urgency_score': round(avg_urgency_score, 2),
            'high_urgency_percentage': round((level_counts.get('high', 0) + level_counts.get('critical', 0)) / len(urgency_levels) * 100, 1)
        }
    
    def _analyze_question_types(self, messages: List[Message]) -> Dict:
        """Analyze types of questions being asked"""
        question_types = Counter()
        
        for message in messages:
            analysis = message.message_analysis
            faq_data = analysis.get('faq_potential', {})
            question_type = faq_data.get('question_type', 'general')
            question_types[question_type] += 1
        
        return {
            'distribution': dict(question_types),
            'most_common': question_types.most_common(5)
        }
    
    async def _generate_llm_insights(self, analysis_data: Dict, messages: List[Message]) -> Dict[str, str]:
        """Generate executive summary and recommendations using LLM"""
        
        # Prepare data for LLM analysis
        prompt_data = {
            'total_conversations': analysis_data['total_conversations'],
            'total_messages': analysis_data['total_messages'],
            'top_topics': analysis_data['important_topics'][:5],
            'satisfaction_trends': analysis_data['satisfaction_trends'],
            'urgency_distribution': analysis_data['urgency_distribution'],
            'faq_gaps': analysis_data['faq_gaps'][:3],
            'doc_improvements': analysis_data['doc_improvements'][:3],
            'escalation_rate': analysis_data['escalation_patterns']['escalation_rate']
        }
        
        # Create LLM prompt for executive summary
        executive_summary_prompt = f"""
Analyze the following conversation data and provide a concise executive summary:

Data Overview:
- Analyzed {prompt_data['total_messages']} meaningful messages from {prompt_data['total_conversations']} conversations
- Average satisfaction score: {prompt_data['satisfaction_trends'].get('average_score', 'N/A')}
- Escalation rate: {prompt_data['escalation_rate']:.1f}%

Top Topics by Frequency:
{json.dumps(prompt_data['top_topics'], indent=2)}

Satisfaction Distribution:
{json.dumps(prompt_data['satisfaction_trends'].get('distribution', {}), indent=2)}

Urgency Distribution:
{json.dumps(prompt_data['urgency_distribution'].get('distribution', {}), indent=2)}

Top FAQ Gaps (Missing from current documentation):
{json.dumps(prompt_data['faq_gaps'], indent=2)}

Documentation Improvement Opportunities:
{json.dumps(prompt_data['doc_improvements'], indent=2)}

Please provide a comprehensive executive summary in 3-4 paragraphs that highlights:
1. Overall conversation trends and user behavior patterns
2. Key areas where users need help most frequently
3. Current bot performance and user satisfaction levels
4. Critical gaps in documentation or FAQ coverage

Write in a professional, data-driven tone suitable for business stakeholders.
"""

        # Create LLM prompt for recommendations
        recommendations_prompt = f"""
Based on the conversation analysis data provided below, generate specific, actionable recommendations:

{json.dumps(prompt_data, indent=2)}

Please provide 5-7 specific recommendations that address:
1. FAQ improvements (what questions should be added to FAQ)
2. Documentation enhancements (what topics need better coverage)
3. Bot response improvements (areas where bot could perform better)
4. User experience optimization (reducing escalations, improving satisfaction)
5. Content prioritization (what information should be most accessible)

Format each recommendation as a numbered list with:
- Clear action item
- Rationale based on the data
- Expected impact

Write in a professional, actionable tone suitable for product and content teams.
"""
        
        try:
            # Get LLM service using the existing LLMManager pattern
            llm_service = await LLMManager.get_active_service()
            
            # Generate executive summary using LLM
            executive_summary_response, _ = await llm_service.generate_response(
                messages=[{'role': 'user', 'content': executive_summary_prompt}],
                max_tokens=800
            )
            
            # Generate recommendations using LLM
            recommendations_response, _ = await llm_service.generate_response(
                messages=[{'role': 'user', 'content': recommendations_prompt}],
                max_tokens=1000
            )
            
            return {
                'executive_summary': executive_summary_response,
                'recommendations': recommendations_response
            }
            
        except Exception as e:
            # Fallback to template-based summary if LLM fails
            return {
                'executive_summary': self._generate_fallback_summary(analysis_data),
                'recommendations': self._generate_fallback_recommendations(analysis_data)
            }
    
    def _generate_fallback_summary(self, analysis_data: Dict) -> str:
        """Generate fallback summary if LLM is unavailable"""
        top_topic = analysis_data['important_topics'][0]['topic'] if analysis_data['important_topics'] else 'general inquiries'
        avg_satisfaction = analysis_data['satisfaction_trends'].get('average_score', 0)
        
        return f"""
Analysis of {analysis_data['total_messages']} meaningful messages from {analysis_data['total_conversations']} conversations reveals key insights about user interactions.

The most frequent topic of discussion is {top_topic}, indicating primary user interests and needs. User satisfaction trends show an average score of {avg_satisfaction:.1f}, with {analysis_data['satisfaction_trends'].get('positive_percentage', 0):.1f}% positive responses.

{len(analysis_data['faq_gaps'])} potential FAQ items were identified that could improve user self-service capabilities. Additionally, {len(analysis_data['doc_improvements'])} documentation improvement opportunities were detected.

The escalation rate of {analysis_data['escalation_patterns']['escalation_rate']:.1f}% suggests areas where bot responses could be enhanced to better address user needs.
"""
    
    def _generate_fallback_recommendations(self, analysis_data: Dict) -> str:
        """Generate fallback recommendations if LLM is unavailable"""
        recommendations = []
        
        if analysis_data['faq_gaps']:
            recommendations.append("1. Add frequently asked questions to FAQ section based on identified gaps")
        
        if analysis_data['doc_improvements']:
            recommendations.append("2. Enhance documentation coverage for topics with high improvement potential")
        
        if analysis_data['escalation_patterns']['escalation_rate'] > 10:
            recommendations.append("3. Improve bot responses to reduce escalation rate")
        
        if analysis_data['satisfaction_trends'].get('negative_percentage', 0) > 20:
            recommendations.append("4. Address user satisfaction issues through response quality improvements")
        
        recommendations.append("5. Monitor top conversation topics for content prioritization")
        
        return "\n".join(recommendations)