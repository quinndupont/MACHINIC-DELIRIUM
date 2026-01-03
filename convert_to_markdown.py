#!/usr/bin/env python3
"""
Convert Anti-Oedipus.txt to markdown format using AI to identify headings,
page numbers, and structure.

Usage:
    # Full conversion (requires OpenAI API key in .env)
    python3 convert_to_markdown.py
    
    # Test mode (processes only first chunk and displays results)
    python3 convert_to_markdown.py --test
    
    # Custom input/output files
    python3 convert_to_markdown.py -i input.txt -o output.md
    
    # Limit number of chunks processed
    python3 convert_to_markdown.py --max-chunks 2
    
    # Process entire text as single chunk (better continuity)
    python3 convert_to_markdown.py --single-chunk

Note: This script uses OpenAI's API with gpt-4o-mini (cheaper/faster model).
- Default: Uses large chunks (~400k chars each) for efficient processing. For a 1.2MB file,
  expect 2-3 API calls total.
- Single chunk mode: Processes entire text at once for maximum continuity. Requires
  model with large context window (gpt-4o-mini supports 128k tokens).
  
Alternative: Use convert_to_markdown_single_chunk.py for a dedicated single-chunk version.
"""

import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()

class TextToMarkdownConverter:
    def __init__(self, input_file, output_file, api_key, test_mode=False, max_chunks=None, single_chunk=False):
        self.input_file = input_file
        self.output_file = output_file
        self.client = OpenAI(api_key=api_key)
        # Use much larger chunks - gpt-4o-mini has 128k token context (~500k chars)
        # Use 400k chars per chunk to leave room for prompts and output
        self.chunk_size = 400000  # characters per chunk
        self.test_mode = test_mode
        self.max_chunks = max_chunks
        self.single_chunk = single_chunk
        self.model = "gpt-4o-mini"  # Cheaper and faster model
        
        # Structure extracted from table of contents
        self.toc_structure = []
        self.title_page = ""
        self.toc_text = ""
        self.main_text = ""
        
    def parse_text_structure(self, text):
        """Parse text into title page, table of contents, and main text."""
        lines = text.split('\n')
        
        # Find CONTENTS marker (start of table of contents)
        toc_start_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "CONTENTS":
                toc_start_idx = i
                break
        
        if toc_start_idx is None:
            raise ValueError("Could not find 'CONTENTS' marker in text")
        
        # Title page is everything before CONTENTS
        self.title_page = '\n'.join(lines[:toc_start_idx])
        
        # Find end of table of contents (start of main text)
        # Main text starts after INDEX entry (last entry in TOC)
        toc_end_idx = None
        for i in range(toc_start_idx, len(lines)):
            stripped = lines[i].strip()
            # Look for start of actual content (PREFACE or ## PREFACE)
            if stripped.startswith("## PREFACE") or (stripped == "PREFACE" and i > toc_start_idx + 50):
                toc_end_idx = i
                break
        
        if toc_end_idx is None:
            # Fallback: look for first ## heading
            for i in range(toc_start_idx, len(lines)):
                if lines[i].strip().startswith("##"):
                    toc_end_idx = i
                    break
        
        if toc_end_idx is None:
            raise ValueError("Could not find end of table of contents")
        
        # Table of contents is between CONTENTS and main text
        self.toc_text = '\n'.join(lines[toc_start_idx:toc_end_idx])
        
        # Main text is everything after table of contents
        self.main_text = '\n'.join(lines[toc_end_idx:])
        
        return self.title_page, self.toc_text, self.main_text
    
    def parse_table_of_contents(self, toc_text):
        """Parse table of contents to extract structure and create hyperlinks."""
        lines = toc_text.split('\n')
        structure = []
        current_section = None
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped == "CONTENTS":
                continue
            
            # Check if this is a section heading (ALL CAPS, no number prefix)
            # Sections are like "THE DESIRING-MACHINES", "PSYCHOANALYSIS AND FAMILIALISM: THE HOLY FAMILY"
            if self.is_all_caps_heading(stripped) and not re.match(r'^\d+\.', stripped):
                # This is a section
                section_name = stripped.split('  ')[0].strip()  # Remove page numbers
                current_section = {
                    'type': 'section',
                    'name': section_name,
                    'chapters': []
                }
                structure.append(current_section)
            elif current_section and re.match(r'^\d+\.', stripped):
                # This is a chapter within current section
                # Format: "1. Desiring-Production I" or "1. The Imperialism of Oedipus 51"
                match = re.match(r'^(\d+)\.\s+(.+?)(?:\s+\d+)?$', stripped)
                if match:
                    chapter_num = match.group(1)
                    chapter_title = match.group(2).strip()
                    current_section['chapters'].append({
                        'number': chapter_num,
                        'title': chapter_title
                    })
            elif not current_section and re.match(r'^[A-Z\s:,\-\']+$', stripped):
                # Standalone entry (like PREFACE, INTRODUCTION)
                if stripped not in ["CONTENTS", "REFERENCE NOTES", "INDEX"]:
                    structure.append({
                        'type': 'standalone',
                        'name': stripped.split('  ')[0].strip()
                    })
        
        self.toc_structure = structure
        return structure
    
    def is_all_caps_heading(self, line):
        """Check if a line is an ALL CAPS heading (not just any ALL CAPS text)."""
        stripped = line.strip()
        if len(stripped) < 3:
            return False
        
        # Must be mostly uppercase
        upper_count = sum(1 for c in stripped if c.isupper())
        total_letters = sum(1 for c in stripped if c.isalpha())
        
        if total_letters == 0:
            return False
        
        # At least 80% uppercase
        if upper_count / total_letters >= 0.8:
            # Check if it matches heading pattern (allows punctuation, spaces, numbers)
            if re.match(r'^[A-Z\s:,\-\'\d\.]+$', stripped):
                return True
        
        return False
    
    def create_toc_markdown(self):
        """Create markdown table of contents with hyperlinks."""
        if not self.toc_structure:
            return ""
        
        toc_lines = ["# Table of Contents", ""]
        
        for item in self.toc_structure:
            if item['type'] == 'standalone':
                # Create anchor from name
                anchor = self.create_anchor(item['name'])
                toc_lines.append(f"- [{item['name']}](#{anchor})")
            elif item['type'] == 'section':
                # Section heading
                anchor = self.create_anchor(item['name'])
                toc_lines.append(f"\n## {item['name']}")
                toc_lines.append("")
                
                # Chapters in this section
                for chapter in item['chapters']:
                    chapter_anchor = self.create_anchor(f"{chapter['number']} {chapter['title']}")
                    toc_lines.append(f"  - [{chapter['number']}. {chapter['title']}](#{chapter_anchor})")
        
        return '\n'.join(toc_lines)
    
    def create_anchor(self, text):
        """Create markdown anchor from text."""
        # Convert to lowercase, replace spaces and special chars with hyphens
        anchor = text.lower()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'[-\s]+', '-', anchor)
        anchor = anchor.strip('-')
        return anchor
    
    def identify_structure_in_text(self, text):
        """Identify sections (## ALL CAPS) and chapters (# number + title) in text."""
        lines = text.split('\n')
        processed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Empty line - preserve it
            if not stripped:
                processed_lines.append('')
                i += 1
                continue
            
            # Check if previous line was empty (section boundary)
            prev_line_empty = (i == 0 or not lines[i-1].strip())
            
            # Check for section marker: blank line + ## + ALL CAPS heading
            # Handle both numbered (## 3 SAVAGES...) and unnumbered (## THE DESIRING-MACHINES)
            if prev_line_empty:
                if stripped.startswith('## '):
                    section_text = stripped[3:].strip()
                    # Remove leading number if present (e.g., "3 SAVAGES..." -> "SAVAGES...")
                    section_text_clean = re.sub(r'^\d+\s+', '', section_text)
                    if self.is_all_caps_heading(section_text_clean):
                        # This is a section marker - keep it as is
                        processed_lines.append(stripped)
                        i += 1
                        continue
                elif stripped.startswith('# ') and not stripped.startswith('## '):
                    # Check for chapter marker: # number Title (e.g., "# 1 Desiring-Production")
                    if re.match(r'^#\s+\d+\s+[A-Z]', stripped):
                        # This is a chapter marker - keep it as is
                        processed_lines.append(stripped)
                        i += 1
                        continue
                    # Check if it's a plain ALL CAPS heading that should become a section
                    elif self.is_all_caps_heading(stripped[2:]):
                        # Convert to section heading
                        processed_lines.append(f"## {stripped[2:]}")
                        i += 1
                        continue
                elif self.is_all_caps_heading(stripped):
                    # Plain ALL CAPS at section boundary - could be a section heading
                    # But check if it should be removed first (page header)
                    if self.should_remove_all_caps(stripped):
                        i += 1
                        continue
                    # Otherwise, convert to section heading
                    processed_lines.append(f"## {stripped}")
                    i += 1
                    continue
            
            # Check for page numbers (standalone numbers or roman numerals)
            if self.is_page_number(stripped):
                i += 1
                continue
            
            # Check if this is an ALL CAPS line that should be removed
            # (page headers, repeated section names with page numbers, etc.)
            if self.is_all_caps_heading(stripped):
                # Don't remove if it's already a markdown heading
                if stripped.startswith('#'):
                    processed_lines.append(line)
                    i += 1
                    continue
                
                # Check if it should be removed
                if self.should_remove_all_caps(stripped):
                    i += 1
                    continue
            
            # Preserve the line
            processed_lines.append(line)
            i += 1
        
        return '\n'.join(processed_lines)
    
    def should_remove_all_caps(self, line):
        """Determine if an ALL CAPS line should be removed."""
        stripped = line.strip()
        
        # Remove if it's a known page header pattern
        known_headers = [
            "CAPITALISM AND SCHIZOPHRENIA",
            "ANTI-OEDIPUS",
            "CONTENTS",
            "ACKNOWLEDGMENTS"
        ]
        
        for header in known_headers:
            if header in stripped or stripped in header:
                return True
        
        # Remove if it's a section/chapter name followed by a page number
        # Pattern: "SECTION NAME 123" or "CHAPTER NAME 123"
        # Examples: "THE DESIRING-MACHINES 49", "PSYCHOANALYSIS AND FAMILIALISM: THE HOLY FAMILY 137"
        if re.match(r'^[A-Z\s:,\-\']+\s+\d+$', stripped):
            return True
        
        # Remove if it matches section/chapter names from TOC followed by numbers
        # Check if it ends with a number and matches known section/chapter names
        match = re.match(r'^([A-Z\s:,\-\']+?)\s+(\d+)$', stripped)
        if match:
            name_part = match.group(1).strip()
            # Check if this matches any section or chapter name from TOC
            for item in self.toc_structure:
                if item['type'] == 'section':
                    if name_part == item['name'] or item['name'] in name_part:
                        return True
                    for chapter in item.get('chapters', []):
                        if name_part == chapter['title'] or chapter['title'] in name_part:
                            return True
                elif item['type'] == 'standalone':
                    if name_part == item['name'] or item['name'] in name_part:
                        return True
        
        # Remove if it's very short (likely a page header)
        if len(stripped) < 5:
            return True
        
        return False
    
    def is_page_number(self, line):
        """Check if a line is a page number."""
        stripped = line.strip()
        
        # Standalone roman numerals or numbers
        if re.match(r'^[xivlcdmIVXLCDM]+$', stripped) and len(stripped) < 10:
            return True
        if re.match(r'^\d+$', stripped) and len(stripped) < 4:
            return True
        
        # Page number with text (e.g., "9, ANTI-OEDIPUS")
        if re.match(r'^[xivlcdmIVXLCDM\d]+\s*[,]?\s*[A-Z\s:,\-\']*$', stripped):
            # Check if it starts with a number/roman numeral
            if re.match(r'^[xivlcdmIVXLCDM\d]+', stripped):
                return True
        
        return False
    
    def chunk_text_by_structure(self, text):
        """Chunk text by sections - each section (## ALL CAPS heading) becomes one chunk."""
        lines = text.split('\n')
        chunks = []
        
        # Find all section boundaries (lines starting with ## )
        section_indices = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('## '):
                section_indices.append(i)
        
        # If no sections found, return entire text as one chunk
        if not section_indices:
            return [text]
        
        # Process each section
        for section_idx in range(len(section_indices)):
            start_idx = section_indices[section_idx]
            # End index is start of next section, or end of text
            end_idx = section_indices[section_idx + 1] if section_idx + 1 < len(section_indices) else len(lines)
            
            # Extract section lines
            section_lines = lines[start_idx:end_idx]
            section_text = '\n'.join(section_lines)
            
            # Only add non-empty chunks
            if section_text.strip():
                chunks.append(section_text)
        
        return chunks
    
    def _get_system_prompt(self):
        """Get the system prompt for AI processing."""
        return """You are a text formatting expert. Your task is to convert plain text to properly formatted markdown.

CRITICAL RULES - FOLLOW EXACTLY:
1. Preserve EVERY SINGLE WORD - never summarize, omit, or skip any text
2. Empty lines indicate section divisions - preserve them
3. Chapter headings (#) and section headings (##) have already been added - preserve them exactly
4. Format footnotes/references appropriately (use [^1] style or keep inline)
5. Preserve ALL paragraph structure and line breaks exactly as they appear
6. Format lists with proper markdown syntax (- or 1.)
7. Use markdown formatting for emphasis (*italic* or **bold**) where appropriate
8. Maintain proper spacing around headings and sections
9. Format block quotes with > if present
10. Keep all original text content - return the COMPLETE text with markdown formatting
11. Do NOT add or remove chapter/section headings - they are already correctly placed
12. Do NOT remove UPPER CASE text that is part of the actual content (only headers have been removed)
13. Ensure headings have proper markdown anchor formatting for table of contents links

Return ONLY the formatted markdown text. Include ALL content. No explanations."""
    
    def _get_user_prompt(self, preprocessed, chunk_num, total_chunks):
        """Get the user prompt for AI processing."""
        return f"""Convert this text chunk ({chunk_num} of {total_chunks}) to markdown format.

The text has already been preprocessed to:
- Remove page headers and page numbers
- Identify and preserve section headings (## ALL CAPS) and chapter headings (# number + title)
- Preserve empty lines as section divisions

IMPORTANT: This chunk was split at section/chapter boundaries to maintain structure.
- Empty lines indicate section divisions - preserve them exactly
- Maintain continuity with previous chunks (if any)
- Format the remaining text properly (lists, emphasis, quotes, etc.)
- Preserve all content exactly as it appears
- Maintain the structure that has been established
- Ensure headings are properly formatted for markdown anchors

Text to convert:
{preprocessed}"""
    
    def process_chunk_single(self, preprocessed_text):
        """Process entire text as single chunk (for better continuity)."""
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(preprocessed_text, 1, 1)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=160000  # Much higher for single chunk
            )
            result = response.choices[0].message.content.strip()
            
            if not result:
                print("Warning: Single chunk returned empty result. Using preprocessed text.")
                return preprocessed_text
            
            if len(result) < len(preprocessed_text) * 0.5:
                print(f"Warning: Single chunk result seems truncated. Original: {len(preprocessed_text)} chars, Result: {len(result)} chars")
                print("  Using preprocessed text instead.")
                return preprocessed_text
            
            return result
        except Exception as e:
            print(f"Error processing single chunk: {e}")
            raise
    
    def process_chunk(self, chunk, chunk_num, total_chunks):
        """Process a chunk of text with AI to identify structure."""
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(chunk, chunk_num, total_chunks)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Lower temperature for more consistent formatting
                max_tokens=16000  # Allow for large output
            )
            result = response.choices[0].message.content.strip()
            
            # Verify we got substantial content back
            if not result:
                print(f"Warning: Chunk {chunk_num} returned empty result. Using preprocessed text.")
                return chunk
            
            # Check if result seems truncated (less than 50% of original)
            if len(result) < len(chunk) * 0.5:
                print(f"Warning: Chunk {chunk_num} result seems truncated. Original: {len(chunk)} chars, Result: {len(result)} chars")
                print(f"  Using preprocessed text instead.")
                return chunk
            
            return result
        except Exception as e:
            print(f"Error processing chunk {chunk_num}: {e}")
            print(f"  Using preprocessed text as fallback.")
            return chunk
    
    def merge_chunks(self, formatted_chunks):
        """Merge formatted chunks, preserving structure."""
        if not formatted_chunks:
            return ""
        
        if len(formatted_chunks) == 1:
            return formatted_chunks[0]
        
        # Merge chunks, preserving empty line boundaries
        merged = formatted_chunks[0]
        
        for i in range(1, len(formatted_chunks)):
            current = formatted_chunks[i]
            
            # Remove leading/trailing whitespace but preserve structure
            current_stripped = current.strip()
            if not current_stripped:
                continue
            
            # Check if merged ends with empty line(s) and current starts with empty line(s)
            merged_ends_newline = merged.endswith('\n')
            current_starts_newline = current.startswith('\n')
            
            if merged_ends_newline and current_starts_newline:
                # Both have newlines - merge directly (empty line boundary preserved)
                merged += current
            elif merged_ends_newline:
                # Merged ends with newline, current doesn't start with one
                # Add one newline to preserve section division
                merged += '\n' + current
            elif current_starts_newline:
                # Current starts with newline, merged doesn't end with one
                # Merge directly (newline in current preserves boundary)
                merged += current
            else:
                # Neither has newline at boundary - add one to preserve section division
                merged += '\n\n' + current
        
        return merged
    
    def post_process(self, markdown_text):
        """Post-process the markdown to clean up and ensure consistency."""
        # Remove excessive blank lines (but preserve section divisions)
        markdown_text = re.sub(r'\n{4,}', '\n\n\n', markdown_text)
        
        # Ensure proper spacing around headings
        markdown_text = re.sub(r'\n(#{1,6}[^\n]+)\n([^\n#])', r'\n\1\n\n\2', markdown_text)
        
        # Clean up any remaining page number markers
        markdown_text = re.sub(r'\[Page\s+([^\]]+)\]', r'', markdown_text)
        
        return markdown_text
    
    def convert(self):
        """Main conversion process."""
        print(f"Reading {self.input_file}...")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"Text length: {len(text)} characters")
        print("Parsing text structure (title page, table of contents, main text)...")
        title_page, toc_text, main_text = self.parse_text_structure(text)
        
        print(f"  Title page: {len(title_page)} characters")
        print(f"  Table of contents: {len(toc_text)} characters")
        print(f"  Main text: {len(main_text)} characters")
        
        print("\nParsing table of contents to extract structure...")
        self.parse_table_of_contents(toc_text)
        print(f"  Found {len(self.toc_structure)} sections/entries")
        
        print("\nCreating table of contents with hyperlinks...")
        toc_markdown = self.create_toc_markdown()
        
        print("\nPreprocessing main text (identifying structure, removing headers)...")
        preprocessed_text = self.identify_structure_in_text(main_text)
        print(f"Preprocessed text length: {len(preprocessed_text)} characters")
        
        # Single chunk mode - process entire text at once
        if self.single_chunk:
            print(f"\nProcessing entire text as single chunk with AI ({self.model})...")
            print(f"Processing ({len(preprocessed_text)} characters)...")
            try:
                final_markdown = self.process_chunk_single(preprocessed_text)
            except Exception as e:
                print(f"Error processing single chunk: {e}")
                print("Falling back to chunked processing...")
                # Fall back to chunked mode
                chunks = self.chunk_text_by_structure(preprocessed_text)
                formatted_chunks = []
                for i, chunk in enumerate(tqdm(chunks, desc="Processing")):
                    formatted = self.process_chunk(chunk, i+1, len(chunks))
                    formatted_chunks.append(formatted)
                final_markdown = self.post_process(self.merge_chunks(formatted_chunks))
            
            print(f"  Result: {len(final_markdown)} characters")
            print("Post-processing...")
            final_markdown = self.post_process(final_markdown)
        else:
            # Chunked mode - one chunk per section
            print("Splitting into chunks by sections (one chunk per section)...")
            chunks = self.chunk_text_by_structure(preprocessed_text)
            total_chunks = len(chunks)
            print(f"Created {total_chunks} section chunk(s)")
            if total_chunks > 1:
                for i, chunk in enumerate(chunks, 1):
                    # Extract section name from chunk for display
                    chunk_lines = chunk.split('\n')
                    section_name = "Unknown"
                    for line in chunk_lines[:5]:  # Look in first 5 lines
                        if line.strip().startswith('## '):
                            section_name = line.strip()[3:].strip()
                            break
                    print(f"  Section {i}: {section_name} ({len(chunk):,} characters)")
            
            # Limit chunks in test mode or if max_chunks is specified
            if self.test_mode:
                limit = self.max_chunks if self.max_chunks else 1  # Test with 1 chunk by default
                chunks = chunks[:limit]
                print(f"Test mode: Processing only first {len(chunks)} chunk(s)")
            elif self.max_chunks:
                chunks = chunks[:self.max_chunks]
                print(f"Limiting to first {len(chunks)} chunk(s)")
            
            print(f"\nProcessing {len(chunks)} chunk(s) with AI ({self.model})...")
            formatted_chunks = []
            
            for i, chunk in enumerate(tqdm(chunks, desc="Processing")):
                print(f"\nProcessing chunk {i+1}/{len(chunks)} ({len(chunk)} characters)...")
                formatted = self.process_chunk(chunk, i+1, len(chunks))
                formatted_chunks.append(formatted)
                print(f"  Result: {len(formatted)} characters")
            
            print("\nMerging chunks...")
            merged = self.merge_chunks(formatted_chunks)
            
            print("Post-processing...")
            final_markdown = self.post_process(merged)
        
        # Combine title page, table of contents, and main text
        print("\nCombining title page, table of contents, and main text...")
        complete_markdown = f"{self.title_page}\n\n{toc_markdown}\n\n{final_markdown}"
        
        # Display results in test mode
        if self.test_mode:
            print("\n" + "="*80)
            print("TEST MODE RESULTS (first 2000 characters):")
            print("="*80)
            print(complete_markdown[:2000])
            if len(complete_markdown) > 2000:
                print(f"\n... (truncated, total length: {len(complete_markdown)} characters)")
            print("="*80 + "\n")
        
        print(f"\nWriting to {self.output_file}...")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(complete_markdown)
        
        print(f"\n✓ Conversion complete! Output saved to {self.output_file}")
        print(f"  Original size: {len(text):,} characters")
        print(f"  Markdown size: {len(complete_markdown):,} characters")
        if not self.single_chunk:
            print(f"  Processed {len(chunks)} chunk(s) (of {total_chunks} total)")
        else:
            print(f"  Processed as single chunk")
        if len(complete_markdown) < len(text) * 0.8:
            print(f"  ⚠ Warning: Output is significantly shorter than input. Some content may be missing.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert Anti-Oedipus.txt to markdown format")
    parser.add_argument("--input", "-i", default="Anti-Oedipus.txt", help="Input text file")
    parser.add_argument("--output", "-o", default="Anti-Oedipus.md", help="Output markdown file")
    parser.add_argument("--test", action="store_true", help="Test mode: process only first chunk and display results")
    parser.add_argument("--max-chunks", type=int, help="Maximum number of chunks to process")
    parser.add_argument("--single-chunk", action="store_true", help="Process entire text as single chunk (better continuity, requires larger model)")
    args = parser.parse_args()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file or environment")
        return
    
    input_file = args.input
    output_file = args.output
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return
    
    # In test mode, default to 1 chunk unless max-chunks is explicitly set
    max_chunks = args.max_chunks if args.max_chunks else (1 if args.test else None)
    converter = TextToMarkdownConverter(input_file, output_file, api_key, 
                                       test_mode=args.test, max_chunks=max_chunks,
                                       single_chunk=args.single_chunk)
    converter.convert()

if __name__ == "__main__":
    main()
