#!/usr/bin/env python3
"""
Agent to fix paragraph formatting in markdown files.
Processes text chunk by chunk (per chapter/section) to fix paragraph breaks semantically.
"""

import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()

class ParagraphFixer:
    def __init__(self, input_file, output_file, api_key=None):
        self.input_file = input_file
        self.output_file = output_file
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        
    def parse_sections(self, content):
        """Parse markdown content into sections (chapters and subsections)."""
        lines = content.split('\n')
        sections = []
        current_section = None
        current_content = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for headings (h1-h4)
            if re.match(r'^#{1,4}\s+', line):
                # Save previous section
                if current_section is not None:
                    current_section['content'] = '\n'.join(current_content)
                    sections.append(current_section)
                
                # Start new section
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                current_section = {
                    'level': level,
                    'title': title,
                    'line_start': i,
                    'content': []
                }
                current_content = []
                i += 1
                continue
            
            # Collect content for current section
            if current_section is not None:
                current_content.append(line)
            else:
                # Content before first heading
                if not sections:
                    sections.append({
                        'level': 0,
                        'title': 'Preamble',
                        'line_start': 0,
                        'content': []
                    })
                    current_section = sections[0]
                    current_content = current_section['content']
                current_content.append(line)
            
            i += 1
        
        # Save last section
        if current_section is not None:
            current_section['content'] = '\n'.join(current_content)
            sections.append(current_section)
        
        return sections
    
    def is_special_line(self, line):
        """Check if line is a special markdown element that shouldn't be merged."""
        stripped = line.strip()
        
        # Empty lines
        if not stripped:
            return True
        
        # Headings
        if re.match(r'^#{1,6}\s+', stripped):
            return True
        
        # Lists (ordered or unordered)
        if re.match(r'^\s*[-*+]\s+', stripped) or re.match(r'^\s*\d+[.)]\s+', stripped):
            return True
        
        # Code blocks
        if stripped.startswith('```'):
            return True
        
        # Footnotes
        if re.match(r'^\[\^\d+\]:', stripped):
            return True
        
        # Horizontal rules
        if re.match(r'^---+$', stripped):
            return True
        
        # Blockquotes
        if stripped.startswith('>'):
            return True
        
        return False
    
    def extract_text_blocks(self, content):
        """Extract text blocks that need paragraph fixing, preserving special elements."""
        lines = content.split('\n')
        blocks = []
        current_text_block = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            is_special = self.is_special_line(line)
            
            if is_special:
                # Save current text block if exists
                if current_text_block:
                    text_content = '\n'.join(current_text_block)
                    if text_content.strip():  # Only add non-empty blocks
                        blocks.append({
                            'type': 'text',
                            'content': text_content
                        })
                    current_text_block = []
                
                # Handle special elements
                if line.strip():  # Non-empty special line
                    blocks.append({
                        'type': 'special',
                        'content': line
                    })
                else:
                    # Empty line - preserve as special
                    blocks.append({
                        'type': 'special',
                        'content': line
                    })
            else:
                # Regular text line - add to current text block
                current_text_block.append(line)
            
            i += 1
        
        # Save last text block
        if current_text_block:
            text_content = '\n'.join(current_text_block)
            if text_content.strip():
                blocks.append({
                    'type': 'text',
                    'content': text_content
                })
        
        return blocks
    
    def fix_paragraphs_with_llm(self, text_block):
        """Use LLM to fix paragraph breaks in a text block."""
        if not text_block.strip():
            return text_block
        
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        estimated_tokens = len(text_block) // 4
        max_tokens = min(8000, estimated_tokens * 2 + 1000)  # Allow room for response
        
        prompt = f"""You are a text formatting expert. Fix the paragraph breaks in the following text block. 

The text currently has many line breaks but lacks proper paragraph division. Your task is to:
1. Group related sentences into proper paragraphs
2. Create paragraph breaks (double line breaks) where there are semantic breaks in thought
3. Keep single line breaks within paragraphs only where they are necessary (e.g., for readability of long paragraphs)
4. Preserve ALL original text - do not add, remove, or change any words
5. Preserve all punctuation, capitalization, and formatting exactly as written
6. Only fix paragraph breaks - do not fix other formatting issues unless they affect paragraph structure
7. Do not wrap the response in code blocks or markdown formatting

Text to fix:
{text_block}

Return ONLY the fixed text with proper paragraph breaks, preserving all original content:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a text formatting expert specializing in fixing paragraph breaks while preserving original content exactly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lower temperature for more consistent formatting
                max_tokens=max_tokens
            )
            
            fixed_text = response.choices[0].message.content.strip()
            
            # Remove any markdown code block formatting if LLM added it
            if fixed_text.startswith('```'):
                # Extract content between code block markers
                lines = fixed_text.split('\n')
                if len(lines) > 2 and lines[0].startswith('```'):
                    fixed_text = '\n'.join(lines[1:-1])
                else:
                    fixed_text = re.sub(r'^```[^\n]*\n?', '', fixed_text)
                    fixed_text = re.sub(r'\n?```$', '', fixed_text)
            
            return fixed_text
            
        except Exception as e:
            print(f"Error processing text block: {e}")
            print(f"Block preview: {text_block[:200]}...")
            # Return original if error
            return text_block
    
    def split_large_block(self, text_block, max_chars=6000):
        """Split very large text blocks into smaller chunks for processing."""
        if len(text_block) <= max_chars:
            return [text_block]
        
        # Try to split at paragraph boundaries (double newlines)
        chunks = []
        parts = text_block.split('\n\n')
        current_chunk = []
        current_size = 0
        
        for part in parts:
            part_size = len(part)
            if current_size + part_size > max_chars and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [part]
                current_size = part_size
            else:
                current_chunk.append(part)
                current_size += part_size + 2  # +2 for '\n\n'
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def process_section(self, section):
        """Process a single section to fix paragraph breaks."""
        content = section['content']
        
        # Skip very short sections or sections with no text content
        if not content.strip():
            section['fixed_content'] = content
            return section
        
        # Extract text blocks
        blocks = self.extract_text_blocks(content)
        
        # Process each text block
        fixed_blocks = []
        for block in blocks:
            if block['type'] == 'special':
                # Keep special elements as-is
                fixed_blocks.append(block['content'])
            else:
                # Fix paragraph breaks in text blocks
                # Only process if block is substantial (more than just whitespace)
                text_content = block['content'].strip()
                if text_content and len(text_content) > 10:  # Minimum length to process
                    # Split large blocks if needed
                    chunks = self.split_large_block(block['content'])
                    fixed_chunks = []
                    for chunk in chunks:
                        fixed_chunk = self.fix_paragraphs_with_llm(chunk)
                        fixed_chunks.append(fixed_chunk)
                    fixed_text = '\n\n'.join(fixed_chunks)
                    fixed_blocks.append(fixed_text)
                else:
                    # Keep small blocks as-is
                    fixed_blocks.append(block['content'])
        
        # Reconstruct section content, preserving structure
        section['fixed_content'] = '\n'.join(fixed_blocks)
        return section
    
    def process_file(self):
        """Process the entire markdown file."""
        print(f"Reading input file: {self.input_file}")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("Parsing sections...")
        sections = self.parse_sections(content)
        print(f"Found {len(sections)} sections")
        
        print("\nProcessing sections...")
        fixed_sections = []
        
        for i, section in enumerate(tqdm(sections, desc="Processing")):
            title = section.get('title', 'Unknown')
            level = section.get('level', 0)
            indent = '  ' * level
            
            print(f"\n{indent}Processing: {title}")
            
            # Process section
            fixed_section = self.process_section(section)
            fixed_sections.append(fixed_section)
        
        # Reconstruct full document
        print("\nReconstructing document...")
        output_parts = []
        
        for section in fixed_sections:
            # Add heading if present
            if section['level'] > 0:
                heading_prefix = '#' * section['level']
                output_parts.append(f"{heading_prefix} {section['title']}")
            
            # Add fixed content (which may already have proper spacing)
            content = section['fixed_content']
            output_parts.append(content)
        
        # Join with double newlines between sections, but preserve internal spacing
        output_content = '\n\n'.join(output_parts)
        
        # Write output file
        print(f"\nWriting output file: {self.output_file}")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"\nDone! Fixed document saved to: {self.output_file}")
        return self.output_file


def main():
    import sys
    
    input_file = "Anti-Oedipus.md"
    output_file = "Anti-Oedipus-fixed.md"
    
    # Check for test mode
    test_mode = '--test' in sys.argv or '-t' in sys.argv
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return
    
    fixer = ParagraphFixer(input_file, output_file)
    
    if test_mode:
        # Test mode: process only first 3 sections
        print("TEST MODE: Processing first 3 sections only")
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = fixer.parse_sections(content)
        print(f"Found {len(sections)} total sections")
        print(f"Processing first 3 sections for testing...")
        
        test_sections = sections[:3]
        fixed_sections = []
        
        for section in test_sections:
            title = section.get('title', 'Unknown')
            print(f"\nProcessing: {title}")
            fixed_section = fixer.process_section(section)
            fixed_sections.append(fixed_section)
        
        # Write test output
        test_output = "Anti-Oedipus-test-output.md"
        output_parts = []
        for section in fixed_sections:
            if section['level'] > 0:
                heading_prefix = '#' * section['level']
                output_parts.append(f"{heading_prefix} {section['title']}")
            output_parts.append(section['fixed_content'])
        
        output_content = '\n\n'.join(output_parts)
        with open(test_output, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"\nTest output saved to: {test_output}")
        print("Review the output and run without --test to process the full file.")
    else:
        fixer.process_file()


if __name__ == "__main__":
    main()

