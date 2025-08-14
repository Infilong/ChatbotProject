#!/usr/bin/env python3
"""
Debug the chunking algorithm step by step
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from documents.models import Document

def debug_chunking():
    """Debug the FAQ chunking step by step"""
    
    print("=== DEBUGGING FAQ CHUNKING ALGORITHM ===")
    print("=" * 60)
    
    # Get the document
    docs = list(Document.objects.filter(is_active=True, extracted_text__isnull=False).exclude(extracted_text=''))
    doc = docs[0]
    text = doc.extracted_text
    
    print(f"Full document length: {len(text)} characters")
    print()
    
    # Debug the splitting by **
    print("STEP 1: Split by **")
    sections = text.split('**')
    print(f"Split into {len(sections)} sections:")
    
    for i, section in enumerate(sections):
        if not section.strip():
            continue
        print(f"Section {i}: '{section.strip()[:100]}{'...' if len(section.strip()) > 100 else ''}'")
        if '?' in section:
            print(f"  -> Contains question mark")
            if section.strip().endswith('?'):
                print(f"  -> ENDS with question mark")
        print()
    
    print("=" * 40)
    print("STEP 2: Find the security question specifically")
    
    # Find sections that contain security
    for i, section in enumerate(sections):
        if 'security' in section.lower():
            print(f"Section {i} contains 'security':")
            print(f"'{section}'")
            print(f"Length: {len(section)} chars")
            print(f"Ends with '?': {section.strip().endswith('?')}")
            print()

if __name__ == "__main__":
    debug_chunking()