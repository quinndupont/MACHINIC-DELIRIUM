#!/usr/bin/env python3
"""
Search FAISS index for similar vectors
Usage: python search_faiss.py <index_path> <query_vector_json> <k>
Output: JSON array of indices (most similar first)
"""

import sys
import json
import numpy as np
import faiss

def main():
    if len(sys.argv) < 4:
        print(json.dumps({'error': 'Usage: python search_faiss.py <index_path> <query_vector_json> <k>'}), file=sys.stderr)
        sys.exit(1)
    
    index_path = sys.argv[1]
    query_vector_json = sys.argv[2]
    k = int(sys.argv[3])
    
    try:
        # Load FAISS index
        index = faiss.read_index(index_path)
        
        # Parse query vector from JSON
        query_vector = np.array(json.loads(query_vector_json), dtype='float32')
        
        # Reshape to 2D if needed (1 x dimension)
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Ensure vector is normalized (should already be normalized from embed_query_openai.py)
        faiss.normalize_L2(query_vector)
        
        # Search - IndexIDMap returns the mapped IDs (chunk indices)
        similarities, indices = index.search(query_vector, k)
        
        # Return indices as JSON array
        # indices[0] contains the chunk IDs from IndexIDMap, which map directly to chunks.json
        result = {
            'indices': indices[0].tolist(),  # These are the chunk IDs from IndexIDMap
            'similarities': similarities[0].tolist()
        }
        print(json.dumps(result))
        
    except FileNotFoundError:
        print(json.dumps({'error': f'Index file not found: {index_path}'}))
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON: {str(e)}'}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        import traceback
        traceback.print_exc(file=sys.stderr)  # Debug info to stderr
        sys.exit(1)

if __name__ == '__main__':
    main()

