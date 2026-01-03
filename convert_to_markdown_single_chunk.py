#!/usr/bin/env python3
"""
Convert Anti-Oedipus.txt to markdown format using AI - SINGLE CHUNK VERSION.

This version processes the entire text as one large chunk for maximum continuity.
Use this when you want the AI to see the full context of the document.

Usage:
    # Full conversion (requires OpenAI API key in .env)
    python3 convert_to_markdown_single_chunk.py
    
    # Custom input/output files
    python3 convert_to_markdown_single_chunk.py -i input.txt -o output.md

Note: This script processes entire text in one chunk for better continuity.
Available models:
- gpt-4o-mini: 128k tokens (default, may not work for very large files)
- o1-preview: 200k tokens (larger context, more expensive)
- o1-mini: 200k tokens (larger context, cheaper than o1-preview)
- claude-3-5-sonnet-20241022: 200k tokens (Anthropic, requires ANTHROPIC_API_KEY)

For files >300k tokens, consider using --model o1-preview or chunked processing.
"""

import os
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Hard-coded chapter names from the table of contents
CHAPTER_NAMES = [
    "PREFACE",
    "INTRODUCTION",
    "THE DESIRING-MACHINES",
    "PSYCHOANALYSIS AND FAMILIALISM: THE HOLY FAMILY",
    "SAVAGES, BARBARIANS, CIVILIZED MEN",
    "INTRODUCTION TO SCHIZOANALYSIS",
    "REFERENCE NOTES",
    "INDEX"
]

# Known page headers/footers that should be removed (UPPER CASE text at top/bottom of pages)
PAGE_HEADERS = [
    "CAPITALISM AND SCHIZOPHRENIA",
    "ANTI-OEDIPUS",
    "CONTENTS",
    "ACKNOWLEDGMENTS"
]

class TextToMarkdownConverterSingleChunk:
    def __init__(self, input_file, output_file, api_key, model="gpt-4o-mini", use_anthropic=False):
        self.input_file = input_file
        self.output_file = output_file
        self.model = model
        self.use_anthropic = use_anthropic
        
        if use_anthropic:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("Anthropic SDK not installed. Install with: pip install anthropic")
        else:
            self.client = OpenAI(api_key=api_key)
        
    def read_text(self):
        """Read and preprocess the input text file."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove table of contents (lines 17-219 based on user's selection)
        # Find the CONTENTS line and remove until we hit the first actual chapter
        toc_start = None
        toc_end = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "CONTENTS":
                toc_start = i
            elif toc_start is not None and stripped == "PREFACE":
                toc_end = i
                break
        
        if toc_start is not None and toc_end is not None:
            # Remove the table of contents
            lines = lines[:toc_start] + lines[toc_end:]
        
        text = ''.join(lines)
        
        # Clean up the text: normalize whitespace, remove excessive blank lines
        # But preserve paragraph structure
        text = re.sub(r'\r\n', '\n', text)  # Normalize line endings
        text = re.sub(r'\n{4,}', '\n\n\n', text)  # Max 3 blank lines
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces (but keep newlines)
        text = re.sub(r' +\n', '\n', text)  # Remove trailing spaces
        
        return text
    
    def is_all_caps_line(self, line):
        """Check if a line is entirely ALL CAPS (with some punctuation allowed)."""
        stripped = line.strip()
        
        # Must be all uppercase (or mostly uppercase with some punctuation and numbers)
        # Allow for some lowercase if it's a very short line (like "by Author")
        if len(stripped) < 3:
            return False
        
        # Check if it's mostly/all uppercase
        # Count uppercase letters
        upper_count = sum(1 for c in stripped if c.isupper())
        total_letters = sum(1 for c in stripped if c.isalpha())
        
        if total_letters == 0:
            return False
        
        # If more than 80% are uppercase, consider it ALL CAPS
        if upper_count / total_letters >= 0.8:
            # Must match pattern of ALL CAPS (allows punctuation, spaces, numbers)
            if re.match(r'^[A-Z\s:,\-\'\d\.]+$', stripped):
                return True
        
        return False
    
    def is_page_header(self, line):
        """Check if a line is a page header/footer (UPPER CASE text that should be removed)."""
        if not self.is_all_caps_line(line):
            return False
        
        stripped = line.strip()
        
        # Check if it matches known page headers
        for header in PAGE_HEADERS:
            if header in stripped or stripped in header:
                return True
        
        # Check if it matches a chapter name (these appear as headers on pages)
        for chapter in CHAPTER_NAMES:
            # Handle partial matches (e.g., "INTRODUCTION" matches "INTRODUCTION TO SCHIZOANALYSIS")
            if chapter in stripped or stripped in chapter:
                return True
        
        # Any ALL CAPS line that's reasonably short is likely a header
        if len(stripped) > 3 and len(stripped) < 200:
            return True
        
        return False
    
    def is_multi_line_header(self, lines, start_idx):
        """Check if multiple consecutive lines form a page header."""
        # Look ahead up to 5 lines to see if they form a header together
        header_lines = []
        for i in range(start_idx, min(start_idx + 5, len(lines))):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                break
            # Check if line is ALL CAPS (using our detection function)
            if self.is_all_caps_line(line):
                header_lines.append(stripped)
            else:
                break
        
        if len(header_lines) < 2:
            return False, 0
        
        # Combine the lines and check if they form a known header
        combined = ' '.join(header_lines).replace('  ', ' ')  # Normalize spaces
        
        # Check if combined text matches known page headers
        for header in PAGE_HEADERS:
            if header in combined or combined in header:
                return True, len(header_lines)
        
        # Check if combined text matches chapter names
        for chapter in CHAPTER_NAMES:
            # Remove numbers and normalize for comparison
            combined_clean = re.sub(r'\d+', '', combined).strip()
            chapter_clean = chapter.strip()
            if chapter_clean in combined_clean or combined_clean in chapter_clean:
                return True, len(header_lines)
            # Also check if the combined text contains the chapter name
            if chapter in combined:
                return True, len(header_lines)
        
        # If all lines are ALL CAPS and form a reasonable header, treat as header
        return True, len(header_lines)
    
    def is_page_number(self, line):
        """Check if a line is a page number (standalone or with chapter name)."""
        stripped = line.strip()
        
        # Standalone roman numerals or numbers
        if re.match(r'^[xivlcdmIVXLCDM]+$', stripped) and len(stripped) < 10:
            return True
        if re.match(r'^\d+$', stripped) and len(stripped) < 4:
            return True
        
        # Page number with chapter name (e.g., "xl PREFACE", "9, ANTI-OEDIPUS")
        # Pattern: optional number/roman numeral, optional comma, optional chapter name
        page_pattern = r'^[xivlcdmIVXLCDM\d]+\s*[,]?\s*[A-Z\s:,\-\']*$'
        if re.match(page_pattern, stripped):
            # Check if it contains a chapter name
            for chapter in CHAPTER_NAMES:
                if chapter in stripped:
                    return True
            # Check if it starts with a number/roman numeral
            if re.match(r'^[xivlcdmIVXLCDM\d]+', stripped):
                return True
        
        return False
    
    def detect_chapter(self, lines, start_idx):
        """Detect which chapter we're currently in by looking ahead."""
        # Look ahead up to 10 lines to find chapter markers
        for i in range(start_idx, min(start_idx + 10, len(lines))):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check for exact chapter name matches
            for chapter in CHAPTER_NAMES:
                # Check if line starts with chapter name (most common case)
                if line.startswith(chapter):
                    # Make sure it's not just part of a longer sentence
                    # If the line is short or ends shortly after the chapter name, it's likely a heading
                    if len(line) <= len(chapter) + 100:  # Allow some text after (e.g., "by Author")
                        return chapter
                # Check if chapter name appears in line and line is short (for cases like "PREFACE by Michel Foucault")
                elif chapter in line and len(line) < 200:
                    # Make sure it's not just mentioned in the middle of content
                    # Check if chapter name is near the start of the line
                    chapter_pos = line.find(chapter)
                    if chapter_pos < 50:  # Chapter name appears near the start
                        return chapter
        
        return None
    
    def preprocess_text(self, text):
        """Preprocess text to remove headers, page numbers, and identify structure."""
        lines = text.split('\n')
        processed_lines = []
        current_chapter = None
        chapter_heading_added = {}  # Track which chapters have had headings added
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Empty line - section division
            if not stripped:
                processed_lines.append('')
                i += 1
                continue
            
            # Check if this is a page number (standalone or with chapter name)
            if self.is_page_number(stripped):
                # Skip page numbers
                i += 1
                continue
            
            # Check for multi-line headers first
            is_header, header_lines_count = self.is_multi_line_header(lines, i)
            if is_header:
                # Check if it's actually a chapter heading (first occurrence)
                detected_chapter = self.detect_chapter(lines, i + header_lines_count)
                if detected_chapter and detected_chapter not in chapter_heading_added:
                    # This is the actual chapter heading, keep it
                    processed_lines.append('')
                    processed_lines.append(f"# {detected_chapter}")
                    processed_lines.append('')
                    current_chapter = detected_chapter
                    chapter_heading_added[detected_chapter] = True
                    i += header_lines_count
                    continue
                else:
                    # This is a repeated page header, skip it
                    i += header_lines_count
                    continue
            
            # Check if this is an ALL CAPS line (more aggressive detection)
            if self.is_all_caps_line(line):
                # Check if it's actually a chapter heading (first occurrence)
                detected_chapter = self.detect_chapter(lines, i)
                if detected_chapter and detected_chapter not in chapter_heading_added:
                    # Check if previous line was empty (indicates section start)
                    prev_line_empty = (i == 0 or not lines[i-1].strip())
                    if prev_line_empty:
                        # This is the actual chapter heading, keep it
                        processed_lines.append('')
                        processed_lines.append(f"# {detected_chapter}")
                        processed_lines.append('')
                        current_chapter = detected_chapter
                        chapter_heading_added[detected_chapter] = True
                        i += 1
                        continue
                
                # If it's a page header or repeated chapter name, remove it
                if self.is_page_header(stripped):
                    i += 1
                    continue
            
            # Check if we're entering a new chapter (by detecting chapter name in content)
            # Only check if previous line was empty (section break) or we're at the start
            prev_line_empty = (i == 0 or not lines[i-1].strip())
            if prev_line_empty:
                detected_chapter = self.detect_chapter(lines, i)
                if detected_chapter and detected_chapter != current_chapter:
                    if detected_chapter not in chapter_heading_added:
                        processed_lines.append('')
                        processed_lines.append(f"# {detected_chapter}")
                        processed_lines.append('')
                        current_chapter = detected_chapter
                        chapter_heading_added[detected_chapter] = True
            
            # Detect numbered sections (e.g., "1. Title", "1 Desiring-Production")
            if re.match(r'^\d+[\.\s]+[A-Z]', stripped):
                # Extract section number and title
                match = re.match(r'^(\d+)[\.\s]+(.+)$', stripped)
                if match:
                    section_num = match.group(1)
                    section_title = match.group(2).strip()
                    processed_lines.append('')
                    processed_lines.append(f"## {section_num}. {section_title}")
                    processed_lines.append('')
                    i += 1
                    continue
            
            # Preserve original line
            processed_lines.append(line)
            i += 1
        
        return '\n'.join(processed_lines)
    
    def _estimate_tokens(self, text):
        """Rough token estimation: ~4 characters per token."""
        return len(text) // 4
    
    def process_single_chunk(self, preprocessed_text):
        """Process entire text as single chunk (for better continuity)."""
        system_prompt = """You are a text formatting expert. Your task is to convert plain text to properly formatted markdown.

CRITICAL RULES - FOLLOW EXACTLY:
1. Preserve EVERY SINGLE WORD - never summarize, omit, or skip any text
2. Empty lines indicate section divisions - preserve them
3. Chapter headings (#) and section headings (##) have already been added - preserve them
4. Format footnotes/references appropriately (use [^1] style or keep inline)
5. Preserve ALL paragraph structure and line breaks exactly as they appear
6. Format lists with proper markdown syntax (- or 1.)
7. Use markdown formatting for emphasis (*italic* or **bold**) where appropriate
8. Maintain proper spacing around headings and sections
9. Format block quotes with > if present
10. Keep all original text content - return the COMPLETE text with markdown formatting
11. Do NOT add or remove chapter/section headings - they are already correctly placed
12. Do NOT remove UPPER CASE text that is part of the actual content (only headers have been removed)
13. Maintain continuity throughout the entire document - you have the full context

Return ONLY the formatted markdown text. Include ALL content. No explanations."""

        user_prompt = f"""Convert this entire text to markdown format.

The text has already been preprocessed to:
- Remove page headers and page numbers
- Add chapter headings (#) and section headings (##)
- Preserve empty lines as section divisions

Your task is to:
- Format the remaining text properly (lists, emphasis, quotes, etc.)
- Preserve all content exactly as it appears
- Maintain the structure that has been established
- Keep continuity throughout the document since you have the full context

Text to convert:
{preprocessed_text}"""
        
        try:
            if self.use_anthropic:
                # Anthropic API format
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,  # Anthropic uses different max_tokens (output limit)
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                result = response.content[0].text.strip()
            else:
                # OpenAI API format
                max_output_tokens = 160000 if "o1" in self.model else 16000
                if "o1" in self.model:
                    # o1 models don't support system messages, use user message
                    full_prompt = f"{system_prompt}\n\n{user_prompt}"
                    messages = [{"role": "user", "content": full_prompt}]
                else:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_output_tokens
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
        text = self.read_text()
        
        print(f"Text length: {len(text)} characters")
        print("Preprocessing text (removing headers, page numbers, adding chapter headings)...")
        preprocessed_text = self.preprocess_text(text)
        print(f"Preprocessed text length: {len(preprocessed_text)} characters")
        
        # Check if text is too large before processing
        estimated_tokens = len(preprocessed_text) // 4
        model_limits = {
            "gpt-4o-mini": 128000,
            "gpt-4o": 128000,
            "o1-preview": 200000,
            "o1-mini": 200000,
            "claude-3-5-sonnet-20241022": 200000,
            "claude-3-opus-20240229": 200000,
        }
        limit = model_limits.get(self.model, 128000)
        
        if estimated_tokens > limit:
            print(f"\n⚠ ERROR: Text too large for single-chunk processing!")
            print(f"  Estimated tokens: ~{estimated_tokens:,}")
            print(f"  Model limit: {limit:,} tokens")
            print(f"  Exceeds limit by: {estimated_tokens - limit:,} tokens")
            print(f"\nOptions:")
            print(f"  1. Use chunked processing: python3 convert_to_markdown.py")
            print(f"  2. Try a larger model: --model o1-preview (200k tokens)")
            print(f"  3. Use Claude API: --anthropic --model claude-3-5-sonnet-20241022")
            print(f"\nNote: Even 200k token models may not work for files >250k tokens.")
            print(f"      Consider using chunked processing for better reliability.")
            return
        
        print(f"\nProcessing entire text as single chunk with AI ({self.model})...")
        print(f"Processing ({len(preprocessed_text)} characters)...")
        print(f"Estimated tokens: ~{estimated_tokens:,} (limit: {limit:,})")
        
        try:
            final_markdown = self.process_single_chunk(preprocessed_text)
            print(f"  Result: {len(final_markdown)} characters")
        except Exception as e:
            error_msg = str(e)
            if "context_length_exceeded" in error_msg or "maximum context length" in error_msg:
                print(f"\n⚠ ERROR: Text exceeds model context limit!")
                print(f"  {error_msg}")
                print(f"\nRecommendation: Use chunked processing instead:")
                print(f"  python3 convert_to_markdown.py")
                return
            else:
                print(f"Error: {e}")
                print("Using preprocessed text as fallback.")
                final_markdown = preprocessed_text
        
        print("Post-processing...")
        final_markdown = self.post_process(final_markdown)
        
        print(f"\nWriting to {self.output_file}...")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(final_markdown)
        
        print(f"\n✓ Conversion complete! Output saved to {self.output_file}")
        print(f"  Original size: {len(text):,} characters")
        print(f"  Markdown size: {len(final_markdown):,} characters")
        print(f"  Processed as single chunk for maximum continuity")
        if len(final_markdown) < len(text) * 0.8:
            print(f"  ⚠ Warning: Output is significantly shorter than input. Some content may be missing.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert Anti-Oedipus.txt to markdown format (single chunk version)")
    parser.add_argument("--input", "-i", default="Anti-Oedipus.txt", help="Input text file")
    parser.add_argument("--output", "-o", default="Anti-Oedipus.md", help="Output markdown file")
    parser.add_argument("--model", "-m", default="gpt-4o-mini", 
                       help="Model to use: gpt-4o-mini (128k), o1-preview (200k), o1-mini (200k), claude-3-5-sonnet-20241022 (200k)")
    parser.add_argument("--anthropic", action="store_true", help="Use Anthropic API (requires ANTHROPIC_API_KEY)")
    args = parser.parse_args()
    
    # Determine which API key to use
    if args.anthropic or "claude" in args.model.lower():
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not found in environment variables")
            print("Please set it in your .env file or environment")
            return
        use_anthropic = True
        if "claude" not in args.model.lower():
            args.model = "claude-3-5-sonnet-20241022"
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables")
            print("Please set it in your .env file or environment")
            return
        use_anthropic = False
    
    input_file = args.input
    output_file = args.output
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return
    
    print(f"Using model: {args.model}")
    if use_anthropic:
        print("Using Anthropic API")
    else:
        print("Using OpenAI API")
    
    converter = TextToMarkdownConverterSingleChunk(input_file, output_file, api_key, 
                                                   model=args.model, use_anthropic=use_anthropic)
    converter.convert()

if __name__ == "__main__":
    main()

