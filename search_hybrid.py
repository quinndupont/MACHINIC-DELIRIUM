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
    """Find chunks containing query keywords."""
    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    
    scores = []
    for idx, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        chunk_words = set(re.findall(r'\b\w+\b', chunk_lower))
        
        # Count word matches
        word_matches = len(query_words.intersection(chunk_words))
        exact_phrase_count = chunk_lower.count(query_lower)
        
        # Weight exact phrase matches more heavily
        score = word_matches + (exact_phrase_count * 10)
        
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
        
        # Step 3: Combine results
        # Create score map: index -> (semantic_score, keyword_score)
        combined_scores = {}
        
        # Add semantic results
        for i, idx in enumerate(semantic_indices[0]):
            if idx not in combined_scores:
                combined_scores[idx] = {'semantic': float(similarities[0][i]), 'keyword': 0.0}
        
        # Add keyword results
        for idx in keyword_indices:
            if idx in combined_scores:
                combined_scores[idx]['keyword'] = 1.0
            else:
                combined_scores[idx] = {'semantic': 0.0, 'keyword': 1.0}
        
        # Calculate combined scores (weighted)
        semantic_weight = 0.7
        keyword_weight = 0.3
        
        final_scores = []
        for idx, scores in combined_scores.items():
            # Normalize semantic score (0-1 range)
            semantic_norm = max(0, scores['semantic'])  # FAISS IP can be negative
            combined = (semantic_norm * semantic_weight) + (scores['keyword'] * keyword_weight)
            final_scores.append((idx, combined, scores['semantic'], scores['keyword']))
        
        # Sort by combined score
        final_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k (convert numpy int64 to Python int)
        result = {
            'indices': [int(idx) for idx, _, _, _ in final_scores[:k]],
            'similarities': [float(sem) for _, _, sem, _ in final_scores[:k]],
            'combined_scores': [float(comb) for _, comb, _, _ in final_scores[:k]]
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

