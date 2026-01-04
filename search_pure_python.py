#!/usr/bin/env python3
"""
Pure Python vector similarity search (no FAISS, no NumPy)
Uses cosine similarity computed in pure Python
Usage: python search_pure_python.py <embeddings_json> <query_vector_json> <k>
Output: JSON array of indices (most similar first)
"""

import sys
import json
import math

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

def main():
    if len(sys.argv) < 4:
        print(json.dumps({'error': 'Usage: python search_pure_python.py <embeddings_json> <query_vector_json> <k>'}), file=sys.stderr)
        sys.exit(1)
    
    embeddings_path = sys.argv[1]
    query_vector_json = sys.argv[2]
    k = int(sys.argv[3])
    
    try:
        # Load embeddings from JSON file
        with open(embeddings_path, 'r', encoding='utf-8') as f:
            embeddings_data = json.load(f)
        
        # Support both formats: list of vectors or chunks.json format
        if 'embeddings' in embeddings_data:
            embeddings = embeddings_data['embeddings']
        elif 'chunks' in embeddings_data:
            # If chunks.json format, we need embeddings stored separately
            # For now, assume embeddings are in a separate file
            print(json.dumps({'error': 'Embeddings must be stored separately. Use build_pure_python.py to create embeddings.json'}), file=sys.stderr)
            sys.exit(1)
        else:
            # Assume it's a list of embeddings
            embeddings = embeddings_data
        
        # Parse query vector
        query_vector = json.loads(query_vector_json)
        if isinstance(query_vector, dict) and 'error' in query_vector:
            print(json.dumps(query_vector), file=sys.stderr)
            sys.exit(1)
        
        # Normalize query vector
        query_vector = normalize_vector(query_vector)
        
        # Compute similarities for all embeddings
        similarities = []
        for idx, embedding in enumerate(embeddings):
            # Normalize embedding
            normalized_embedding = normalize_vector(embedding)
            similarity = cosine_similarity(query_vector, normalized_embedding)
            similarities.append((idx, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top k
        top_k = similarities[:k]
        
        result = {
            'indices': [idx for idx, _ in top_k],
            'similarities': [sim for _, sim in top_k]
        }
        
        print(json.dumps(result))
        
    except FileNotFoundError:
        print(json.dumps({'error': f'Embeddings file not found: {embeddings_path}'}), file=sys.stderr)
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

