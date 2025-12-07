"""
RAG (Retrieval-Augmented Generation) System
Handles document chunking and text search
Uses TF-IDF for lightweight semantic search without heavy ML dependencies
"""

import os
import re
import math
import hashlib
from typing import List, Dict, Optional
from collections import Counter


class TextChunker:
    """Split text into overlapping chunks for better retrieval"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[Dict]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or not text.strip():
            return []
        
        # Clean text
        text = text.strip()
        
        # Split by sentences first for better context
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_length + 1  # +1 for space
            else:
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'char_count': len(chunk_text),
                        'chunk_id': len(chunks)
                    })
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk) + len(current_chunk)
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'char_count': len(chunk_text),
                'chunk_id': len(chunks)
            })
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter empty sentences and clean
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get sentences for overlap"""
        if not sentences:
            return []
        
        # Get last few sentences for overlap
        overlap_chars = 0
        overlap_sentences = []
        
        for sentence in reversed(sentences):
            if overlap_chars + len(sentence) <= self.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_chars += len(sentence)
            else:
                break
        
        return overlap_sentences


class SimpleVectorStore:
    """
    Simple text search using TF-IDF
    Lightweight alternative that doesn't require heavy ML dependencies
    """
    
    def __init__(self):
        self.documents = []
        self.doc_freqs = Counter()  # Document frequency for each term
        self.total_docs = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Convert to lowercase and extract words
        text = text.lower()
        # Remove punctuation and split
        words = re.findall(r'\b[a-zA-Zà-ÿÀ-Ÿ0-9]+\b', text)
        # Filter very short words
        return [w for w in words if len(w) > 2]
    
    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute term frequency"""
        tf = Counter(tokens)
        total = len(tokens)
        if total == 0:
            return {}
        return {term: count / total for term, count in tf.items()}
    
    def _compute_idf(self, term: str) -> float:
        """Compute inverse document frequency"""
        if self.total_docs == 0:
            return 0
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0
        return math.log(self.total_docs / df)
    
    def add_documents(self, chunks: List[Dict], document_id: str = None):
        """Add document chunks to the store"""
        if not chunks:
            return
        
        for chunk in chunks:
            chunk['document_id'] = document_id
            tokens = self._tokenize(chunk['text'])
            chunk['tokens'] = tokens
            chunk['tf'] = self._compute_tf(tokens)
            
            # Update document frequencies
            unique_terms = set(tokens)
            for term in unique_terms:
                self.doc_freqs[term] += 1
            
            self.documents.append(chunk)
            self.total_docs += 1
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar documents using TF-IDF"""
        if not self.documents:
            return []
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.documents[:top_k]
        
        # Compute query TF-IDF
        query_tf = self._compute_tf(query_tokens)
        
        # Score each document
        scores = []
        for i, doc in enumerate(self.documents):
            score = 0
            for term in query_tokens:
                if term in doc['tf']:
                    tf = doc['tf'][term]
                    idf = self._compute_idf(term)
                    score += tf * idf
            scores.append((score, i))
        
        # Sort by score (descending)
        scores.sort(reverse=True, key=lambda x: x[0])
        
        # Return top k results
        results = []
        for score, idx in scores[:top_k]:
            doc = self.documents[idx].copy()
            doc['score'] = score
            # Remove internal fields
            doc.pop('tokens', None)
            doc.pop('tf', None)
            results.append(doc)
        
        return results
    
    def get_all_text(self) -> str:
        """Get all document text concatenated"""
        return '\n\n'.join([doc['text'] for doc in self.documents])
    
    def clear(self):
        """Clear the store"""
        self.documents = []
        self.doc_freqs = Counter()
        self.total_docs = 0


class RAGSystem:
    """Main RAG system combining chunking and text search"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        self.vector_store = SimpleVectorStore()
        self.document_hashes = set()
    
    def add_document(self, text: str, document_id: str = None) -> int:
        """
        Add a document to the RAG system
        
        Args:
            text: Document text
            document_id: Optional document identifier
            
        Returns:
            Number of chunks created
        """
        # Check for duplicate documents
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.document_hashes:
            return 0
        
        self.document_hashes.add(text_hash)
        
        # Chunk the text
        chunks = self.chunker.chunk_text(text)
        
        # Add to vector store
        self.vector_store.add_documents(chunks, document_id)
        
        return len(chunks)
    
    def get_relevant_context(self, query: str, top_k: int = 5) -> str:
        """
        Get relevant context for a query
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
            
        Returns:
            Concatenated relevant text
        """
        results = self.vector_store.search(query, top_k)
        
        if not results:
            return self.vector_store.get_all_text()[:3000]  # Fallback to first 3000 chars
        
        context_parts = []
        for result in results:
            context_parts.append(result['text'])
        
        return '\n\n---\n\n'.join(context_parts)
    
    def get_full_context(self) -> str:
        """Get all document content"""
        return self.vector_store.get_all_text()
    
    def clear(self):
        """Clear all documents"""
        self.vector_store.clear()
        self.document_hashes.clear()
    
    def get_stats(self) -> Dict:
        """Get statistics about the stored documents"""
        return {
            'total_chunks': len(self.vector_store.documents),
            'unique_documents': len(self.document_hashes)
        }
