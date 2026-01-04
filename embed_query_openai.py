#!/usr/bin/env python3
"""
Convert query text to embedding vector using OpenAI API
Usage: python embed_query_openai.py "query text" [api_key]
Output: JSON array of floats (the embedding vector)
Fallback for systems where sentence-transformers/PyTorch isn't available
"""

import sys
import json
import os
from openai import OpenAI

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Query text required'}), file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else os.getenv('OPENAI_API_KEY', '')
    
    if not api_key:
        print(json.dumps({'error': 'OpenAI API key required (as argument or OPENAI_API_KEY env var)'}), file=sys.stderr)
        sys.exit(1)
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Generate embedding using OpenAI's text-embedding-3-small (1536 dimensions)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        
        # Output as JSON array
        print(json.dumps(response.data[0].embedding))
        
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

