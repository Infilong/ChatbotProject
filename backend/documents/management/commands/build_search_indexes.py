"""
Django management command to build hybrid search indexes (BM25 + Vector Embeddings)
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from documents.hybrid_search import hybrid_search_service
from documents.models import Document
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Build hybrid search indexes for RAG (BM25 + Vector Embeddings)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-rebuild',
            action='store_true',
            help='Force rebuild even if embeddings exist',
        )
        parser.add_argument(
            '--embedding-model',
            type=str,
            default='all-MiniLM-L6-v2',
            help='Sentence transformer model name',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS('Building Hybrid Search Indexes (BM25 + Vector Embeddings)')
        )
        
        try:
            # Check active documents
            doc_count = Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False
            ).exclude(extracted_text='').count()
            
            if doc_count == 0:
                self.stdout.write(
                    self.style.WARNING('No active documents with extracted text found')
                )
                return
            
            self.stdout.write(f"Found {doc_count} active documents to index")
            
            # Set embedding model if specified
            if options['embedding_model']:
                hybrid_search_service.embedding_model_name = options['embedding_model']
                self.stdout.write(f"Using embedding model: {options['embedding_model']}")
            
            # Build indexes
            self.stdout.write("Building indexes...")
            success = hybrid_search_service.build_indexes(
                force_rebuild=options['force_rebuild']
            )
            
            if success:
                # Get analytics
                analytics = hybrid_search_service.get_search_analytics()
                
                duration = timezone.now() - start_time
                
                self.stdout.write(
                    self.style.SUCCESS('\nHybrid Search Indexes Built Successfully!')
                )
                self.stdout.write(f"Duration: {duration.total_seconds():.1f} seconds")
                self.stdout.write(f"Analytics:")
                self.stdout.write(f"   - Documents indexed: {analytics['documents_indexed']}")
                self.stdout.write(f"   - Total chunks: {analytics['total_chunks']}")
                self.stdout.write(f"   - BM25 index size: {analytics['bm25_index_size']}")
                self.stdout.write(f"   - Vector index size: {analytics['vector_index_size']}")
                self.stdout.write(f"   - Embedding model: {analytics['embedding_model']}")
                
                # Test search
                self.stdout.write("\nTesting search functionality...")
                test_queries = [
                    "how to contact you",
                    "pricing information",
                    "support for teams", 
                    "data analytics services"
                ]
                
                for query in test_queries:
                    results = hybrid_search_service.hybrid_search(query, top_k=2)
                    if results:
                        self.stdout.write(f"   SUCCESS '{query}': {len(results)} results (top score: {results[0].hybrid_score:.3f})")
                    else:
                        self.stdout.write(f"   NO RESULTS '{query}': No results found")
                
                self.stdout.write(
                    self.style.SUCCESS('\nHybrid Search System Ready!')
                )
                
            else:
                raise CommandError("Failed to build indexes")
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\nIndex building interrupted by user')
            )
        except Exception as e:
            duration = timezone.now() - start_time
            self.stdout.write(
                self.style.ERROR(f'\nError building indexes: {e}')
            )
            self.stdout.write(f"Duration before error: {duration.total_seconds():.1f} seconds")
            raise CommandError(f"Index building failed: {e}")