#!/usr/bin/env python3
"""
Build embeddings index using OpenAI API (pure Python, no FAISS/NumPy)
- Splits markdown into ~800 character overlapping chunks
- Uses OpenAI text-embedding-3-small for embeddings (1536 dimensions)
- Saves chunks to JSON file
- Saves embeddings to separate JSON file (for pure Python search)

Usage: python build_pure_python.py <markdown_file> [api_key]
"""

import os
import sys
import json
import re
from openai import OpenAI

class PurePythonIndexBuilder:
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
        self.embeddings = []
        
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
            # Check for chapter headers in various formats:
            # - ## 1 TITLE
            # - ## Chapter 1: Title
            # - # Chapter 1: Title
            is_chapter = False
            chapter_num = 0
            chapter_title = ''
            
            # Format: ## 1 TITLE or ## NUMBER TITLE
            match = re.match(r'^##\s+(\d+)\s+(.+)$', line.strip())
            if match:
                is_chapter = True
                chapter_num = int(match.group(1))
                chapter_title = match.group(2).strip()
            # Format: ## Chapter X: Title or # Chapter X: Title
            elif line.startswith('# Chapter ') or line.startswith('## Chapter '):
                is_chapter = True
                chapter_match = line.replace('#', '').strip()
                parts = chapter_match.split(':', 1)
                chapter_num_str = parts[0].replace('Chapter', '').strip()
                chapter_num = int(chapter_num_str) if chapter_num_str.isdigit() else 0
                chapter_title = parts[1].strip() if len(parts) > 1 else ''
            
            if is_chapter:
                if current_chapter:
                    chapters.append(current_chapter)
                current_chapter = {
                    'num': chapter_num,
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
        
        # If no chapters found, treat entire document as one chapter
        if not chapters:
            chapters.append({
                'num': 1,
                'title': 'Document',
                'start_line': 0,
                'end_line': len(lines),
                'subsections': []
            })
        
        # Set end lines
        for i in range(len(chapters) - 1):
            chapters[i]['end_line'] = chapters[i + 1]['start_line']
        
        return chapters
    
    def _create_chunks_for_chapter(self, text, chapter):
        """Create overlapping chunks for a single chapter."""
        chunks = []
        metadata = []
        
        lines = text.split('\n')
        chapter_text_lines = lines[chapter['start_line']:chapter['end_line']]
        chapter_text = '\n'.join(chapter_text_lines)
        
        if not chapter_text.strip():
            return chunks, metadata
        
        # Find which subsection we're in
        current_subsection = None
        
        # Split into chunks
        pos = 0
        max_iterations = (len(chapter_text) // (self.chunk_size - self.chunk_overlap)) * 2  # Safety limit
        iterations = 0
        
        while pos < len(chapter_text) and iterations < max_iterations:
            iterations += 1
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
                for sub in reversed(chapter['subsections']):
                    if sub['start_line'] <= chunk_start_global:
                        current_subsection = sub['title']
                        break
                
                chunks.append(chunk_text)
                metadata.append({
                    'chapter_num': chapter['num'],
                    'chapter_title': chapter['title'],
                    'subsection': current_subsection,
                    'start_char': pos,
                    'end_char': chunk_end
                })
            
            # Move position with overlap
            new_pos = chunk_end - self.chunk_overlap
            if new_pos <= pos:  # Safety check to prevent infinite loop
                new_pos = pos + (self.chunk_size - self.chunk_overlap)
            pos = new_pos
            
            if pos >= len(chapter_text):
                break
        
        if iterations >= max_iterations:
            print(f"    Warning: Hit iteration limit for chapter {chapter['num']}, may have incomplete chunks")
        
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
        
        return embeddings
    
    def build_index(self):
        """Build index from text file."""
        print(f"Loading text from {self.text_path}...")
        text = self.load_text()
        
        print("Parsing chapters...")
        chapters = self.parse_chapters(text)
        print(f"Found {len(chapters)} chapters")
        
        print("Creating chunks...")
        total_chunks = 0
        for i, chapter in enumerate(chapters):
            print(f"  Processing chapter {chapter['num']}: {chapter['title'][:50]}...")
            chapter_chunks, chapter_metadata = self._create_chunks_for_chapter(text, chapter)
            self.chunks.extend(chapter_chunks)
            self.chunk_metadata.extend(chapter_metadata)
            total_chunks += len(chapter_chunks)
            print(f"    Created {len(chapter_chunks)} chunks (total: {total_chunks})")
        print(f"Created {len(self.chunks)} chunks total")
        
        print("Generating embeddings...")
        self.embeddings = self.embed_chunks(self.chunks)
        print(f"Generated {len(self.embeddings)} embeddings")
        
    def save(self, chunks_path='chunks.json', embeddings_path='embeddings.json'):
        """Save chunks and embeddings to JSON files."""
        if not self.embeddings:
            raise ValueError("Index not built. Call build_index() first.")
        
        print(f"Saving chunks to {chunks_path}...")
        chunks_data = {
            'chunks': self.chunks,
            'metadata': self.chunk_metadata,
            'embedding_model': 'text-embedding-3-small',
            'embedding_dim': self.embedding_dim
        }
        
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saving embeddings to {embeddings_path}...")
        with open(embeddings_path, 'w', encoding='utf-8') as f:
            json.dump(self.embeddings, f)
        
        print("✅ Index saved successfully!")
        print(f"  Chunks file: {chunks_path} ({os.path.getsize(chunks_path) / 1024 / 1024:.2f} MB)")
        print(f"  Embeddings file: {embeddings_path} ({os.path.getsize(embeddings_path) / 1024 / 1024:.2f} MB)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python build_pure_python.py <markdown_file> [api_key]", file=sys.stderr)
        sys.exit(1)
    
    text_path = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(text_path):
        print(f"Error: File not found: {text_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        builder = PurePythonIndexBuilder(text_path, api_key)
        builder.build_index()
        builder.save()
        
        print("\n✅ Pure Python index built successfully!")
        print("\nNext steps:")
        print("1. Update config.php:")
        print("   'SEARCH_SCRIPT' => __DIR__ . '/search_pure_python.py',")
        print("   'EMBEDDINGS_JSON' => __DIR__ . '/embeddings.json',")
        print("2. Upload embeddings.json and chunks.json to production")
        print("3. Test: php test_rag.php 'test query'")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

