"""
Test knowledge base integration
"""

import asyncio
from django.core.management.base import BaseCommand
from documents.knowledge_base import KnowledgeBase
from chat.llm_services import LLMManager


class Command(BaseCommand):
    help = 'Test the knowledge base integration'
    
    def handle(self, *args, **options):
        asyncio.run(self.test_knowledge_base())
    
    async def test_knowledge_base(self):
        """Test the knowledge base integration"""
        
        self.stdout.write(
            self.style.SUCCESS('=== TESTING KNOWLEDGE BASE INTEGRATION ===\n')
        )
        
        # Test 1: Search for relevant documents
        self.stdout.write("Test 1: Searching for documents about 'customer service'")
        docs = KnowledgeBase.search_relevant_documents("customer service", limit=5)
        self.stdout.write(f"Found {len(docs)} relevant documents:")
        
        for doc in docs:
            score = doc.get_relevance_score("customer service")
            self.stdout.write(f"  - {doc.name} (relevance: {score:.2f})")
            self.stdout.write(f"    Extracted text length: {len(doc.extracted_text)} characters")
            if doc.ai_summary:
                summary_preview = doc.ai_summary[:100] + "..." if len(doc.ai_summary) > 100 else doc.ai_summary
                self.stdout.write(f"    AI Summary: {summary_preview}")
            keywords_preview = doc.ai_keywords[:5] if len(doc.ai_keywords) > 5 else doc.ai_keywords
            self.stdout.write(f"    Keywords: {keywords_preview}")
            self.stdout.write("")
        
        # Test 2: Get knowledge context for LLM
        self.stdout.write("\nTest 2: Getting knowledge context for LLM")
        context, used_docs = KnowledgeBase.get_knowledge_context("customer service hours")
        self.stdout.write(f"Context length: {len(context)} characters")
        self.stdout.write(f"Used documents: {[doc.name for doc in used_docs]}")
        if context:
            context_preview = context[:200] + "..." if len(context) > 200 else context
            self.stdout.write(f"Context preview: {context_preview}")
        self.stdout.write("")
        
        # Test 3: Test LLM response with knowledge base
        self.stdout.write("\nTest 3: Testing LLM response with knowledge base")
        try:
            question = "What are the customer service hours?"
            response, metadata = await LLMManager.generate_chat_response(
                user_message=question,
                conversation_history=[],
                use_knowledge_base=True
            )
            
            self.stdout.write(f"Question: {question}")
            self.stdout.write(f"Response: {response}")
            
            if 'knowledge_context_used' in metadata:
                self.stdout.write(f"Knowledge context was used: {metadata['knowledge_context_used']}")
            
            if 'referenced_documents' in metadata:
                doc_names = [doc.name for doc in metadata['referenced_documents']]
                self.stdout.write(f"Referenced documents: {doc_names}")
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error testing LLM integration: {e}")
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n=== KNOWLEDGE BASE TEST COMPLETED ===')
        )