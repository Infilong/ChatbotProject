"""
Hybrid Search Service: BM25 + Vector Embeddings for RAG
Modern implementation following 2025 best practices
"""

import logging
import numpy as np
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from django.conf import settings
from django.utils import timezone

# Import required libraries for hybrid search
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    from rank_bm25 import BM25Okapi
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
except ImportError as e:
    raise ImportError(f"Required packages not installed: {e}")

from .models import Document

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Search result with relevance scores"""
    document: Document
    chunk_text: str
    chunk_index: int
    bm25_score: float
    vector_score: float
    hybrid_score: float
    metadata: Dict[str, Any]

class HybridSearchService:
    """
    Modern Hybrid Search Service combining BM25 and Vector Embeddings
    Follows 2025 RAG best practices for efficient semantic + keyword search
    """
    
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize hybrid search service
        
        Args:
            embedding_model_name: Name of the sentence transformer model
        """
        self.embedding_model_name = embedding_model_name
        self.embedding_model = None
        self.vector_index = None
        self.bm25_index = None
        self.document_chunks = []
        self.chunk_metadata = []
        self.stemmer = PorterStemmer()
        
        # Download NLTK data if needed
        self._ensure_nltk_data()
        
        # Initialize embedding model
        self._load_embedding_model()
    
    def _ensure_nltk_data(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK data...")
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)
                nltk.download('stopwords', quiet=True)
            except Exception as e:
                logger.warning(f"Failed to download NLTK data: {e}")
    
    def _load_embedding_model(self):
        """Load sentence transformer model for embeddings"""
        try:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def chunk_text(self, text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        try:
            # Tokenize text
            tokens = word_tokenize(text.lower())
            
            if len(tokens) <= chunk_size:
                return [text]
            
            chunks = []
            start = 0
            
            while start < len(tokens):
                end = min(start + chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                
                # Reconstruct text from tokens (approximate)
                chunk_text = ' '.join(chunk_tokens)
                
                # Find actual sentence boundaries for cleaner chunks
                sentences = text.split('.')
                chunk_sentences = []
                current_length = 0
                
                for sentence in sentences:
                    sentence_tokens = len(word_tokenize(sentence.lower()))
                    if current_length + sentence_tokens <= chunk_size:
                        chunk_sentences.append(sentence.strip())
                        current_length += sentence_tokens
                    else:
                        break
                
                if chunk_sentences:
                    chunk_text = '. '.join(chunk_sentences)
                    if not chunk_text.endswith('.'):
                        chunk_text += '.'
                
                chunks.append(chunk_text)
                start += chunk_size - chunk_overlap
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            # Fallback: split by character count
            words = text.split()
            chunks = []
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                chunks.append(chunk)
            return chunks
    
    def preprocess_text_for_bm25(self, text: str) -> List[str]:
        """
        Preprocess text for BM25 indexing
        
        Args:
            text: Input text
            
        Returns:
            List of processed tokens
        """
        try:
            # Tokenize and convert to lowercase
            tokens = word_tokenize(text.lower())
            
            # Remove stopwords and non-alphabetic tokens
            try:
                stop_words = set(stopwords.words('english'))
            except:
                stop_words = set()
            
            # Filter and stem tokens
            processed_tokens = []
            for token in tokens:
                if (token.isalpha() and 
                    len(token) > 2 and 
                    token not in stop_words):
                    try:
                        stemmed = self.stemmer.stem(token)
                        processed_tokens.append(stemmed)
                    except:
                        processed_tokens.append(token)
            
            return processed_tokens
            
        except Exception as e:
            logger.error(f"Error preprocessing text for BM25: {e}")
            # Fallback: simple tokenization
            return text.lower().split()
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate vector embeddings for texts
        
        Args:
            texts: List of text chunks
            
        Returns:
            Numpy array of embeddings
        """
        if not self.embedding_model:
            raise RuntimeError("Embedding model not loaded")
        
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts")
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            logger.info(f"Generated embeddings shape: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def build_indexes(self, force_rebuild: bool = False) -> bool:
        """
        Build BM25 and FAISS vector indexes from all active documents
        
        Args:
            force_rebuild: Whether to force rebuild even if embeddings exist
            
        Returns:
            True if indexes built successfully
        """
        try:
            logger.info("Building hybrid search indexes...")
            
            # Get all active documents with content
            documents = Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False
            ).exclude(extracted_text='')
            
            if not documents.exists():
                logger.warning("No active documents found for indexing")
                return False
            
            # Prepare data structures
            all_chunks = []
            all_bm25_tokens = []
            chunk_metadata = []
            
            for doc in documents:
                # Check if we need to generate chunks and embeddings
                if not doc.chunks or force_rebuild:
                    # Generate chunks
                    chunks = self.chunk_text(doc.extracted_text)
                    doc.chunks = chunks
                    doc.embeddings_generated = False
                    doc.embedding_model = self.embedding_model_name
                    doc.save(update_fields=['chunks_json', 'chunks_count', 'embeddings_generated', 'embedding_model'])
                    logger.info(f"Generated {len(chunks)} chunks for document: {doc.name}")
                else:
                    chunks = doc.chunks
                
                # Process each chunk
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    
                    # Preprocess for BM25
                    bm25_tokens = self.preprocess_text_for_bm25(chunk)
                    all_bm25_tokens.append(bm25_tokens)
                    
                    # Store metadata
                    chunk_metadata.append({
                        'document_id': doc.id,
                        'document_name': doc.name,
                        'chunk_index': i,
                        'chunk_text': chunk
                    })
            
            # Build BM25 index
            logger.info("Building BM25 index...")
            self.bm25_index = BM25Okapi(all_bm25_tokens)
            
            # Generate embeddings and build FAISS index
            logger.info("Generating embeddings...")
            embeddings = self.generate_embeddings(all_chunks)
            
            # Build FAISS index
            logger.info("Building FAISS vector index...")
            dimension = embeddings.shape[1]
            self.vector_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            self.vector_index.add(embeddings.astype('float32'))
            
            # Store data
            self.document_chunks = all_chunks
            self.chunk_metadata = chunk_metadata
            
            # Mark documents as having embeddings generated
            Document.objects.filter(
                id__in=[doc.id for doc in documents]
            ).update(embeddings_generated=True)
            
            logger.info(f"Hybrid search indexes built successfully:")
            logger.info(f"  - {len(all_chunks)} chunks indexed")
            logger.info(f"  - BM25 index: {len(all_bm25_tokens)} documents")
            logger.info(f"  - Vector index: {self.vector_index.ntotal} vectors")
            
            return True
            
        except Exception as e:
            logger.error(f"Error building indexes: {e}")
            return False
    
    def search_bm25(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Search using BM25 keyword matching
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of (chunk_index, score) tuples
        """
        if not self.bm25_index:
            return []
        
        try:
            # Preprocess query
            query_tokens = self.preprocess_text_for_bm25(query)
            
            if not query_tokens:
                return []
            
            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top-k results
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include non-zero scores
                    results.append((int(idx), float(scores[idx])))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in BM25 search: {e}")
            return []
    
    def search_vector(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Search using vector similarity
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of (chunk_index, score) tuples
        """
        if not self.vector_index or not self.embedding_model:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search vector index
            scores, indices = self.vector_index.search(
                query_embedding.astype('float32'), top_k
            )
            
            results = []
            for i in range(len(indices[0])):
                idx = indices[0][i]
                score = scores[0][i]
                if score > 0:  # Filter out zero scores
                    results.append((int(idx), float(score)))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    def hybrid_search(
        self, 
        query: str, 
        top_k: int = 5,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        min_score: float = 0.1
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining BM25 and vector similarity
        
        Args:
            query: Search query
            top_k: Number of top results to return
            bm25_weight: Weight for BM25 scores (0.0 - 1.0)
            vector_weight: Weight for vector scores (0.0 - 1.0)
            min_score: Minimum hybrid score threshold
            
        Returns:
            List of SearchResult objects sorted by hybrid score
        """
        try:
            # Ensure indexes are built
            if not self.bm25_index or not self.vector_index:
                logger.info("Indexes not found, building them...")
                if not self.build_indexes():
                    logger.error("Failed to build indexes")
                    return []
            
            # Search both indexes
            bm25_results = self.search_bm25(query, top_k * 2)  # Get more results for fusion
            vector_results = self.search_vector(query, top_k * 2)
            
            # Normalize scores
            def normalize_scores(results):
                if not results:
                    return {}
                scores = [score for _, score in results]
                if max(scores) == 0:
                    return {}
                return {idx: score / max(scores) for idx, score in results}
            
            bm25_normalized = normalize_scores(bm25_results)
            vector_normalized = normalize_scores(vector_results)
            
            # Combine scores
            all_indices = set(bm25_normalized.keys()) | set(vector_normalized.keys())
            
            combined_results = []
            for idx in all_indices:
                bm25_score = bm25_normalized.get(idx, 0.0)
                vector_score = vector_normalized.get(idx, 0.0)
                
                # Calculate hybrid score
                hybrid_score = (bm25_weight * bm25_score) + (vector_weight * vector_score)
                
                if hybrid_score >= min_score and idx < len(self.chunk_metadata):
                    metadata = self.chunk_metadata[idx]
                    
                    # Get document
                    try:
                        document = Document.objects.get(id=metadata['document_id'])
                        
                        result = SearchResult(
                            document=document,
                            chunk_text=metadata['chunk_text'],
                            chunk_index=metadata['chunk_index'],
                            bm25_score=bm25_score,
                            vector_score=vector_score,
                            hybrid_score=hybrid_score,
                            metadata=metadata
                        )
                        combined_results.append(result)
                        
                    except Document.DoesNotExist:
                        logger.warning(f"Document {metadata['document_id']} not found")
                        continue
            
            # Sort by hybrid score and return top_k
            combined_results.sort(key=lambda x: x.hybrid_score, reverse=True)
            
            logger.info(f"Hybrid search for '{query}' found {len(combined_results)} results")
            for i, result in enumerate(combined_results[:3]):  # Log top 3
                logger.info(f"  {i+1}. {result.document.name} (score: {result.hybrid_score:.3f})")
            
            return combined_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []
    
    def get_search_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about the search indexes
        
        Returns:
            Dictionary with index statistics
        """
        analytics = {
            'embedding_model': self.embedding_model_name,
            'total_chunks': len(self.document_chunks),
            'bm25_index_size': len(self.document_chunks) if self.bm25_index else 0,
            'vector_index_size': self.vector_index.ntotal if self.vector_index else 0,
            'documents_indexed': len(set(meta['document_id'] for meta in self.chunk_metadata)),
            'indexes_built': bool(self.bm25_index and self.vector_index)
        }
        
        return analytics

# Global instance
hybrid_search_service = HybridSearchService()