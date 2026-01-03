#!/usr/bin/env python3
"""
Python RAG API script - called from PHP
Usage: python rag_api.py query "query text" k api_key
"""

import sys
import json
import os

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from rag import RAGSystem

def main():
    if len(sys.argv) < 5:
        print(json.dumps({'error': 'Invalid arguments'}))
        sys.exit(1)
    
    command = sys.argv[1]
    query = sys.argv[2]
    k = int(sys.argv[3])
    api_key = sys.argv[4]
    
    if command != 'query':
        print(json.dumps({'error': 'Unknown command'}))
        sys.exit(1)
    
    try:
        # Initialize RAG system
        markdown_file = os.path.join(project_dir, "Anti-Oedipus.md")
        rag = RAGSystem(markdown_file, api_key)
        
        # Query
        results = rag.query(query, k=k)
        
        # Format results for PHP
        formatted_results = []
        for result in results:
            formatted_results.append({
                'text': result['text'],
                'chapter_num': result.get('metadata', {}).get('chapter_num', 0),
                'chapter_title': result.get('metadata', {}).get('chapter_title', 'Unknown'),
                'subsection': result.get('metadata', {}).get('subsection', '')
            })
        
        print(json.dumps(formatted_results))
        
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    main()

