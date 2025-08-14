#!/usr/bin/env python3
"""
Simple debug for data security query
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from documents.hybrid_search import hybrid_search_service
from documents.models import Document

def debug_simple():
    """Simple debug without async"""
    
    query = "how do datapro protect data security"
    
    print("=== DEBUGGING DATA SECURITY QUERY ===")
    print(f"Query: '{query}'")
    print("=" * 60)
    
    # Check what documents we have
    print("STEP 1: Checking available documents...")
    docs = list(Document.objects.filter(is_active=True, extracted_text__isnull=False).exclude(extracted_text=''))
    print(f"Found {len(docs)} active documents with content:")
    
    for doc in docs:
        print(f"- {doc.name} (ID: {doc.id})")
        print(f"  Content length: {len(doc.extracted_text)} characters")
        
        # Check if document contains data security related terms
        security_terms = ['security', 'protect', 'data', 'privacy', 'encryption', 'safe', 'secure']
        found_terms = []
        content_lower = doc.extracted_text.lower()
        
        for term in security_terms:
            if term in content_lower:
                found_terms.append(term)
        
        if found_terms:
            print(f"  [YES] Contains security terms: {found_terms}")
            
            # Show a snippet around security content
            for search_term in ['security', 'data protection', 'protect']:
                if search_term in content_lower:
                    pos = content_lower.find(search_term)
                    start = max(0, pos - 100)
                    end = min(len(doc.extracted_text), pos + 200)
                    snippet = doc.extracted_text[start:end].replace('\n', ' ').strip()
                    print(f"  Context around '{search_term}':")
                    print(f"    ...{snippet}...")
                    break
        else:
            print(f"  [NO] No obvious security terms found")
        print()
    
    # Test hybrid search
    print("STEP 2: Testing hybrid search...")
    try:
        search_results = hybrid_search_service.hybrid_search(query, top_k=5, min_score=0.05)
        
        if search_results:
            print(f"[YES] Hybrid search found {len(search_results)} results:")
            for i, result in enumerate(search_results, 1):
                print(f"  {i}. Document: {result.document.name}")
                print(f"     Hybrid Score: {result.hybrid_score:.3f}")
                print(f"     BM25 Score: {result.bm25_score:.3f}")
                print(f"     Vector Score: {result.vector_score:.3f}")
                chunk_preview = result.chunk_text[:200].replace('\n', ' ').strip()
                print(f"     Chunk: {chunk_preview}...")
                print()
        else:
            print("[NO] Hybrid search found NO results")
    
    except Exception as e:
        print(f"[ERROR] Hybrid search error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with simpler queries
    print("STEP 3: Testing simpler queries...")
    simple_queries = [
        "security",
        "data",
        "protect",
        "privacy"
    ]
    
    for test_query in simple_queries:
        print(f"\nTesting: '{test_query}'")
        try:
            results = hybrid_search_service.hybrid_search(test_query, top_k=1, min_score=0.05)
            if results:
                print(f"  [YES] Found {len(results)} results (score: {results[0].hybrid_score:.3f})")
                chunk = results[0].chunk_text[:100].replace('\n', ' ').strip()
                print(f"  Chunk: {chunk}...")
            else:
                print(f"  [NO] No results")
        except Exception as e:
            print(f"  [ERROR] Error: {e}")

if __name__ == "__main__":
    debug_simple()