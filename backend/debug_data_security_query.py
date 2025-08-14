#!/usr/bin/env python3
"""
Debug why "how do datapro protect data security" query isn't finding relevant information
"""
import os
import sys
import django
import asyncio

# Setup Django environment
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from documents.hybrid_search import hybrid_search_service
from documents.knowledge_base import KnowledgeBase
from documents.models import Document
from chat.llm_services import LLMManager

async def debug_data_security_query():
    """Debug the data security query step by step"""
    
    query = "how do datapro protect data security"
    
    print("=== DEBUGGING DATA SECURITY QUERY ===")
    print(f"Query: '{query}'")
    print("=" * 60)
    
    # Step 1: Check what documents we have and their content
    print("STEP 1: Checking available documents...")
    docs = Document.objects.filter(is_active=True, extracted_text__isnull=False).exclude(extracted_text='')
    print(f"Found {docs.count()} active documents with content:")
    
    for doc in docs:
        print(f"- {doc.name} (ID: {doc.id})")
        print(f"  Categories: {doc.category}")
        print(f"  Content length: {len(doc.extracted_text)} characters")
        
        # Check if document contains data security related terms
        security_terms = ['security', 'protect', 'data', 'privacy', 'encryption', 'safe', 'secure']
        found_terms = []
        content_lower = doc.extracted_text.lower()
        
        for term in security_terms:
            if term in content_lower:
                found_terms.append(term)
        
        if found_terms:
            print(f"  ✅ Contains security terms: {found_terms}")
            
            # Show a snippet around security content
            for term in ['security', 'data protection', 'protect']:
                if term in content_lower:
                    pos = content_lower.find(term)
                    start = max(0, pos - 100)
                    end = min(len(doc.extracted_text), pos + 200)
                    snippet = doc.extracted_text[start:end]
                    print(f"  Security snippet around '{term}':")
                    print(f"    ...{snippet}...")
                    break
        else:
            print(f"  ❌ No obvious security terms found")
        print()
    
    # Step 2: Test hybrid search directly
    print("STEP 2: Testing hybrid search...")
    try:
        search_results = hybrid_search_service.hybrid_search(query, top_k=5, min_score=0.05)
        
        if search_results:
            print(f"✅ Hybrid search found {len(search_results)} results:")
            for i, result in enumerate(search_results, 1):
                print(f"  {i}. Document: {result.document.name}")
                print(f"     Hybrid Score: {result.hybrid_score:.3f}")
                print(f"     BM25 Score: {result.bm25_score:.3f}")
                print(f"     Vector Score: {result.vector_score:.3f}")
                print(f"     Chunk: {result.chunk_text[:150]}...")
                print()
        else:
            print("❌ Hybrid search found NO results")
    
    except Exception as e:
        print(f"❌ Hybrid search error: {e}")
    
    # Step 3: Test knowledge base integration
    print("STEP 3: Testing knowledge base integration...")
    try:
        context, docs = KnowledgeBase.get_knowledge_context(query, max_documents=3)
        
        if docs and context:
            print(f"✅ Knowledge base found {len(docs)} documents")
            print(f"Context length: {len(context)} characters")
            print("Context preview:")
            print("-" * 40)
            print(context[:500] + "..." if len(context) > 500 else context)
            print("-" * 40)
        else:
            print("❌ Knowledge base found NO relevant documents")
    
    except Exception as e:
        print(f"❌ Knowledge base error: {e}")
    
    # Step 4: Test full LLM pipeline
    print("STEP 4: Testing full LLM pipeline...")
    try:
        response, sources = await LLMManager.generate_chat_response(
            user_message=query,
            conversation_history=None,
            use_knowledge_base=True,
            language='en'
        )
        
        print(f"LLM Response Length: {len(response)} characters")
        print("LLM Response:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        if sources:
            print(f"Sources used: {len(sources)} documents")
            for source in sources:
                print(f"  - {source.name}")
        else:
            print("No sources used")
    
    except Exception as e:
        print(f"❌ LLM pipeline error: {e}")
    
    # Step 5: Test with various related queries
    print("STEP 5: Testing related queries...")
    related_queries = [
        "data security",
        "protect data", 
        "data protection",
        "security measures",
        "privacy protection"
    ]
    
    for test_query in related_queries:
        print(f"\nTesting: '{test_query}'")
        try:
            results = hybrid_search_service.hybrid_search(test_query, top_k=2, min_score=0.05)
            if results:
                print(f"  ✅ Found {len(results)} results (best score: {results[0].hybrid_score:.3f})")
            else:
                print(f"  ❌ No results")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_data_security_query())