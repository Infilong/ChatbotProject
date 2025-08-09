#!/usr/bin/env python
"""
Test script for the knowledge base system integration
"""

import os
import sys
import asyncio
import django

# Setup Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from documents.knowledge_base import KnowledgeBase
from chat.llm_services import LLMManager


async def test_knowledge_base():
    """Test the knowledge base integration"""
    
    print("=== TESTING KNOWLEDGE BASE INTEGRATION ===\n")
    
    # Test 1: Search for relevant documents
    print("Test 1: Searching for documents about 'customer service'")
    docs = KnowledgeBase.search_relevant_documents("customer service", limit=5)
    print(f"Found {len(docs)} relevant documents:")
    for doc in docs:
        score = doc.get_relevance_score("customer service")
        print(f"  - {doc.name} (relevance: {score:.2f})")
        print(f"    Extracted text length: {len(doc.extracted_text)} characters")
        print(f"    AI Summary: {doc.ai_summary[:100]}...")
        print(f"    Keywords: {doc.ai_keywords[:5]}")
        print()
    
    # Test 2: Get knowledge context for LLM
    print("\nTest 2: Getting knowledge context for LLM")
    context, used_docs = KnowledgeBase.get_knowledge_context("customer service hours")
    print(f"Context length: {len(context)} characters")
    print(f"Used documents: {[doc.name for doc in used_docs]}")
    print(f"Context preview: {context[:200]}...")
    print()
    
    # Test 3: Test LLM response with knowledge base
    print("\nTest 3: Testing LLM response with knowledge base")
    try:
        question = "What are the customer service hours?"
        response, metadata = await LLMManager.generate_chat_response(
            user_message=question,
            conversation_history=[],
            use_knowledge_base=True
        )
        
        print(f"Question: {question}")
        print(f"Response: {response}")
        print(f"Metadata: {metadata}")
        
        if 'knowledge_context_used' in metadata:
            print(f"Knowledge context was used: {metadata['knowledge_context_used']}")
        
        if 'referenced_documents' in metadata:
            print(f"Referenced documents: {[doc.name for doc in metadata['referenced_documents']]}")
    
    except Exception as e:
        print(f"Error testing LLM integration: {e}")
    
    print("\n=== KNOWLEDGE BASE TEST COMPLETED ===")


if __name__ == "__main__":
    asyncio.run(test_knowledge_base())