#!/usr/bin/env python3
"""
Debug the exact chunking logic step by step
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from documents.models import Document

def debug_chunking_logic():
    """Debug the exact chunking logic for FAQ"""
    
    print("=== DEBUGGING EXACT FAQ CHUNKING LOGIC ===")
    print("=" * 60)
    
    # Get document
    docs = list(Document.objects.filter(is_active=True, extracted_text__isnull=False).exclude(extracted_text=''))
    doc = docs[0]
    text = doc.extracted_text
    max_words = 300
    
    # Replicate the chunking algorithm step by step
    print("Simulating _chunk_faq_text() algorithm:")
    print()
    
    # Split by questions marked with **
    sections = text.split('**')
    chunks = []
    current_chunk = ""
    
    print(f"Total sections after split: {len(sections)}")
    print()
    
    for i, section in enumerate(sections):
        if not section.strip():
            print(f"Section {i}: (empty, skipping)")
            continue
        
        section_preview = section.strip()[:100] + ("..." if len(section.strip()) > 100 else "")
        print(f"Section {i}: '{section_preview}'")
        
        # If this looks like a question (ends with ?)
        if section.strip().endswith('?'):
            print(f"  -> This is a QUESTION (ends with ?)")
            
            # Start a new chunk with this question
            if current_chunk and len(current_chunk.split()) > 50:
                print(f"  -> Current chunk has {len(current_chunk.split())} words (>50), saving it:")
                print(f"     '{current_chunk[:100]}...'")
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            current_chunk = f"**{section}**"
            print(f"  -> Started new chunk: '**{section.strip()[:50]}...**'")
            
        else:
            # This is likely an answer or content
            section_text = section.strip()
            print(f"  -> This is CONTENT/ANSWER")
            
            if current_chunk:
                test_chunk = current_chunk + " " + section_text
                test_words = len(test_chunk.split())
                print(f"  -> Test chunk would have {test_words} words (max: {max_words})")
                
                if test_words <= max_words:
                    current_chunk = test_chunk
                    print(f"  -> Added to current chunk (now {test_words} words)")
                else:
                    # Current chunk is getting too big, save it
                    if current_chunk:
                        print(f"  -> Chunk too big, saving current chunk ({len(current_chunk.split())} words):")
                        print(f"     '{current_chunk[:100]}...'")
                        chunks.append(current_chunk.strip())
                    current_chunk = section_text
                    print(f"  -> Started new chunk with this section")
            else:
                current_chunk = section_text
                print(f"  -> Started new chunk with this section (no current chunk)")
        
        # Check if this is the security-related section
        if 'security' in section.lower() or 'privacy' in section.lower():
            print(f"  *** SECURITY-RELATED SECTION FOUND! ***")
            print(f"      Current chunk: '{current_chunk[:200]}...'")
        
        print(f"  Current chunk status: {len(current_chunk.split()) if current_chunk else 0} words")
        print()
    
    # Don't forget the last chunk
    if current_chunk.strip():
        print("Adding final chunk:")
        print(f"'{current_chunk[:100]}...'")
        chunks.append(current_chunk.strip())
    
    # Filter out very short chunks
    chunks = [chunk for chunk in chunks if len(chunk.split()) > 10]
    
    print("=" * 40)
    print(f"FINAL RESULT: {len(chunks)} chunks created")
    print()
    
    for i, chunk in enumerate(chunks, 1):
        print(f"CHUNK {i} ({len(chunk.split())} words):")
        print(f"'{chunk[:200]}...'")
        if 'security' in chunk.lower():
            print("*** CONTAINS SECURITY INFO! ***")
        print()

if __name__ == "__main__":
    debug_chunking_logic()