#!/usr/bin/env python3
"""
Hybrid search: combines semantic (FAISS) and keyword matching
Usage: python search_hybrid.py <index_path> <chunks_json> <query_text> <k>
Output: JSON array of indices (most similar first)
"""

import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
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
        print(json.dumps({'error': 'Usage: python search_hybrid.py <index_path> <chunks_json> <query_text> <k>'}), file=sys.stderr)
        sys.exit(1)
    
    index_path = sys.argv[1]
    chunks_json_path = sys.argv[2]
    query_text = sys.argv[3]
    k = int(sys.argv[4])
    
    try:
        # Load chunks
        with open(chunks_json_path, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        chunks = chunks_data['chunks']
        model_name = chunks_data.get('model', 'all-MiniLM-L6-v2')
        
        # Load FAISS index
        index = faiss.read_index(index_path)
        
        # Load embedding model
        model = SentenceTransformer(model_name)
        
        # Step 1: Semantic search (FAISS)
        query_embedding = model.encode(
            query_text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        query_vector = np.array([query_embedding], dtype='float32')
        faiss.normalize_L2(query_vector)
        
        semantic_k = min(k * 2, len(chunks))  # Get more for hybrid
        similarities, semantic_indices = index.search(query_vector, semantic_k)
        
        # Step 2: Keyword search
        keyword_indices = keyword_search(chunks, query_text, k * 2)
        
        # Step 3: Combine results with improved exact match prioritization
        # Check for exact phrase matches in chunks (case-insensitive)
        query_lower = query_text.lower().strip()
        query_original = query_text.strip()
        exact_match_indices = set()
        for idx, chunk in enumerate(chunks):
            chunk_lower = chunk.lower()
            # Check for exact phrase match (case-insensitive)
            if query_lower in chunk_lower:
                exact_match_indices.add(idx)
            # Also check case-sensitive for better precision
            elif query_original in chunk:
                exact_match_indices.add(idx)
        
        # Create score map: index -> (semantic_score, keyword_score, exact_match)
        combined_scores = {}
        
        # Add semantic results
        for i, idx in enumerate(semantic_indices[0]):
            if idx not in combined_scores:
                combined_scores[idx] = {
                    'semantic': float(similarities[0][i]), 
                    'keyword': 0.0,
                    'exact_match': idx in exact_match_indices
                }
        
        # Add keyword results with exact match boost
        for idx in keyword_indices:
            is_exact = idx in exact_match_indices
            if idx in combined_scores:
                combined_scores[idx]['keyword'] = 1.0
                combined_scores[idx]['exact_match'] = is_exact
            else:
                combined_scores[idx] = {
                    'semantic': 0.0, 
                    'keyword': 1.0,
                    'exact_match': is_exact
                }
        
        # Calculate combined scores (weighted, with heavy boost for exact matches)
        semantic_weight = 0.4  # Reduced to prioritize exact matches
        keyword_weight = 0.3
        exact_match_boost = 0.6  # Heavy boost for exact matches
        
        final_scores = []
        for idx, scores in combined_scores.items():
            # Normalize semantic score (0-1 range)
            semantic_norm = max(0, scores['semantic'])  # FAISS IP can be negative
            keyword_score = scores['keyword']
            exact_bonus = exact_match_boost if scores['exact_match'] else 0.0
            
            # Exact matches get heavy boost
            combined = (semantic_norm * semantic_weight) + (keyword_score * keyword_weight) + exact_bonus
            final_scores.append((idx, combined, scores['semantic'], scores['keyword'], scores['exact_match']))
        
        # Sort by combined score
        final_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k (convert numpy int64 to Python int)
        result = {
            'indices': [int(idx) for idx, _, _, _, _ in final_scores[:k]],
            'similarities': [float(sem) for _, _, sem, _, _ in final_scores[:k]],
            'combined_scores': [float(comb) for _, comb, _, _, _ in final_scores[:k]],
            'exact_matches': [bool(exact) for _, _, _, _, exact in final_scores[:k]]
        }
        print(json.dumps(result))
        
    except FileNotFoundError as e:
        print(json.dumps({'error': f'File not found: {str(e)}'}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

