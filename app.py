from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
import os
from rag import RAGSystem
from openai import OpenAI
import math
from markupsafe import Markup
import markdown

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key")

API_KEY = os.getenv("OPENAI_API_KEY")
APP_PASSWORD = os.getenv("APP_PASSWORD")

# Initialize RAG System - use markdown file only
markdown_file = "Anti-Oedipus.md"
if not os.path.exists(markdown_file):
    raise FileNotFoundError(f"Markdown file {markdown_file} not found")

rag_system = RAGSystem(markdown_file, API_KEY)
client = OpenAI(api_key=API_KEY)

# Full text content for LLM context
FULL_TEXT = None

def get_full_text():
    """Load and return the full text content of the book."""
    global FULL_TEXT
    if FULL_TEXT is not None:
        return FULL_TEXT
    
    if not os.path.exists(markdown_file):
        raise FileNotFoundError(f"Markdown file {markdown_file} not found")
    
    with open(markdown_file, "r", encoding="utf-8") as f:
        FULL_TEXT = f.read()
    
    return FULL_TEXT

SYSTEM_PROMPT_BASE = """You are Gilles Deleuze, co-author of Anti-Oedipus with Felix Guattari. You are teaching this work through intuitive explanations and direct citations from the book.

CRITICAL: Always respond using "we" to refer to yourself and your co-author Guattari, as this work was written collaboratively. Never use "I" alone - always use "we" when speaking about the work, concepts, or ideas. For example, say "we wrote", "we argue", "we propose", not "I wrote", "I argue", "I propose".

You have access to relevant passages from Anti-Oedipus. Use your understanding of the entire work to provide comprehensive answers.
Always cite the text directly when explaining concepts, referencing specific passages when relevant. Include chapter numbers and titles when citing.
Your responses should reflect the depth and complexity of the work, drawing connections across different sections when appropriate.
Speak in the voice of Deleuze: philosophical, precise, and engaged with the concepts you developed with Guattari.
"""

# Global text cache
CHAPTERS = []
TOC = []

def slugify(text):
    """Convert text to URL-friendly slug."""
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def parse_markdown_chapters():
    """Parse markdown file into chapters based on h2 headings (##)."""
    global CHAPTERS, TOC
    if CHAPTERS:
        return
    
    if not os.path.exists(markdown_file):
        raise FileNotFoundError(f"Markdown file {markdown_file} not found")
    
    with open(markdown_file, "r", encoding="utf-8") as f:
        raw_text = f.read()
    
    # Parse markdown by chapters (h2 headings)
    import re
    lines = raw_text.split('\n')
    
    # Skip title page (first 15 lines) and table of contents
    # The TOC section has duplicate headings, so we need to find where actual content starts
    # Content starts with "## INTRODUCTION" around line 206
    i = 15
    current_chapter = None
    chapter_num = 0
    
    # Skip past the table of contents section
    # Look for "## INTRODUCTION" which is the first real chapter (not in TOC)
    # The TOC section ends before line 206
    found_first_chapter = False
    while i < len(lines) and i < 300:  # TOC should be well before line 300
        line = lines[i]
        if line.startswith('## '):
            title = line[3:].strip()
            # Look for "INTRODUCTION" - this is the first real chapter, not in TOC
            if title == 'INTRODUCTION':
                found_first_chapter = True
                break
        i += 1
    
    # If we didn't find INTRODUCTION, start from line 200 (after TOC)
    if not found_first_chapter:
        i = 200
        # Find first ## heading from this point
        while i < len(lines):
            if lines[i].startswith('## '):
                break
            i += 1
    
    while i < len(lines):
        line = lines[i]
        
        # Check for h2 headings (##) - these are major chapters
        # Skip the TOC heading itself
        if line.startswith('## ') and 'Table of Contents' not in line:
            # Save previous chapter
            if current_chapter and current_chapter['content']:
                current_chapter['content'] = '\n'.join(current_chapter['content'])
                CHAPTERS.append(current_chapter)
            
            # Start new chapter
            chapter_title = line[3:].strip()  # Remove '## ' prefix
            chapter_num += 1
            current_chapter = {
                'title': chapter_title,
                'slug': slugify(chapter_title) or f"chapter-{chapter_num}",
                'content': []
            }
            i += 1
            continue
        
        # Check for h3 headings (###) - subsections within chapters
        if line.startswith('### '):
            subsection_title = line[4:].strip()
            # Add as part of chapter content
            if current_chapter:
                current_chapter['content'].append(line)
            i += 1
            continue
        
        # Check for h4 headings (####) - subsections within chapters
        if line.startswith('#### '):
            subsection_title = line[5:].strip()
            # Add as part of chapter content
            if current_chapter:
                current_chapter['content'].append(line)
            i += 1
            continue
        
        # Regular content - only add if we have a chapter started
        if current_chapter is not None:
            current_chapter['content'].append(line)
        i += 1
    
    # Add last chapter
    if current_chapter and current_chapter['content']:
        current_chapter['content'] = '\n'.join(current_chapter['content'])
        CHAPTERS.append(current_chapter)
    
    # Build TOC
    TOC = [{'title': ch['title'], 'slug': ch['slug'], 'num': i+1} 
           for i, ch in enumerate(CHAPTERS)]

def get_title_page():
    """Extract and return the title page content (first 15 lines)."""
    if not os.path.exists(markdown_file):
        return ""
    
    with open(markdown_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Get first 15 lines
    title_lines = lines[:15]
    return '\n'.join(line.rstrip() for line in title_lines)

def get_toc_html():
    """Generate HTML for table of contents."""
    html = '<ul class="toc-list">'
    # Add title page link
    html += '<li><a href="?chapter=0">Title Page</a></li>'
    # Add chapter links
    if TOC:
        for item in TOC:
            html += f'<li><a href="?chapter={item["num"]}">{item["title"]}</a></li>'
    html += '</ul>'
    return html

# Clear cache and parse chapters
CHAPTERS = []
TOC = []
parse_markdown_chapters()
# Debug: print number of chapters found
print(f"Parsed {len(CHAPTERS)} chapters")
# Preload full text for LLM context
get_full_text()

@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'test', 'ui_test']
    if request.endpoint not in allowed_routes and 'logged_in' not in session:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid Password")
    return render_template('login.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/ui-test', endpoint='ui_test')
def ui_test():
    print(f"UI_TEST route called, endpoint: {request.endpoint}")
    return render_template('ui-test.html')

@app.route('/')
def index():
    # Support both 'page' (legacy) and 'chapter' parameters
    chapter_num = request.args.get('chapter', type=int)
    page = request.args.get('page', type=int)
    
    # Check if we want the title page (chapter=0 or no chapter specified)
    if chapter_num == 0 or (chapter_num is None and page is None):
        title_page_content = get_title_page()
        total_chapters = len(CHAPTERS)
        return render_template('index.html',
                             is_title_page=True,
                             title_page_content=title_page_content,
                             toc=get_toc_html(),
                             chapter=0,
                             total_chapters=total_chapters,
                             chapter_title="Title Page",
                             prev_chapter=None,
                             next_chapter=1 if total_chapters > 0 else None)
    
    if chapter_num:
        current_chapter = chapter_num
    elif page:
        current_chapter = page
    else:
        current_chapter = 1
    
    total_chapters = len(CHAPTERS)
    
    if current_chapter < 1:
        current_chapter = 1
    if current_chapter > total_chapters:
        current_chapter = total_chapters
    
    # Get current chapter
    chapter = CHAPTERS[current_chapter - 1]
    
    # Render markdown to HTML with extensions
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc', 'fenced_code'])
    html_content = md.convert(chapter['content'])
    
    # Add anchor IDs to headings for TOC links
    import re
    def add_heading_ids(match):
        level = len(match.group(1))
        text = match.group(2)
        slug = slugify(text)
        return f'<h{level} id="{slug}">{text}</h{level}>'
    
    html_content = re.sub(r'<h([1-6])>(.+?)</h\1>', add_heading_ids, html_content)
    
    safe_html_content = Markup(html_content)
    
    # Generate TOC HTML
    toc_html = get_toc_html()
    
    return render_template('index.html', 
                         is_title_page=False,
                         content=safe_html_content,
                         toc=toc_html,
                         chapter=current_chapter,
                         total_chapters=total_chapters,
                         chapter_title=chapter['title'],
                         prev_chapter=current_chapter - 1 if current_chapter > 1 else 0,
                         next_chapter=current_chapter + 1 if current_chapter < total_chapters else None)

@app.route('/api/define', methods=['POST'])
def define():
    data = request.json
    term = data.get('term')
    context = data.get('context') # Surrounding text
    
    # Use RAG to retrieve relevant chunks for the term
    query_text = f"{term} {context}" if context else term
    rag_results = rag_system.query(query_text, k=6)
    
    # Build context from retrieved chunks with chapter information
    context_parts = []
    for result in rag_results:
        chunk_text = result['text']
        metadata = result.get('metadata', {})
        chapter_info = f"Chapter {metadata.get('chapter_num', '?')}: {metadata.get('chapter_title', 'Unknown')}"
        if metadata.get('subsection'):
            chapter_info += f" - {metadata['subsection']}"
        context_parts.append(f"[{chapter_info}]\n{chunk_text}\n")
    
    context_text = "\n---\n\n".join(context_parts)
    
    # Build system prompt with retrieved context
    system_prompt = f"""{SYSTEM_PROMPT_BASE}

You have access to relevant passages from Anti-Oedipus that mention the term. When citing the text, always include the chapter number and title. Here are the relevant passages:

{context_text}

Provide a comprehensive definition based on how this term is used in these passages."""
    
    user_prompt = f"Define the term '{term}' as it is used in Anti-Oedipus."
    if context:
        user_prompt += f" The user has selected this text for context: \"{context}\"."

    response = client.chat.completions.create(
        model="gpt-4o",  # Using gpt-4o for better context handling
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    return jsonify({"definition": response.choices[0].message.content})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    history = data.get('history', [])
    
    # Use RAG to retrieve relevant chunks
    rag_results = rag_system.query(message, k=8)
    
    # Build context from retrieved chunks with chapter information
    context_parts = []
    for result in rag_results:
        chunk_text = result['text']
        metadata = result.get('metadata', {})
        chapter_info = f"Chapter {metadata.get('chapter_num', '?')}: {metadata.get('chapter_title', 'Unknown')}"
        if metadata.get('subsection'):
            chapter_info += f" - {metadata['subsection']}"
        context_parts.append(f"[{chapter_info}]\n{chunk_text}\n")
    
    context_text = "\n---\n\n".join(context_parts)
    
    # Build system prompt with retrieved context
    system_prompt = f"""{SYSTEM_PROMPT_BASE}

You have access to relevant passages from Anti-Oedipus. When citing the text, always include the chapter number and title. Here are the relevant passages:

{context_text}

When answering questions, cite specific chapters and passages. If the user asks about something not covered in the provided passages, acknowledge this and provide your best answer based on your understanding of the work you wrote with Guattari."""
    
    # Build messages array
    # Always prepend the system prompt to ensure it's up to date
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (excluding any existing system messages)
    for msg in history:
        if msg.get('role') != 'system':
            messages.append(msg)
    
    # Add current user message
    messages.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model="gpt-4o",  # Using gpt-4o for better context handling
        messages=messages,
        stream=True,
        temperature=0.8,
        max_tokens=2000
    )

    def generate():
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return app.response_class(generate(), mimetype='text/plain')

@app.route('/api/search', methods=['POST'])
def search():
    """Search full text and return matches with chapter information."""
    try:
        if not request.json:
            return jsonify({'error': 'No JSON data provided', 'results': [], 'total': 0}), 400
        
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'results': [], 'total': 0})
        
        # Ensure chapters are loaded
        if not CHAPTERS:
            parse_markdown_chapters()
        
        if not CHAPTERS:
            return jsonify({'error': 'No chapters loaded', 'results': [], 'total': 0}), 500
        
        results = []
        import re
        
        # Search through all chapters
        for chapter_idx, chapter in enumerate(CHAPTERS):
            chapter_num = chapter_idx + 1
            content = chapter.get('content', '')
            
            if not content:
                continue
            
            # Case-insensitive search
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            matches = list(pattern.finditer(content))
            
            for match in matches:
                start_pos = match.start()
                end_pos = match.end()
                
                # Get context around the match (100 chars before and after)
                context_start = max(0, start_pos - 100)
                context_end = min(len(content), end_pos + 100)
                context = content[context_start:context_end]
                
                # Find the line number for scrolling
                lines_before = content[:start_pos].count('\n')
                
                results.append({
                    'chapter_num': chapter_num,
                    'chapter_title': chapter.get('title', f'Chapter {chapter_num}'),
                    'chapter_slug': chapter.get('slug', f'chapter-{chapter_num}'),
                    'match_start': start_pos,
                    'match_end': end_pos,
                    'context': context,
                    'line_number': lines_before,
                    'match_text': match.group()
                })
        
        return jsonify({
            'results': results,
            'total': len(results),
            'query': query
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Search error: {error_trace}")
        return jsonify({
            'error': str(e),
            'results': [],
            'total': 0
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
