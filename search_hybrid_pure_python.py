#!/usr/bin/env python3
"""
Hybrid search: combines semantic (pure Python cosine similarity) and keyword matching
Usage: python search_hybrid_pure_python.py <embeddings_json> <chunks_json> <query_text> <k> [api_key]
Output: JSON array of indices (most similar first)
"""

import sys
import json
import os
import math
import re
from openai import OpenAI

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors (pure Python)."""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def normalize_vector(vec):
    """Normalize a vector to unit length (pure Python)."""
    magnitude = math.sqrt(sum(a * a for a in vec))
    if magnitude == 0:
        return vec
    return [a / magnitude for a in vec]

def keyword_search(chunks, query, k):
    """Find chunks containing query keywords with improved exact matching."""
    query_lower = query.lower()
    query_original = query
    
    # Extract words (including hyphenated words)
    query_words = set(re.findall(r'\b[\w-]+\b', query_lower))
    query_words.update(re.findall(r'\w+', query_lower))
    
    scores = []
    for idx, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        chunk_original = chunks[idx]
        
        # Exact phrase match (case-insensitive)
        exact_phrase_count_ci = chunk_lower.count(query_lower)
        
        # Exact phrase match (case-sensitive)
        exact_phrase_count_cs = chunk_original.count(query_original)
        
        # Word matches
        chunk_words = set(re.findall(r'\b[\w-]+\b', chunk_lower))
        chunk_words.update(re.findall(r'\w+', chunk_lower))
        word_matches = len(query_words.intersection(chunk_words))
        
        # Calculate score
        score = (exact_phrase_count_cs * 100) + (exact_phrase_count_ci * 50) + word_matches
        
        if score > 0:
            scores.append((idx, score))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in scores[:k]]

def main():
    if len(sys.argv) < 5:
        print(json.dumps({'error': 'Usage: python search_hybrid_pure_python.py <embeddings_json> <chunks_json> <query_text> <k> [api_key]'}), file=sys.stderr)
        sys.exit(1)
    
    embeddings_path = sys.argv[1]
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
        
        # Load embeddings
        with open(embeddings_path, 'r', encoding='utf-8') as f:
            embeddings = json.load(f)
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Step 1: Semantic search (pure Python cosine similarity)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query_text
        )
        query_embedding = normalize_vector(response.data[0].embedding)
        
        # Compute similarities
        semantic_scores = {}
        for idx, embedding in enumerate(embeddings):
            normalized_embedding = normalize_vector(embedding)
            similarity = cosine_similarity(query_embedding, normalized_embedding)
            semantic_scores[idx] = similarity
        
        # Get top semantic results
        semantic_sorted = sorted(semantic_scores.items(), key=lambda x: x[1], reverse=True)
        semantic_indices = [idx for idx, _ in semantic_sorted[:k * 2]]
        
        # Step 2: Keyword search
        keyword_indices = keyword_search(chunks, query_text, k * 2)
        
        # Step 3: Combine results
        keyword_scores = {}
        for i, idx in enumerate(keyword_indices):
            keyword_scores[idx] = float(len(keyword_indices) - i)
        
        # Check for exact matches
        exact_matches = []
        query_lower = query_text.lower()
        query_original = query_text
        for idx, chunk in enumerate(chunks):
            if query_original in chunk or query_lower in chunk.lower():
                exact_matches.append(idx)
        
        # Combine scores
        all_indices = set(semantic_indices) | set(keyword_indices) | set(exact_matches)
        
        final_scores = []
        for idx in all_indices:
            semantic_norm = semantic_scores.get(idx, 0.0)
            keyword_score = keyword_scores.get(idx, 0.0)
            
            # Normalize keyword score
            if keyword_indices:
                keyword_norm = keyword_score / len(keyword_indices)
            else:
                keyword_norm = 0.0
            
            # Boost exact matches
            exact_boost = 0.6 if idx in exact_matches else 0.0
            
            # Combine with weights
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

