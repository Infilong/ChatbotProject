"""
Chat services for document-based intelligent responses.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.utils.translation import gettext_lazy as _
from documents.models import Document
from .models import AdminPrompt

logger = logging.getLogger(__name__)


class DocumentSearchService:
    """Service for searching and retrieving relevant documents"""
    
    @staticmethod
    def search_documents(query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant documents based on user query.
        Returns documents with relevance scores and excerpts.
        """
        if not query or not query.strip():
            return []
        
        # Get all active documents
        documents = Document.objects.filter(is_active=True)
        
        if not documents.exists():
            return []
        
        # Calculate relevance scores for each document
        document_scores = []
        for doc in documents:
            score = doc.get_relevance_score(query)
            if score > 0:  # Only include documents with some relevance
                excerpt = doc.get_excerpt(query, max_length=300)
                document_scores.append({
                    'document': doc,
                    'score': score,
                    'excerpt': excerpt,
                    'title': doc.name,
                    'category': doc.category or _('Uncategorized'),
                    'file_type': doc.file_type,
                })
        
        # Sort by relevance score (highest first) and return top results
        document_scores.sort(key=lambda x: x['score'], reverse=True)
        return document_scores[:limit]
    
    @staticmethod
    def has_relevant_documents(query: str, threshold: float = 0.5) -> bool:
        """Check if there are any documents relevant to the query"""
        results = DocumentSearchService.search_documents(query, limit=1)
        return len(results) > 0 and results[0]['score'] >= threshold


class ChatbotPromptService:
    """Service for generating document-based chatbot prompts"""
    
    @staticmethod
    def get_system_prompt(language: str = 'en') -> str:
        """Get the main system prompt for document-based responses"""
        try:
            # Get default system prompt
            prompt = AdminPrompt.objects.filter(
                prompt_type='system',
                language=language,
                is_active=True,
                is_default=True
            ).first()
            
            if prompt:
                prompt.increment_usage()
                return prompt.prompt_text
            
            # Fallback system prompt if no custom one exists
            return ChatbotPromptService._get_default_system_prompt(language)
            
        except Exception as e:
            logger.error(f"Error retrieving system prompt: {e}")
            return ChatbotPromptService._get_default_system_prompt(language)
    
    @staticmethod
    def _get_default_system_prompt(language: str = 'en') -> str:
        """Default system prompt for document-based responses"""
        if language == 'ja':
            return """あなたは、アップロードされた企業文書に基づいて回答する専門的なAIアシスタントです。

重要なルール:
1. **文書優先**: アップロードされた文書に関連情報がある場合は、必ずその情報を使用してください
2. **正確性**: 文書に基づく回答は、文書の内容に厳密に従ってください
3. **透明性**: 回答の根拠となる文書を明示してください
4. **制限**: 文書に情報がない場合のみ、一般的な知識で回答してください

回答形式:
- 関連文書がある場合: "文書「[文書名]」に基づいて回答いたします："で始める
- 文書がない場合: "アップロードされた文書には関連情報がありませんが、一般的には："で始める

常に丁寧で専門的な口調を保ち、正確で有用な情報を提供してください。"""
        else:
            return """You are a professional AI assistant that provides responses based on uploaded company documents.

CRITICAL RULES:
1. **DOCUMENT PRIORITY**: When uploaded documents contain relevant information, you MUST use that information as your primary source
2. **STRICT ACCURACY**: When responding based on documents, stick strictly to the document content
3. **TRANSPARENCY**: Always cite which document your answer is based on
4. **FALLBACK ONLY**: Only use general knowledge when no relevant documents are available

Response Format:
- When documents are relevant: Start with "Based on the document '[Document Name]': "
- When no documents available: Start with "No relevant documents found. Based on general knowledge: "

Always maintain a professional tone and provide accurate, helpful information."""
    
    @staticmethod
    def create_document_based_prompt(
        user_query: str, 
        relevant_docs: List[Dict[str, Any]], 
        language: str = 'en'
    ) -> str:
        """
        Create a comprehensive prompt that includes user query and relevant document context
        """
        system_prompt = ChatbotPromptService.get_system_prompt(language)
        
        if not relevant_docs:
            # No relevant documents found
            if language == 'ja':
                return f"""{system_prompt}

ユーザーの質問: {user_query}

注意: アップロードされた文書に関連情報がありません。一般的な知識に基づいて回答してください。"""
            else:
                return f"""{system_prompt}

User Query: {user_query}

Note: No relevant documents found in uploaded files. Please respond based on general knowledge."""
        
        # Build document context
        doc_context = ""
        for i, doc_info in enumerate(relevant_docs, 1):
            doc = doc_info['document']
            excerpt = doc_info['excerpt']
            
            if language == 'ja':
                doc_context += f"""
文書 {i}: 「{doc.name}」
カテゴリ: {doc.category or 'その他'}
関連箇所:
{excerpt}

---"""
            else:
                doc_context += f"""
Document {i}: "{doc.name}"
Category: {doc.category or 'Other'}
Relevant Content:
{excerpt}

---"""
        
        if language == 'ja':
            return f"""{system_prompt}

利用可能な関連文書:
{doc_context}

ユーザーの質問: {user_query}

上記の文書に基づいて、正確で有用な回答を提供してください。必ず参照した文書名を明記してください。"""
        else:
            return f"""{system_prompt}

Available Relevant Documents:
{doc_context}

User Query: {user_query}

Please provide an accurate and helpful response based on the above documents. Always cite the document name you're referencing."""


class DocumentBasedChatService:
    """Main service for document-based chat responses"""
    
    @staticmethod
    def prepare_response_context(user_message: str, language: str = 'en') -> Dict[str, Any]:
        """
        Prepare the complete context for generating a document-based response
        """
        # Search for relevant documents
        relevant_docs = DocumentSearchService.search_documents(user_message, limit=3)
        
        # Create the prompt with document context
        full_prompt = ChatbotPromptService.create_document_based_prompt(
            user_message, 
            relevant_docs, 
            language
        )
        
        # Prepare response metadata
        context = {
            'prompt': full_prompt,
            'has_relevant_docs': len(relevant_docs) > 0,
            'relevant_documents': relevant_docs,
            'document_count': len(relevant_docs),
            'search_query': user_message,
            'language': language
        }
        
        # Add document sources for transparency
        if relevant_docs:
            context['document_sources'] = [
                {
                    'name': doc_info['document'].name,
                    'category': doc_info['document'].category,
                    'relevance_score': round(doc_info['score'], 2),
                    'file_type': doc_info['document'].file_type
                }
                for doc_info in relevant_docs
            ]
        
        return context
    
    @staticmethod
    def get_instruction_prompt(prompt_type: str = 'instruction', language: str = 'en') -> str:
        """Get specific instruction prompts from AdminPrompt"""
        try:
            prompt = AdminPrompt.objects.filter(
                prompt_type=prompt_type,
                language=language,
                is_active=True,
                is_default=True
            ).first()
            
            if prompt:
                prompt.increment_usage()
                return prompt.prompt_text
                
        except Exception as e:
            logger.error(f"Error retrieving {prompt_type} prompt: {e}")
        
        return ""
    
    @staticmethod
    def log_document_usage(relevant_docs: List[Dict[str, Any]]):
        """Log document usage for analytics"""
        for doc_info in relevant_docs:
            try:
                doc = doc_info['document']
                doc.increment_reference()
                logger.info(f"Document '{doc.name}' referenced in chat response")
            except Exception as e:
                logger.error(f"Error logging document usage: {e}")


# Utility functions for template integration
def get_document_based_response_prompt(user_query: str, language: str = 'en') -> str:
    """
    Simple utility function to get a complete prompt for document-based responses
    """
    context = DocumentBasedChatService.prepare_response_context(user_query, language)
    return context['prompt']


def check_document_availability(query: str) -> bool:
    """Check if relevant documents are available for a query"""
    return DocumentSearchService.has_relevant_documents(query)