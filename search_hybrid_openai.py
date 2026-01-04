#!/usr/bin/env python3
"""
Hybrid search: combines semantic (FAISS) and keyword matching using OpenAI embeddings
Usage: python search_hybrid_openai.py <index_path> <chunks_json> <query_text> <k> [api_key]
Output: JSON array of indices (most similar first)
"""

import sys
import json
import os
import numpy as np
import faiss
from openai import OpenAI
import re

def keyword_search(chunks, query, k):
    """Find chunks containing query keywords with improved exact matching."""
    query_lower = query.lower()
    query_original = query  # Keep original for exact case-sensitive match
    
    # Extract words (including hyphenated words)
    query_words = set(re.findall(r'\b[\w-]+\b', query_lower))
    # Also try splitting on hyphens for compound names
    query_words.update(re.findall(r'\w+', query_lower))
    
    scores = []
    for idx, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        chunk_original = chunks[idx]  # Keep original for exact match
        
        # Exact phrase match (case-insensitive) - highest priority
        exact_phrase_count_ci = chunk_lower.count(query_lower)
        
        # Exact phrase match (case-sensitive) - even higher priority
        exact_phrase_count_cs = chunk_original.count(query_original)
        
        # Word matches (including hyphenated words)
        chunk_words = set(re.findall(r'\b[\w-]+\b', chunk_lower))
        chunk_words.update(re.findall(r'\w+', chunk_lower))
        word_matches = len(query_words.intersection(chunk_words))
        
        # Calculate score with heavy weighting for exact matches
        # Case-sensitive exact match gets highest score
        score = (exact_phrase_count_cs * 100) + (exact_phrase_count_ci * 50) + word_matches
        
        if score > 0:
            scores.append((idx, score))
    
    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in scores[:k]]

def main():
    if len(sys.argv) < 5:
        print(json.dumps({'error': 'Usage: python search_hybrid_openai.py <index_path> <chunks_json> <query_text> <k> [api_key]'}), file=sys.stderr)
        sys.exit(1)
    
    index_path = sys.argv[1]
    chunks_json_path = sys.argv[2]
    query_text = sys.argv[3]
    k = int(sys.argv[4])
    api_key = sys.argv[5] if len(sys.argv) > 5 else os.getenv('OPENAI_API_KEY', '')
    
    if not api_key:
        print(json.dumps({'error': 'OpenAI API key required (as argument or OPENAI_API_KEY env var)'}), file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load chunks
        with open(chunks_json_path, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        chunks = chunks_data['chunks']
        
        # Load FAISS index
        index = faiss.read_index(index_path)
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Step 1: Semantic search (FAISS)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query_text
        )
        query_embedding = np.array(response.data[0].embedding, dtype='float32').reshape(1, -1)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        semantic_similarities, semantic_indices = index.search(query_embedding, k * 2)  # Get more for combining
        
        # Step 2: Keyword search
        keyword_indices = keyword_search(chunks, query_text, k * 2)
        
        # Step 3: Combine results
        # Create score maps
        semantic_scores = {}
        for i, idx in enumerate(semantic_indices[0]):
            semantic_scores[int(idx)] = float(semantic_similarities[0][i])
        
        keyword_scores = {}
        for i, idx in enumerate(keyword_indices):
            keyword_scores[idx] = float(len(keyword_indices) - i)  # Higher score for earlier matches
        
        # Check for exact matches
        exact_matches = []
        query_lower = query_text.lower()
        query_original = query_text
        for idx, chunk in enumerate(chunks):
            if query_original in chunk or query_lower in chunk.lower():
                exact_matches.append(idx)
        
        # Combine scores
        all_indices = set(semantic_indices[0].tolist()) | set(keyword_indices) | set(exact_matches)
        
        final_scores = []
        for idx in all_indices:
            semantic_norm = semantic_scores.get(idx, 0.0)
            keyword_score = keyword_scores.get(idx, 0.0)
            
            # Normalize keyword score to 0-1 range
            if keyword_indices:
                keyword_norm = keyword_score / len(keyword_indices)
            else:
                keyword_norm = 0.0
            
            # Boost exact matches
            exact_boost = 0.6 if idx in exact_matches else 0.0
            
            # Combine with weights (semantic: 0.4, keyword: 0.3, exact: 0.6)
            combined = (semantic_norm * 0.4) + (keyword_norm * 0.3) + exact_boost
            
            final_scores.append((idx, combined, semantic_norm, keyword_norm))
        
        # Sort by combined score
        final_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get top k
        top_indices = [int(idx) for idx, _, _, _ in final_scores[:k]]
        top_similarities = [float(sim) for _, sim, _, _ in final_scores[:k]]
        top_combined = [float(comb) for _, comb, _, _ in final_scores[:k]]
        
        result = {
            'indices': top_indices,
            'similarities': top_similarities,
            'combined_scores': top_combined,
            'exact_matches': [int(idx) for idx in exact_matches[:k]]
        }
        
        print(json.dumps(result))
        
    except FileNotFoundError as e:
        print(json.dumps({'error': f'File not found: {str(e)}'}), file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON: {str(e)}'}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

