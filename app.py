from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("ERROR: python-dotenv is not installed. Please run: pip install -r requirements.txt")
    raise
from rag import RAGSystem
from openai import OpenAI
import math
from markupsafe import Markup
import markdown

app = Flask(__name__)
# Use a strong secret key for production - should be set in environment
# For development, use a fixed key so sessions persist across restarts
dev_secret_key = "dev-secret-key-change-in-production"
app.secret_key = os.getenv("FLASK_SECRET_KEY", dev_secret_key)

# Configure session cookies for security
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to False for localhost development
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds

SERVER_API_KEY = os.getenv("OPENAI_API_KEY")
APP_PASSWORD = os.getenv("APP_PASSWORD")

# Debug: Log password status (don't log actual password)
if APP_PASSWORD:
    print(f"APP_PASSWORD loaded: {'*' * min(len(APP_PASSWORD), 10)} (length: {len(APP_PASSWORD)})")
else:
    print("WARNING: APP_PASSWORD not set in .env file")

# Initialize RAG System - use markdown file only
markdown_file = "Anti-Oedipus.md"
if not os.path.exists(markdown_file):
    raise FileNotFoundError(f"Markdown file {markdown_file} not found")

# RAG system will be initialized per-request with appropriate API key
rag_system_cache = {}
client_cache = {}

def get_api_key():
    """Get API key from session if available, otherwise use server API key."""
    api_key = session.get('user_api_key') or SERVER_API_KEY
    if not api_key:
        raise ValueError("No API key available. Please provide an API key at login.")
    return api_key

def get_rag_system():
    """Get or create RAG system instance for the current API key."""
    api_key = get_api_key()
    if api_key not in rag_system_cache:
        rag_system_cache[api_key] = RAGSystem(markdown_file, api_key)
    return rag_system_cache[api_key]

def get_openai_client():
    """Get or create OpenAI client for the current API key."""
    api_key = get_api_key()
    if api_key not in client_cache:
        client_cache[api_key] = OpenAI(api_key=api_key)
    return client_cache[api_key]

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
    # Skip login check for allowed routes
    if request.endpoint in allowed_routes:
        return None
    
    # Check if user is logged in
    if 'logged_in' not in session:
        print(f"Access denied - no session. Endpoint: {request.endpoint}, Session keys: {list(session.keys())}")
        return redirect(url_for('login'))
    else:
        print(f"Access granted - logged in. Endpoint: {request.endpoint}, Session: {dict(session)}")

def validate_openai_key(api_key):
    """Validate an OpenAI API key format and basic validity."""
    # Check format: OpenAI keys start with 'sk-' and are typically 51 characters
    if not api_key or not api_key.startswith('sk-'):
        return False
    if len(api_key) < 20 or len(api_key) > 100:
        return False
    
    # Optionally do a lightweight validation call
    # For better UX, we'll validate format only and let API calls fail gracefully
    # if the key is invalid
    try:
        test_client = OpenAI(api_key=api_key)
        # Make a minimal, fast API call to validate the key
        # Using a simple models list call with limit=1 for speed
        test_client.models.list(limit=1)
        return True
    except Exception as e:
        # If validation fails, still allow login but API calls will fail
        # This provides better UX - user can try the key
        print(f"API key validation warning: {e}")
        # Return True anyway - format is correct, let actual usage validate
        return True

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_value = request.form.get('password', '').strip()
        
        # Debug logging
        print(f"Login attempt - Input length: {len(input_value)}, APP_PASSWORD set: {bool(APP_PASSWORD)}")
        
        if not input_value:
            return render_template('login.html', error="Please enter a password or API key")
        
        # First, check if it's the server password from .env
        # Only check password if APP_PASSWORD is set and not empty
        if APP_PASSWORD:
            app_password_stripped = APP_PASSWORD.strip()
            if app_password_stripped:
                if input_value == app_password_stripped:
                    print("Password match! Logging in...")
                    # Set permanent BEFORE setting values - this is important!
                    session.permanent = True
                    session['logged_in'] = True
                    # Clear any user API key if using server password
                    if 'user_api_key' in session:
                        session.pop('user_api_key', None)
                    # Force session to be saved
                    session.modified = True
                    print(f"Session after login: {dict(session)}")
                    # Use redirect - Flask will automatically save session cookie
                    # The session cookie is set by Flask's session middleware after route handler returns
                    return redirect(url_for('index'))
                else:
                    print(f"Password mismatch - Input length: {len(input_value)}, Expected length: {len(app_password_stripped)}")
                    # Continue to check if it's an API key instead
        
        # If not the password, check if it's a valid OpenAI API key
        # OpenAI API keys start with 'sk-' and are typically 20+ characters
        if input_value.startswith('sk-') and len(input_value) >= 20:
            if validate_openai_key(input_value):
                session.permanent = True
                session['logged_in'] = True
                session['user_api_key'] = input_value
                session.modified = True
                response = make_response(redirect(url_for('index')))
                return response
            else:
                return render_template('login.html', error="Invalid OpenAI API Key")
        
        # Neither password nor valid API key format
        if APP_PASSWORD:
            return render_template('login.html', error="Invalid Password or API Key")
        else:
            return render_template('login.html', error="Invalid API Key. Please provide a valid OpenAI API key.")
    
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
    try:
        data = request.json
        term = data.get('term')
        context = data.get('context') # Surrounding text
        
        # Use RAG to retrieve relevant chunks for the term
        query_text = f"{term} {context}" if context else term
        rag_results = get_rag_system().query(query_text, k=6)
        
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

        response = get_openai_client().chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for better context handling
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return jsonify({"definition": response.choices[0].message.content})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to get definition: {str(e)}"}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message')
        history = data.get('history', [])
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Use RAG to retrieve relevant chunks
        rag_results = get_rag_system().query(message, k=8)
        
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
        
        response = get_openai_client().chat.completions.create(
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
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to process chat: {str(e)}"}), 500

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
