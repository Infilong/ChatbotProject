"""
Message-level Analysis Service
Analyzes individual user messages for detailed insights
"""

import logging
from typing import Dict, List, Any
from django.utils import timezone
from chat.models import Message

logger = logging.getLogger(__name__)


class MessageAnalysisService:
    """Service for analyzing individual user messages"""

    def __init__(self):
        """Initialize the message analysis service"""
        # Common issue keywords for detection
        self.issue_keywords = {
            'login_problems': ['login', 'log in', 'sign in', 'password', 'access', 'account locked', 'authentication'],
            'billing_issues': ['bill', 'billing', 'charge', 'payment', 'invoice', 'refund', 'cost', 'price', 'subscription'],
            'technical_problems': ['error', 'bug', 'broken', 'not working', 'crash', 'freeze', 'slow', 'loading'],
            'feature_requests': ['feature', 'add', 'new', 'improve', 'enhancement', 'suggestion', 'would like'],
            'integration_issues': ['api', 'integration', 'connect', 'sync', 'webhook', 'oauth', 'authentication'],
            'performance_issues': ['slow', 'timeout', 'performance', 'lag', 'delay', 'speed', 'loading'],
            'data_issues': ['data', 'export', 'import', 'backup', 'restore', 'migration', 'transfer'],
            'ui_ux_feedback': ['interface', 'design', 'user experience', 'confusing', 'hard to find', 'navigation'],
            'documentation_gaps': ['documentation', 'docs', 'guide', 'tutorial', 'how to', 'instructions', 'manual'],
            'security_concerns': ['security', 'privacy', 'permission', 'access control', 'data protection']
        }
        
        # Satisfaction indicators
        self.satisfaction_indicators = {
            'positive': ['thank', 'great', 'perfect', 'excellent', 'helpful', 'solved', 'fixed', 'working', 'good'],
            'negative': ['frustrated', 'annoying', 'terrible', 'awful', 'useless', 'broken', 'disappointed', 'angry'],
            'neutral': ['ok', 'fine', 'understand', 'see', 'got it']
        }
        
        # Importance/urgency indicators
        self.urgency_indicators = {
            'high': ['urgent', 'immediately', 'asap', 'critical', 'emergency', 'important', 'business critical'],
            'medium': ['soon', 'when possible', 'convenient', 'sometime', 'eventually'],
            'low': ['whenever', 'no rush', 'not urgent', 'low priority']
        }
        
        # Service availability and system status indicators (inherently high priority)
        self.service_status_indicators = {
            'service_down': ['service unavailable', 'service down', 'service is down', 'server down', 'server is down', 'system down', 'system is down', 'outage', 'service outage', 'site down', 'website down'],
            'access_blocked': ['cannot access', 'cant access', 'unable to access', 'access denied', 'login failed', 'authentication failed', 'blocked access', 'access blocked'],
            'system_errors': ['system error', 'server error', '500 error', '404 error', 'database error', 'connection failed', 'internal error', 'application error'],
            'data_loss': ['data lost', 'data missing', 'files missing', 'backup failed', 'corruption', 'data corrupted', 'data not found'],
            'security_issues': ['security breach', 'unauthorized access', 'hacked', 'compromised', 'suspicious activity', 'security alert']
        }
        
        # FAQ potential indicators
        self.faq_indicators = [
            'how do i', 'how to', 'where is', 'what is', 'can i', 'is it possible',
            'do you support', 'does it work', 'why', 'when', 'where can i find'
        ]

    def analyze_user_message(self, message: Message) -> Dict[str, Any]:
        """
        Analyze a single user message for detailed insights
        
        Args:
            message: Message object to analyze
            
        Returns:
            Dict containing detailed analysis
        """
        if message.sender_type != 'user':
            return {}
        
        content = message.content.lower()
        
        analysis = {
            'issues_raised': self._detect_issues(content),
            'satisfaction_level': self._analyze_satisfaction(content),
            'importance_level': self._analyze_importance(content),
            'doc_improvement_potential': self._assess_doc_potential(content),
            'faq_potential': self._assess_faq_potential(content),
            'analysis_timestamp': timezone.now().isoformat(),
            'message_uuid': str(message.uuid)
        }
        
        return analysis

    def _detect_issues(self, content: str) -> List[Dict[str, Any]]:
        """Detect issues raised in the message"""
        detected_issues = []
        
        for issue_type, keywords in self.issue_keywords.items():
            relevance_score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in content:
                    relevance_score += 1
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                # Calculate confidence based on keyword matches
                confidence = min(relevance_score / len(keywords) * 100, 100)
                
                detected_issues.append({
                    'issue_type': issue_type.replace('_', ' ').title(),
                    'confidence': round(confidence, 1),
                    'matched_keywords': matched_keywords,
                    'description': self._generate_issue_description(issue_type, matched_keywords)
                })
        
        # Sort by confidence
        detected_issues.sort(key=lambda x: x['confidence'], reverse=True)
        return detected_issues[:3]  # Return top 3 most relevant issues

    def _analyze_satisfaction(self, content: str) -> Dict[str, Any]:
        """Analyze satisfaction level from message content"""
        positive_count = sum(1 for word in self.satisfaction_indicators['positive'] if word in content)
        negative_count = sum(1 for word in self.satisfaction_indicators['negative'] if word in content)
        neutral_count = sum(1 for word in self.satisfaction_indicators['neutral'] if word in content)
        
        total_indicators = positive_count + negative_count + neutral_count
        
        if total_indicators == 0:
            satisfaction = 'unknown'
            confidence = 0
            score = 5  # Neutral score
        elif positive_count > negative_count:
            satisfaction = 'satisfied'
            confidence = (positive_count / total_indicators) * 100
            score = 7 + (positive_count / max(total_indicators, 1)) * 3  # 7-10 range
        elif negative_count > positive_count:
            satisfaction = 'dissatisfied'
            confidence = (negative_count / total_indicators) * 100
            score = 4 - (negative_count / max(total_indicators, 1)) * 3  # 1-4 range
        else:
            satisfaction = 'neutral'
            confidence = (neutral_count / total_indicators) * 100
            score = 5  # Neutral score
        
        return {
            'level': satisfaction,
            'confidence': round(confidence, 1),
            'score': round(score, 1),
            'indicators': {
                'positive': positive_count,
                'negative': negative_count,
                'neutral': neutral_count
            }
        }

    def _analyze_importance(self, content: str) -> Dict[str, Any]:
        """Analyze importance/urgency level"""
        high_count = sum(1 for phrase in self.urgency_indicators['high'] if phrase in content)
        medium_count = sum(1 for phrase in self.urgency_indicators['medium'] if phrase in content)
        low_count = sum(1 for phrase in self.urgency_indicators['low'] if phrase in content)
        
        # Check for service status issues (automatically high priority)
        service_issues = 0
        service_issue_types = []
        for issue_category, keywords in self.service_status_indicators.items():
            if any(keyword in content for keyword in keywords):
                service_issues += 3  # Each service issue adds 3 points (same as explicit high urgency)
                service_issue_types.append(issue_category)
        
        # Check for implicit urgency indicators
        implicit_urgency = 0
        if any(phrase in content for phrase in ['need help', 'stuck', 'blocking', 'cant continue']):
            implicit_urgency += 1
        if any(phrase in content for phrase in ['deadline', 'client', 'presentation', 'meeting']):
            implicit_urgency += 2
        
        # Additional business impact indicators
        business_impact = 0
        if any(phrase in content for phrase in ['production', 'live environment', 'customers affected', 'revenue impact']):
            business_impact += 2
        if any(phrase in content for phrase in ['all users', 'everyone', 'company wide', 'entire system']):
            business_impact += 1
        
        total_urgency = high_count * 3 + medium_count * 2 + low_count * 1 + implicit_urgency + service_issues + business_impact
        
        # Determine importance level
        if total_urgency >= 5 or high_count > 0 or service_issues > 0:
            importance = 'high'
            priority = 'urgent'
            if service_issues > 0:
                priority = 'critical'  # Service issues get critical priority
        elif total_urgency >= 2 or medium_count > 0:
            importance = 'medium'
            priority = 'normal'
        else:
            importance = 'low'
            priority = 'low'
        
        return {
            'level': importance,
            'priority': priority,
            'urgency_score': total_urgency,
            'indicators': {
                'high_urgency': high_count,
                'medium_urgency': medium_count,
                'low_urgency': low_count,
                'implicit_urgency': implicit_urgency,
                'service_issues': service_issues,
                'service_issue_types': service_issue_types,
                'business_impact': business_impact
            }
        }

    def _assess_doc_potential(self, content: str) -> Dict[str, Any]:
        """Assess potential for documentation improvement"""
        doc_indicators = 0
        improvement_areas = []
        
        # Check for documentation-related keywords
        if any(word in content for word in ['documentation', 'docs', 'guide', 'tutorial']):
            doc_indicators += 3
            improvement_areas.append('Missing or unclear documentation')
        
        # Check for "how to" questions
        if any(phrase in content for phrase in self.faq_indicators):
            doc_indicators += 2
            improvement_areas.append('Common question that could be documented')
        
        # Check for confusion indicators
        if any(word in content for word in ['confused', 'unclear', 'dont understand', 'how do i']):
            doc_indicators += 2
            improvement_areas.append('Process or feature needs clearer explanation')
        
        # Check for feature discovery issues
        if any(phrase in content for phrase in ['where is', 'cant find', 'how to access', 'where can i']):
            doc_indicators += 1
            improvement_areas.append('Feature discoverability issue')
        
        potential_level = 'high' if doc_indicators >= 4 else 'medium' if doc_indicators >= 2 else 'low'
        
        return {
            'potential_level': potential_level,
            'score': min(doc_indicators * 20, 100),  # Convert to percentage
            'improvement_areas': improvement_areas,
            'suggested_actions': self._generate_doc_suggestions(improvement_areas)
        }

    def _assess_faq_potential(self, content: str) -> Dict[str, Any]:
        """Assess if this could be a frequently asked question"""
        faq_score = 0
        question_type = 'other'
        
        # Check for question patterns
        if any(phrase in content for phrase in self.faq_indicators):
            faq_score += 30
            question_type = 'how_to'
        
        # Check for common question words
        question_words = ['what', 'why', 'when', 'where', 'who', 'which']
        if any(word in content for word in question_words):
            faq_score += 20
            if question_type == 'other':
                question_type = 'general_inquiry'
        
        # Check for feature-related questions
        if any(word in content for word in ['feature', 'function', 'capability', 'support']):
            faq_score += 15
            question_type = 'feature_inquiry'
        
        # Check for troubleshooting questions
        if any(word in content for word in ['problem', 'issue', 'error', 'trouble']):
            faq_score += 25
            question_type = 'troubleshooting'
        
        # Boost score for concise, clear questions
        if len(content.split()) < 20 and '?' in content:
            faq_score += 10
        
        faq_level = 'high' if faq_score >= 50 else 'medium' if faq_score >= 30 else 'low'
        
        return {
            'faq_potential': faq_level,
            'score': min(faq_score, 100),
            'question_type': question_type,
            'recommended_faq_title': self._generate_faq_title(content, question_type),
            'should_add_to_faq': faq_score >= 40
        }

    def _generate_issue_description(self, issue_type: str, keywords: List[str]) -> str:
        """Generate a human-readable description of the detected issue"""
        descriptions = {
            'login_problems': f"User experiencing authentication or login difficulties. Keywords: {', '.join(keywords)}",
            'billing_issues': f"User has questions or problems related to billing or payments. Keywords: {', '.join(keywords)}",
            'technical_problems': f"User reporting technical errors or system malfunctions. Keywords: {', '.join(keywords)}",
            'feature_requests': f"User requesting new features or improvements. Keywords: {', '.join(keywords)}",
            'integration_issues': f"User having problems with API or system integrations. Keywords: {', '.join(keywords)}",
            'performance_issues': f"User experiencing slow performance or delays. Keywords: {', '.join(keywords)}",
            'data_issues': f"User has concerns about data handling or migration. Keywords: {', '.join(keywords)}",
            'ui_ux_feedback': f"User providing feedback about interface or user experience. Keywords: {', '.join(keywords)}",
            'documentation_gaps': f"User indicates missing or unclear documentation. Keywords: {', '.join(keywords)}",
            'security_concerns': f"User has security or privacy related questions. Keywords: {', '.join(keywords)}"
        }
        return descriptions.get(issue_type, f"Issue detected with keywords: {', '.join(keywords)}")

    def _generate_doc_suggestions(self, improvement_areas: List[str]) -> List[str]:
        """Generate specific documentation improvement suggestions"""
        suggestions = []
        
        if 'Missing or unclear documentation' in improvement_areas:
            suggestions.append('Create or update documentation for this topic')
        if 'Common question that could be documented' in improvement_areas:
            suggestions.append('Add this question to FAQ or knowledge base')
        if 'Process or feature needs clearer explanation' in improvement_areas:
            suggestions.append('Improve step-by-step guides and add screenshots')
        if 'Feature discoverability issue' in improvement_areas:
            suggestions.append('Improve navigation or add feature highlights')
        
        return suggestions

    def _generate_faq_title(self, content: str, question_type: str) -> str:
        """Generate a potential FAQ title from the message content"""
        # Extract the main question
        content_clean = content.strip()
        
        if question_type == 'how_to':
            if content_clean.startswith('how'):
                return content_clean.split('?')[0] + '?'
            else:
                return f"How to {content_clean.split('how to')[-1].split('?')[0].strip()}?"
        elif question_type == 'troubleshooting':
            return f"Troubleshooting: {content_clean.split('?')[0]}?"
        elif question_type == 'feature_inquiry':
            return f"Feature Question: {content_clean.split('?')[0]}?"
        else:
            # General cleanup for FAQ title
            title = content_clean.split('?')[0].strip()
            if len(title) > 80:
                title = title[:77] + "..."
            return title + '?'

    def analyze_conversation_messages(self, conversation) -> Dict[str, Any]:
        """Analyze all user messages in a conversation"""
        user_messages = conversation.messages.filter(sender_type='user')
        
        if not user_messages.exists():
            return {'error': 'No user messages found in conversation'}
        
        analyzed_messages = []
        summary_stats = {
            'total_messages': user_messages.count(),
            'issues_by_type': {},
            'satisfaction_distribution': {'satisfied': 0, 'dissatisfied': 0, 'neutral': 0, 'unknown': 0},
            'importance_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'doc_improvement_opportunities': 0,
            'high_faq_potential': 0
        }
        
        for message in user_messages:
            analysis = self.analyze_user_message(message)
            
            # Save analysis to message
            message.message_analysis = analysis
            message.save(update_fields=['message_analysis'])
            
            analyzed_messages.append({
                'message_id': str(message.uuid),
                'content_preview': message.content[:100] + '...' if len(message.content) > 100 else message.content,
                'timestamp': message.timestamp.isoformat(),
                'analysis': analysis
            })
            
            # Update summary stats
            if analysis.get('issues_raised'):
                for issue in analysis['issues_raised']:
                    issue_type = issue['issue_type']
                    summary_stats['issues_by_type'][issue_type] = summary_stats['issues_by_type'].get(issue_type, 0) + 1
            
            satisfaction = analysis.get('satisfaction_level', {}).get('level', 'unknown')
            summary_stats['satisfaction_distribution'][satisfaction] += 1
            
            importance = analysis.get('importance_level', {}).get('level', 'low')
            summary_stats['importance_distribution'][importance] += 1
            
            if analysis.get('doc_improvement_potential', {}).get('potential_level') in ['high', 'medium']:
                summary_stats['doc_improvement_opportunities'] += 1
            
            if analysis.get('faq_potential', {}).get('faq_potential') == 'high':
                summary_stats['high_faq_potential'] += 1
        
        return {
            'conversation_id': str(conversation.uuid),
            'analyzed_messages': analyzed_messages,
            'summary_stats': summary_stats,
            'analysis_timestamp': timezone.now().isoformat()
        }


# Global service instance
message_analysis_service = MessageAnalysisService()