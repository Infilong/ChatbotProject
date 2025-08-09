"""
Management command to process existing documents for knowledge base
"""

import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from documents.models import Document
from documents.document_processor import DocumentProcessor
from documents.knowledge_base import KnowledgeBase


class Command(BaseCommand):
    help = 'Process documents for knowledge base (extract text and generate AI analysis)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all documents',
        )
        parser.add_argument(
            '--unprocessed',
            action='store_true',
            help='Process only documents without extracted text',
        )
        parser.add_argument(
            '--document-id',
            type=int,
            help='Process specific document by ID',
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Process documents in specific category',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show knowledge base statistics',
        )

    def handle(self, *args, **options):
        if options['stats']:
            self.show_knowledge_base_stats()
            return
            
        if options['document_id']:
            asyncio.run(self.process_document_by_id(options['document_id']))
        elif options['all']:
            asyncio.run(self.process_all_documents())
        elif options['unprocessed']:
            asyncio.run(self.process_unprocessed_documents())
        elif options['category']:
            asyncio.run(self.process_documents_by_category(options['category']))
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify --all, --unprocessed, --document-id, --category, or --stats'
                )
            )

    async def process_document_by_id(self, doc_id):
        """Process specific document by ID"""
        try:
            document = await sync_to_async(Document.objects.get)(id=doc_id)
            self.stdout.write(f'Processing document: {document.name}')
            
            success = await DocumentProcessor.process_document(document)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully processed: {document.name}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to process: {document.name}')
                )
                
        except Document.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Document with ID {doc_id} not found')
            )

    async def process_all_documents(self):
        """Process all active documents"""
        documents = await sync_to_async(list)(Document.objects.filter(is_active=True, file__isnull=False))
        
        if not documents:
            self.stdout.write(
                self.style.WARNING('No active documents found')
            )
            return
        
        self.stdout.write(f'Processing {len(documents)} documents...')
        
        processed = 0
        failed = 0
        
        for document in documents:
            self.stdout.write(f'Processing: {document.name}')
            
            try:
                success = await DocumentProcessor.process_document(document)
                
                if success:
                    processed += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [OK] {document.name}')
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f'  [ERR] {document.name}')
                    )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  [ERR] {document.name}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nProcessing complete: {processed} successful, {failed} failed'
            )
        )

    async def process_unprocessed_documents(self):
        """Process only documents without extracted text"""
        documents = await sync_to_async(list)(Document.objects.filter(
            is_active=True,
            file__isnull=False,
            extracted_text=''
        ))
        
        if not documents:
            self.stdout.write(
                self.style.SUCCESS('All documents are already processed!')
            )
            return
        
        self.stdout.write(f'Processing {len(documents)} unprocessed documents...')
        
        processed = 0
        failed = 0
        
        for document in documents:
            self.stdout.write(f'Processing: {document.name}')
            
            try:
                success = await DocumentProcessor.process_document(document)
                
                if success:
                    processed += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [OK] {document.name}')
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f'  [ERR] {document.name}')
                    )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  [ERR] {document.name}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nProcessing complete: {processed} successful, {failed} failed'
            )
        )

    async def process_documents_by_category(self, category):
        """Process documents in specific category"""
        documents = await sync_to_async(list)(Document.objects.filter(
            is_active=True,
            file__isnull=False,
            category__icontains=category
        ))
        
        if not documents:
            self.stdout.write(
                self.style.WARNING(f'No documents found in category: {category}')
            )
            return
        
        self.stdout.write(f'Processing {len(documents)} documents in category "{category}"...')
        
        processed = 0
        failed = 0
        
        for document in documents:
            self.stdout.write(f'Processing: {document.name}')
            
            try:
                success = await DocumentProcessor.process_document(document)
                
                if success:
                    processed += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [OK] {document.name}')
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f'  [ERR] {document.name}')
                    )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  [ERR] {document.name}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nProcessing complete: {processed} successful, {failed} failed'
            )
        )

    def show_knowledge_base_stats(self):
        """Show knowledge base statistics"""
        self.stdout.write(
            self.style.SUCCESS('\n=== KNOWLEDGE BASE STATISTICS ===')
        )
        
        stats = KnowledgeBase.get_knowledge_summary()
        
        self.stdout.write(f"Total Documents: {stats['total_documents']}")
        self.stdout.write(f"Processed Documents: {stats['processed_documents']}")
        self.stdout.write(f"Processing Rate: {stats['processing_rate']:.1f}%")
        self.stdout.write(f"Total References: {stats['total_references']}")
        
        if stats['categories']:
            self.stdout.write(f"\nCategories: {', '.join(stats['categories'])}")
        
        if stats['top_documents']:
            self.stdout.write('\n=== TOP REFERENCED DOCUMENTS ===')
            for doc in stats['top_documents']:
                last_used = doc['last_used'] or 'Never'
                self.stdout.write(
                    f"• {doc['name']}: {doc['references']} refs, "
                    f"effectiveness {doc['effectiveness']:.1f}, "
                    f"last used: {last_used}"
                )
        
        # Show unprocessed documents
        unprocessed = Document.objects.filter(
            is_active=True,
            file__isnull=False,
            extracted_text=''
        ).count()
        
        if unprocessed > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[!] {unprocessed} documents need processing. '
                    'Run: python manage.py process_documents --unprocessed'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n[OK] All documents are processed!')
            )