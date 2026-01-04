#!/usr/bin/env python3
"""
Build FAISS index using OpenAI embeddings API
- Splits markdown into ~800 character overlapping chunks
- Uses OpenAI text-embedding-3-small for embeddings (1536 dimensions)
- Saves chunks to JSON file
- Creates FAISS index binary file

Usage: python build_faiss_openai.py <markdown_file> [api_key]
"""

import os
import sys
import json
import numpy as np
import faiss
from openai import OpenAI

class OpenAIFAISSIndexBuilder:
    def __init__(self, text_path, api_key=None):
        """
        Initialize builder with OpenAI embedding API.
        
        Args:
            text_path: Path to markdown file
            api_key: OpenAI API key (or use OPENAI_API_KEY env var)
        """
        self.text_path = text_path
        self.chunk_size = 800  # characters
        self.chunk_overlap = 100  # characters overlap
        
        # Get API key
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("OpenAI API key required (argument or OPENAI_API_KEY env var)")
        
        self.client = OpenAI(api_key=api_key)
        self.embedding_dim = 1536  # text-embedding-3-small dimension
        
        print(f"Using OpenAI embeddings (dimension: {self.embedding_dim})")
        
        self.chunks = []
        self.chunk_metadata = []
        self.embeddings = None
        self.index = None
        
    def load_text(self):
        """Load markdown text from file."""
        with open(self.text_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def parse_chapters(self, text):
        """Parse markdown to identify chapters and their structure."""
        lines = text.split('\n')
        chapters = []
        current_chapter = None
        
        for i, line in enumerate(lines):
            # Check for chapter headers (# Chapter X: Title)
            if line.startswith('# Chapter ') or line.startswith('## Chapter '):
                if current_chapter:
                    chapters.append(current_chapter)
                chapter_match = line.replace('#', '').strip()
                parts = chapter_match.split(':', 1)
                chapter_num = parts[0].replace('Chapter', '').strip()
                chapter_title = parts[1].strip() if len(parts) > 1 else ''
                current_chapter = {
                    'num': int(chapter_num) if chapter_num.isdigit() else 0,
                    'title': chapter_title,
                    'start_line': i,
                    'end_line': len(lines),
                    'subsections': []
                }
            elif current_chapter and line.startswith('###'):
                # Subsection
                subsection_title = line.replace('#', '').strip()
                current_chapter['subsections'].append({
                    'title': subsection_title,
                    'start_line': i
                })
        
        if current_chapter:
            chapters.append(current_chapter)
        
        # Set end lines
        for i in range(len(chapters) - 1):
            chapters[i]['end_line'] = chapters[i + 1]['start_line']
        
        return chapters
    
    def create_chunks(self, text, chapters):
        """Create overlapping chunks from text."""
        chunks = []
        metadata = []
        
        lines = text.split('\n')
        
        for chapter in chapters:
            chapter_text_lines = lines[chapter['start_line']:chapter['end_line']]
            chapter_text = '\n'.join(chapter_text_lines)
            
            # Find which subsection we're in
            current_subsection = None
            subsection_start = 0
            
            # Split into chunks
            pos = 0
            while pos < len(chapter_text):
                chunk_end = min(pos + self.chunk_size, len(chapter_text))
                
                # Try to break at sentence/paragraph boundary
                if chunk_end < len(chapter_text):
                    # Look for paragraph break
                    for break_char in ['\n\n', '\n', '. ', '! ', '? ']:
                        break_pos = chapter_text.rfind(break_char, pos, chunk_end)
                        if break_pos != -1:
                            chunk_end = break_pos + len(break_char)
                            break
                
                chunk_text = chapter_text[pos:chunk_end].strip()
                
                if len(chunk_text) > 50:  # Minimum chunk size
                    # Determine subsection
                    chunk_start_global = chapter['start_line'] + chapter_text[:pos].count('\n')
                    for sub in chapter['subsections']:
                        if sub['start_line'] <= chunk_start_global:
                            current_subsection = sub['title']
                    
                    chunks.append(chunk_text)
                    metadata.append({
                        'chapter_num': chapter['num'],
                        'chapter_title': chapter['title'],
                        'subsection': current_subsection,
                        'start_char': pos,
                        'end_char': chunk_end
                    })
                
                # Move position with overlap
                pos = chunk_end - self.chunk_overlap
                if pos >= len(chapter_text):
                    break
        
        return chunks, metadata
    
    def embed_chunks(self, chunks, batch_size=100):
        """Embed chunks using OpenAI API."""
        print(f"Embedding {len(chunks)} chunks using OpenAI API...")
        embeddings = []
        
        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            print(f"  Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}...")
            
            try:
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"Error embedding batch {i//batch_size + 1}: {e}", file=sys.stderr)
                raise
        
        return np.array(embeddings, dtype='float32')
    
    def build_index(self):
        """Build FAISS index from text file."""
        print(f"Loading text from {self.text_path}...")
        text = self.load_text()
        
        print("Parsing chapters...")
        chapters = self.parse_chapters(text)
        print(f"Found {len(chapters)} chapters")
        
        print("Creating chunks...")
        self.chunks, self.chunk_metadata = self.create_chunks(text, chapters)
        print(f"Created {len(self.chunks)} chunks")
        
        print("Generating embeddings...")
        self.embeddings = self.embed_chunks(self.chunks)
        print(f"Generated {len(self.embeddings)} embeddings")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        
        print("Building FAISS index...")
        # Create FAISS index (Inner Product for normalized vectors = cosine similarity)
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(self.embeddings)
        print(f"Index built with {self.index.ntotal} vectors")
        
    def save(self, index_path='faiss_index.bin', chunks_path='chunks.json'):
        """Save FAISS index and chunks to files."""
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        print(f"Saving FAISS index to {index_path}...")
        faiss.write_index(self.index, index_path)
        
        print(f"Saving chunks to {chunks_path}...")
        chunks_data = {
            'chunks': self.chunks,
            'metadata': self.chunk_metadata,
            'embedding_model': 'text-embedding-3-small',
            'embedding_dim': self.embedding_dim
        }
        
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        
        print("✅ Index and chunks saved successfully!")
        print(f"  Index file: {index_path} ({os.path.getsize(index_path) / 1024 / 1024:.2f} MB)")
        print(f"  Chunks file: {chunks_path} ({os.path.getsize(chunks_path) / 1024 / 1024:.2f} MB)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python build_faiss_openai.py <markdown_file> [api_key]", file=sys.stderr)
        sys.exit(1)
    
    text_path = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(text_path):
        print(f"Error: File not found: {text_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        builder = OpenAIFAISSIndexBuilder(text_path, api_key)
        builder.build_index()
        builder.save()
        
        print("\n✅ FAISS index built successfully using OpenAI embeddings!")
        print("\nNext steps:")
        print("1. Update config.php: 'EMBED_SCRIPT' => __DIR__ . '/embed_query_openai.py',")
        print("2. Make sure OPENAI_API_KEY is set in config.php")
        print("3. Test: php test_rag.php 'test query'")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

