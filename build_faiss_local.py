#!/usr/bin/env python3
"""
Build FAISS index using local embedding model
- Splits markdown into ~800 character overlapping chunks
- Uses sentence-transformers for local embeddings (384 dimensions)
- Saves chunks to JSON file
- Creates FAISS index binary file
"""

import os
import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class LocalFAISSIndexBuilder:
    def __init__(self, text_path, model_name="all-MiniLM-L6-v2"):
        """
        Initialize builder with local embedding model.
        
        Args:
            text_path: Path to markdown file
            model_name: Sentence transformer model name (default: all-MiniLM-L6-v2, 384 dims)
        """
        self.text_path = text_path
        self.model_name = model_name
        self.chunk_size = 800  # characters
        self.chunk_overlap = 100  # characters overlap
        
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded. Embedding dimension: {self.embedding_dim}")
        
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
        chapter_num = 0
        pre_chapter_content = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for h1 headings (#) - major chapters
            if line.startswith('# ') and not line.startswith('##'):
                if pre_chapter_content and not current_chapter:
                    chapter_num += 1
                    current_chapter = {
                        'num': chapter_num,
                        'title': 'Introduction',
                        'content': pre_chapter_content,
                        'subsections': []
                    }
                    pre_chapter_content = []
                
                if current_chapter:
                    chapters.append(current_chapter)
                
                chapter_title = line[2:].strip()
                chapter_num += 1
                current_chapter = {
                    'num': chapter_num,
                    'title': chapter_title,
                    'content': [],
                    'subsections': []
                }
                i += 1
                continue
            
            # Check for h3 headings (###) - these are also major chapters
            if line.startswith('### '):
                if pre_chapter_content and not current_chapter:
                    chapter_num += 1
                    current_chapter = {
                        'num': chapter_num,
                        'title': 'Introduction',
                        'content': pre_chapter_content,
                        'subsections': []
                    }
                    pre_chapter_content = []
                
                if current_chapter:
                    chapters.append(current_chapter)
                
                chapter_title = line[4:].strip()
                chapter_num += 1
                current_chapter = {
                    'num': chapter_num,
                    'title': chapter_title,
                    'content': [],
                    'subsections': []
                }
                i += 1
                continue
            
            # Check for h4 headings (####) - subsections
            if line.startswith('#### '):
                subsection_title = line[5:].strip()
                if current_chapter:
                    current_chapter['subsections'].append({
                        'title': subsection_title,
                        'start_line': len(current_chapter['content'])
                    })
                    current_chapter['content'].append(line)
                else:
                    pre_chapter_content.append(line)
                i += 1
                continue
            
            # Regular content
            if current_chapter:
                current_chapter['content'].append(line)
            else:
                pre_chapter_content.append(line)
            i += 1
        
        # Add any remaining pre-chapter content as a chapter
        if pre_chapter_content and not current_chapter:
            chapter_num += 1
            current_chapter = {
                'num': chapter_num,
                'title': 'Introduction',
                'content': pre_chapter_content,
                'subsections': []
            }
        
        # Add last chapter
        if current_chapter:
            chapters.append(current_chapter)
        
        return chapters
    
    def create_chunks(self, text):
        """
        Create overlapping chunks of approximately 800 characters.
        Returns list of chunk texts and metadata.
        """
        chapters = self.parse_chapters(text)
        chunks = []
        metadata = []
        
        for chapter in chapters:
            chapter_text = '\n'.join(chapter['content'])
            
            # Build chapter header for context
            chapter_header = f"Chapter {chapter['num']}: {chapter['title']}\n\n"
            header_len = len(chapter_header)
            
            # If chapter is small enough, create single chunk
            if len(chapter_text) <= self.chunk_size - header_len:
                chunk_text = chapter_header + chapter_text
                chunks.append(chunk_text)
                metadata.append({
                    'chapter_num': chapter['num'],
                    'chapter_title': chapter['title'],
                    'subsection': None
                })
            else:
                # Split chapter into overlapping chunks
                # Use character-based splitting (not token-based)
                text_with_header = chapter_header + chapter_text
                start = 0
                
                while start < len(text_with_header):
                    # Calculate end position
                    end = start + self.chunk_size
                    
                    # If we're near the end, take the rest
                    if end >= len(text_with_header):
                        chunk_text = text_with_header[start:]
                    else:
                        # Try to break at a sentence or paragraph boundary
                        # Look for newline or period near the end
                        break_point = end
                        for i in range(end, max(start + self.chunk_size - 200, start), -1):
                            if text_with_header[i] in ['\n', '.', '!', '?']:
                                break_point = i + 1
                                break
                        
                        chunk_text = text_with_header[start:break_point]
                        end = break_point
                    
                    # Determine subsection for this chunk
                    # Calculate position in original chapter_text
                    chunk_pos_in_chapter = max(0, start - header_len)
                    subsection_title = None
                    for sub in reversed(chapter['subsections']):
                        if sub['start_line'] <= chunk_pos_in_chapter:
                            subsection_title = sub['title']
                            break
                    
                    chunks.append(chunk_text)
                    metadata.append({
                        'chapter_num': chapter['num'],
                        'chapter_title': chapter['title'],
                        'subsection': subsection_title
                    })
                    
                    # Move start forward with overlap
                    start = end - self.chunk_overlap
                    if start >= len(text_with_header):
                        break
        
        return chunks, metadata
    
    def generate_embeddings(self, texts):
        """Generate embeddings using local sentence transformer model."""
        print(f"Generating embeddings for {len(texts)} chunks...")
        # Process in batches for efficiency
        batch_size = 32
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            embeddings.extend(batch_embeddings)
        
        return np.array(embeddings, dtype='float32')
    
    def build_index(self):
        """Build FAISS index from markdown file."""
        print("Loading text from markdown file...")
        text = self.load_text()
        
        print("Creating chunks...")
        self.chunks, self.chunk_metadata = self.create_chunks(text)
        print(f"Created {len(self.chunks)} chunks")
        
        print("Generating embeddings...")
        self.embeddings = self.generate_embeddings(self.chunks)
        print(f"Generated {len(self.embeddings)} embeddings (shape: {self.embeddings.shape})")
        
        # Create FAISS index
        # Using IndexFlatIP (Inner Product) for cosine similarity with normalized vectors
        print(f"Creating FAISS index (dimension: {self.embedding_dim}, vectors: {len(self.embeddings)})...")
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(self.embeddings)
        
        print(f"FAISS index built successfully with {self.index.ntotal} vectors")
    
    def save_index(self, index_path='faiss_index.bin', chunks_path='chunks.json'):
        """Save FAISS index and chunks to disk."""
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        print(f"Saving FAISS index to {index_path}...")
        faiss.write_index(self.index, index_path)
        
        print(f"Saving chunks to {chunks_path}...")
        chunks_data = {
            'chunks': self.chunks,
            'metadata': self.chunk_metadata,
            'model': self.model_name,
            'dimension': self.embedding_dim,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        
        print("Index and chunks saved successfully!")
        print(f"  - {index_path}: FAISS vector index ({os.path.getsize(index_path) / 1024:.1f} KB)")
        print(f"  - {chunks_path}: Text chunks and metadata ({os.path.getsize(chunks_path) / 1024:.1f} KB)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python build_faiss_local.py <markdown_file> [model_name]")
        print("  Default model: all-MiniLM-L6-v2 (384 dimensions)")
        print("  Other options: all-mpnet-base-v2 (768 dims), paraphrase-MiniLM-L6-v2 (384 dims)")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "all-MiniLM-L6-v2"
    
    if not os.path.exists(markdown_file):
        print(f"Error: Markdown file not found: {markdown_file}")
        sys.exit(1)
    
    try:
        builder = LocalFAISSIndexBuilder(markdown_file, model_name=model_name)
        builder.build_index()
        builder.save_index()
        print("\n✓ FAISS index built successfully!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

