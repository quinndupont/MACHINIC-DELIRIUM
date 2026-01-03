import os
import json
import numpy as np
import tiktoken
from openai import OpenAI
import pickle
import re

def cosine_similarity(query_embeddings, doc_embeddings):
    """Compute cosine similarity between query and document embeddings using numpy."""
    # Normalize embeddings
    query_norm = query_embeddings / (np.linalg.norm(query_embeddings, axis=1, keepdims=True) + 1e-8)
    doc_norm = doc_embeddings / (np.linalg.norm(doc_embeddings, axis=1, keepdims=True) + 1e-8)
    # Compute cosine similarity
    return np.dot(query_norm, doc_norm.T)

class RAGSystem:
    def __init__(self, text_path, api_key, model="text-embedding-3-small"):
        self.client = OpenAI(api_key=api_key)
        self.text_path = text_path
        self.model = model
        self.chunk_size = 1000 # tokens
        self.chunk_overlap = 100
        self.cache_file = "embeddings_cache.pkl"
        
        self.chunks = []
        self.chunk_metadata = []  # Store chapter info for each chunk
        self.embeddings = None
        
        self.load_or_create_embeddings()

    def load_text(self):
        with open(self.text_path, 'r', encoding='utf-8') as f:
            return f.read()

    def parse_chapters(self, text):
        """Parse markdown to identify chapters and their structure."""
        lines = text.split('\n')
        chapters = []
        current_chapter = None
        chapter_num = 0
        pre_chapter_content = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for h1 headings (#) - major chapters
            if line.startswith('# ') and not line.startswith('##'):
                # If we have pre-chapter content, create a chapter for it
                if pre_chapter_content and not current_chapter:
                    chapter_num += 1
                    current_chapter = {
                        'num': chapter_num,
                        'title': 'Introduction',
                        'content': pre_chapter_content,
                        'subsections': []
                    }
                    pre_chapter_content = []
                
                if current_chapter:
                    chapters.append(current_chapter)
                
                chapter_title = line[2:].strip()
                chapter_num += 1
                current_chapter = {
                    'num': chapter_num,
                    'title': chapter_title,
                    'content': [],
                    'subsections': []
                }
                i += 1
                continue
            
            # Check for h3 headings (###) - these are also major chapters
            if line.startswith('### '):
                # If we have pre-chapter content, create a chapter for it
                if pre_chapter_content and not current_chapter:
                    chapter_num += 1
                    current_chapter = {
                        'num': chapter_num,
                        'title': 'Introduction',
                        'content': pre_chapter_content,
                        'subsections': []
                    }
                    pre_chapter_content = []
                
                if current_chapter:
                    chapters.append(current_chapter)
                
                chapter_title = line[4:].strip()
                chapter_num += 1
                current_chapter = {
                    'num': chapter_num,
                    'title': chapter_title,
                    'content': [],
                    'subsections': []
                }
                i += 1
                continue
            
            # Check for h4 headings (####) - subsections
            if line.startswith('#### '):
                subsection_title = line[5:].strip()
                if current_chapter:
                    current_chapter['subsections'].append({
                        'title': subsection_title,
                        'start_line': len(current_chapter['content'])
                    })
                    current_chapter['content'].append(line)
                else:
                    pre_chapter_content.append(line)
                i += 1
                continue
            
            # Regular content
            if current_chapter:
                current_chapter['content'].append(line)
            else:
                pre_chapter_content.append(line)
            i += 1
        
        # Add any remaining pre-chapter content as a chapter
        if pre_chapter_content and not current_chapter:
            chapter_num += 1
            current_chapter = {
                'num': chapter_num,
                'title': 'Introduction',
                'content': pre_chapter_content,
                'subsections': []
            }
        
        # Add last chapter
        if current_chapter:
            chapters.append(current_chapter)
        
        return chapters

    def create_chunks(self, text):
        """Create chunks with chapter context preserved."""
        chapters = self.parse_chapters(text)
        enc = tiktoken.encoding_for_model("gpt-4")
        chunks = []
        metadata = []
        
        for chapter in chapters:
            chapter_text = '\n'.join(chapter['content'])
            chapter_tokens = enc.encode(chapter_text)
            
            # Build chapter header for context
            chapter_header = f"Chapter {chapter['num']}: {chapter['title']}\n\n"
            
            # If chapter is small enough, create single chunk
            if len(chapter_tokens) <= self.chunk_size:
                chunk_text = chapter_header + chapter_text
                chunks.append(chunk_text)
                metadata.append({
                    'chapter_num': chapter['num'],
                    'chapter_title': chapter['title'],
                    'subsection': None
                })
            else:
                # Split chapter into multiple chunks with overlap
                lines = chapter['content']
                current_chunk_lines = []
                current_chunk_tokens = 0
                chunk_start_idx = 0
                
                for line_idx, line in enumerate(lines):
                    line_tokens = len(enc.encode(line))
                    
                    # Check if adding this line would exceed chunk size
                    if current_chunk_tokens + line_tokens > self.chunk_size and current_chunk_lines:
                        # Save current chunk
                        chunk_content = '\n'.join(current_chunk_lines)
                        chunk_text = chapter_header + chunk_content
                        chunks.append(chunk_text)
                        
                        # Determine subsection for this chunk
                        subsection_title = None
                        for sub in reversed(chapter['subsections']):
                            if sub['start_line'] <= chunk_start_idx:
                                subsection_title = sub['title']
                                break
                        
                        metadata.append({
                            'chapter_num': chapter['num'],
                            'chapter_title': chapter['title'],
                            'subsection': subsection_title
                        })
                        
                        # Start new chunk with overlap (keep last 10 lines)
                        overlap_size = min(10, len(current_chunk_lines))
                        current_chunk_lines = current_chunk_lines[-overlap_size:] + [line]
                        current_chunk_tokens = sum(len(enc.encode(l)) for l in current_chunk_lines)
                        chunk_start_idx = line_idx - overlap_size
                    else:
                        current_chunk_lines.append(line)
                        current_chunk_tokens += line_tokens
                
                # Add final chunk
                if current_chunk_lines:
                    chunk_content = '\n'.join(current_chunk_lines)
                    chunk_text = chapter_header + chunk_content
                    chunks.append(chunk_text)
                    
                    subsection_title = None
                    for sub in reversed(chapter['subsections']):
                        if sub['start_line'] <= chunk_start_idx:
                            subsection_title = sub['title']
                            break
                    
                    metadata.append({
                        'chapter_num': chapter['num'],
                        'chapter_title': chapter['title'],
                        'subsection': subsection_title
                    })
        
        return chunks, metadata

    def get_embeddings(self, texts):
        # Process in batches to avoid API limits
        batch_size = 100
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.client.embeddings.create(input=batch, model=self.model)
            embeddings.extend([data.embedding for data in response.data])
        return np.array(embeddings)

    def load_or_create_embeddings(self):
        if os.path.exists(self.cache_file):
            print("Loading embeddings from cache...")
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)
                self.chunks = data['chunks']
                self.chunk_metadata = data.get('chunk_metadata', [])
                self.embeddings = data['embeddings']
        else:
            print("Generating embeddings (this may take a minute)...")
            text = self.load_text()
            self.chunks, self.chunk_metadata = self.create_chunks(text)
            self.embeddings = self.get_embeddings(self.chunks)
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump({
                    'chunks': self.chunks,
                    'chunk_metadata': self.chunk_metadata,
                    'embeddings': self.embeddings
                }, f)
            print("Embeddings generated and saved.")

    def exact_search(self, query_text, k=5):
        """Perform exact text/keyword search across chunks."""
        query_lower = query_text.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        scores = []
        for idx, chunk in enumerate(self.chunks):
            chunk_lower = chunk.lower()
            chunk_words = set(re.findall(r'\b\w+\b', chunk_lower))
            
            # Calculate match score: number of matching words + exact phrase matches
            word_matches = len(query_words.intersection(chunk_words))
            exact_phrase_count = chunk_lower.count(query_lower)
            
            # Weight exact phrase matches more heavily
            score = word_matches + (exact_phrase_count * 10)
            
            if score > 0:
                scores.append((idx, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        top_k_indices = [idx for idx, _ in scores[:k]]
        
        results = []
        for idx in top_k_indices:
            chunk_data = {
                'text': self.chunks[idx],
                'metadata': self.chunk_metadata[idx] if idx < len(self.chunk_metadata) else {},
                'score': dict(scores)[idx],
                'search_type': 'exact'
            }
            results.append(chunk_data)
        
        return results
    
    def semantic_search(self, query_text, k=5):
        """Perform semantic search using embeddings."""
        query_embedding = self.client.embeddings.create(
            input=[query_text], model=self.model
        ).data[0].embedding
        
        similarities = cosine_similarity(np.array([query_embedding]), self.embeddings)[0]
        top_k_indices = similarities.argsort()[-k:][::-1]
        
        results = []
        for idx in top_k_indices:
            chunk_data = {
                'text': self.chunks[idx],
                'metadata': self.chunk_metadata[idx] if idx < len(self.chunk_metadata) else {},
                'score': float(similarities[idx]),
                'search_type': 'semantic'
            }
            results.append(chunk_data)
        
        return results
    
    def hybrid_search(self, query_text, k=5, semantic_weight=0.7, exact_weight=0.3):
        """Combine semantic and exact search results using weighted scores."""
        # Get results from both search methods
        semantic_results = self.semantic_search(query_text, k=k*2)
        exact_results = self.exact_search(query_text, k=k*2)
        
        # Create index mapping: chunk text -> chunk index
        chunk_to_idx = {chunk: idx for idx, chunk in enumerate(self.chunks)}
        
        # Normalize scores and combine
        combined_scores = {}
        
        # Normalize semantic scores (they're already 0-1 from cosine similarity)
        if semantic_results:
            max_semantic = max(r['score'] for r in semantic_results)
            min_semantic = min(r['score'] for r in semantic_results)
            semantic_range = max_semantic - min_semantic if max_semantic != min_semantic else 1
            
            for result in semantic_results:
                chunk_text = result['text']
                idx = chunk_to_idx.get(chunk_text)
                if idx is not None:
                    normalized_score = (result['score'] - min_semantic) / semantic_range if semantic_range > 0 else 0
                    combined_scores[idx] = {
                        'chunk': result,
                        'semantic_score': normalized_score * semantic_weight,
                        'exact_score': 0
                    }
        
        # Normalize exact scores
        if exact_results:
            max_exact = max(r['score'] for r in exact_results)
            min_exact = min(r['score'] for r in exact_results)
            exact_range = max_exact - min_exact if max_exact != min_exact else 1
            
            for result in exact_results:
                chunk_text = result['text']
                idx = chunk_to_idx.get(chunk_text)
                if idx is not None:
                    normalized_score = (result['score'] - min_exact) / exact_range if exact_range > 0 else 0
                    
                    if idx in combined_scores:
                        combined_scores[idx]['exact_score'] = normalized_score * exact_weight
                    else:
                        combined_scores[idx] = {
                            'chunk': result,
                            'semantic_score': 0,
                            'exact_score': normalized_score * exact_weight
                        }
        
        # Calculate combined scores
        final_results = []
        for idx, data in combined_scores.items():
            combined_score = data['semantic_score'] + data['exact_score']
            chunk_data = data['chunk'].copy()
            chunk_data['combined_score'] = combined_score
            chunk_data['search_type'] = 'hybrid'
            final_results.append(chunk_data)
        
        # Sort by combined score and return top k
        final_results.sort(key=lambda x: x['combined_score'], reverse=True)
        return final_results[:k]
    
    def query(self, query_text, k=5, search_mode='hybrid'):
        """
        Query the RAG system and return chunks with metadata.
        
        Args:
            query_text: The search query
            k: Number of results to return
            search_mode: 'semantic', 'exact', or 'hybrid' (default)
        """
        if search_mode == 'semantic':
            return self.semantic_search(query_text, k=k)
        elif search_mode == 'exact':
            return self.exact_search(query_text, k=k)
        else:  # hybrid
            return self.hybrid_search(query_text, k=k)

