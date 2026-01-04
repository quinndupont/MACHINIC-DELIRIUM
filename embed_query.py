#!/usr/bin/env python3
"""
Convert query text to embedding vector using local model
Usage: python embed_query.py "query text" [model_name]
Output: JSON array of floats (the embedding vector)
"""

import sys
import json
import numpy as np
from sentence_transformers import SentenceTransformer

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Query text required'}), file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "all-MiniLM-L6-v2"
    
    try:
        # Load model (will cache after first load)
        model = SentenceTransformer(model_name)
        
        # Generate embedding
        embedding = model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        # Output as JSON array
        print(json.dumps(embedding.tolist()))
        
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        import traceback
        traceback.print_exc(file=sys.stderr)  # Debug info to stderr
        sys.exit(1)

if __name__ == '__main__':
    main()

