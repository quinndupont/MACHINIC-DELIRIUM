# PHP Deployment Guide for NearlyFreeSpeech

This guide covers deploying the Anti-Oedipus reader application to NearlyFreeSpeech using PHP instead of Flask.

## Prerequisites

- NearlyFreeSpeech account with SSH access
- PHP 7.4+ (usually available by default)
- Python 3.x (optional, for RAG - check with `which python3`)

## Step 1: Check Python Availability (Optional)

SSH into your server and check if Python is available:

```bash
which python3
python3 --version
```

If Python is available, you can use the full RAG system. If not, the app will fall back to simple text search.

## Step 2: Upload Files

Upload all project files to your NearlyFreeSpeech server, including:
- `index.php` (main entry point)
- `login.php` (login page)
- `config.php` (configuration - see Step 3)
- `php_utils.php` (utility functions)
- `build_faiss_local.py` (Script to build FAISS index with local embeddings)
- `embed_query.py` (Script to convert query to embedding vector)
- `search_faiss.py` (Script to search FAISS index)
- `faiss_index.bin` (Precomputed FAISS index - build with build_faiss_local.py)
- `chunks.json` (Text chunks and metadata - build with build_faiss_local.py)
- `templates/` directory
- `static/` directory
- `Anti-Oedipus.md` (markdown file)
- `requirements.txt` (for Python dependencies, if using Python)

**Exclude:**
- `.env` file (create `config.php` instead)
- `venv/` directory (create on server if using Python)
- `__pycache__/` directories
- Old RAG files (no longer needed): `rag.py`, `rag_api.py`, `faiss_api.py`, `embeddings_cache.pkl`, `faiss_metadata.pkl`

**Note**: You can either upload `faiss_index.bin` and `chunks.json` after building them locally, or build them on the server using `build_faiss_local.py`.

## Step 3: Configure

### Option A: Using config.php (Recommended)

Edit `config.php` and set your values:

```php
$config = [
    'OPENAI_API_KEY' => 'sk-your-server-api-key-here',
    'APP_PASSWORD' => 'your-secure-password-here',
    'FLASK_SECRET_KEY' => 'generate-a-random-secret-key-here',
    'MARKDOWN_FILE' => __DIR__ . '/Anti-Oedipus.md',
    'PYTHON_PATH' => '/usr/local/bin/python', // Update after checking with 'which python' or 'which python3'
    'EMBED_SCRIPT' => __DIR__ . '/embed_query.py', // Convert query to vector
    'SEARCH_SCRIPT' => __DIR__ . '/search_faiss.py', // Search FAISS index
    'HYBRID_SCRIPT' => __DIR__ . '/search_hybrid.py', // Hybrid semantic + keyword search
    'FAISS_INDEX' => __DIR__ . '/faiss_index.bin',
    'CHUNKS_JSON' => __DIR__ . '/chunks.json' // Text chunks and metadata
];
```

Generate a secret key:
```bash
php -r "echo bin2hex(random_bytes(32));"
```

### Option B: Using Environment Variables

If NearlyFreeSpeech supports `.htaccess` environment variables, you can set them there instead.

## Step 4: Set File Permissions

```bash
# Make PHP files readable
chmod 644 *.php

# Make Python scripts executable (if using Python)
chmod 755 build_faiss_local.py embed_query.py search_faiss.py

# Restrict config.php permissions
chmod 600 config.php
```

## Step 5: Install Python Dependencies and Build FAISS Index (If Using Python)

If Python is available and you want to use RAG:

```bash
cd /path/to/your/project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then update `config.php` to use the venv Python:
```php
'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',
```

**Important**: Make sure the venv has all required packages installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

Verify the installation:
```bash
python3 -c "import faiss, sentence_transformers; print('All modules installed!')"
```

### Build FAISS Index

**Important**: You must build the FAISS index before the RAG system will work:

```bash
# Activate venv if not already active
source venv/bin/activate

# Build FAISS index using local embeddings (no API key needed)
python build_faiss_local.py Anti-Oedipus.md
```

This creates:
- `faiss_index.bin`: Precomputed FAISS vector index (binary file, ~2.3 MB)
- `chunks.json`: Text chunks and metadata (JSON file, ~1.3 MB)

**Note**: 
- This step only needs to be run once (or when the markdown file changes)
- Uses local embedding model (no API calls needed)
- Takes about 10-15 seconds to build
- Creates ~1500 overlapping chunks of ~800 characters each

## Step 6: Apache Configuration

NearlyFreeSpeech typically uses `.htaccess` files. Create or update `.htaccess` in your project root:

```apache
# Enable PHP
AddHandler application/x-httpd-php .php

# Set default file
DirectoryIndex index.php index.html

# Security: Protect config.php
<Files "config.php">
    Require all denied
</Files>

# Optional: Set environment variables (if supported)
# SetEnv OPENAI_API_KEY "your-key-here"
# SetEnv APP_PASSWORD "your-password-here"
```

## Step 7: Test

1. Visit your domain: `https://your-domain.com/login.php`
2. Try logging in with your password or API key
3. Test the main reading interface
4. Test the chat/define features

## Troubleshooting

### Python Not Found

If Python is not available, the app will automatically fall back to simple text search. This works but won't have semantic search capabilities.

### Permission Denied

Make sure PHP files are readable (644) and directories are executable (755):
```bash
find . -type f -name "*.php" -exec chmod 644 {} \;
find . -type d -exec chmod 755 {} \;
```

### Session Issues

Check that PHP sessions directory is writable:
```bash
php -i | grep session.save_path
```

If needed, create a sessions directory and update `php.ini` or use `.htaccess`:
```apache
php_value session.save_path "/path/to/your/project/sessions"
```

### RAG Script Not Working

1. **Check FAISS index files exist**:
   ```bash
   ls -lh faiss_index.bin chunks.json
   ```
   If missing, build the index (see Step 5).

2. **Test embedding script**:
   ```bash
   python3 embed_query.py "test query"
   ```
   Should output a JSON array of 384 numbers.

3. **Test search script**:
   ```bash
   QUERY_VEC=$(python3 embed_query.py "test query")
   python3 search_faiss.py faiss_index.bin "$QUERY_VEC" 5
   ```
   Should output JSON with indices and similarities.

4. Check file permissions on scripts (should be 755):
   ```bash
   chmod 755 embed_query.py search_faiss.py
   ```

5. Check that FAISS index files are readable:
   ```bash
   chmod 644 faiss_index.bin chunks.json
   ```

6. Check PHP error logs for shell_exec errors

7. Verify dependencies are installed:
   ```bash
   python3 -c "import faiss; import sentence_transformers; print('Dependencies OK')"
   ```

## Differences from Flask Version

- **Sessions**: Uses PHP sessions instead of Flask sessions
- **Templates**: PHP includes instead of Jinja2 (you may need to update templates)
- **RAG**: Optional - falls back to simple search if Python unavailable
- **Markdown**: Basic markdown parsing (consider using Parsedown library for better support)

## Optional Improvements

### Use Parsedown for Better Markdown

Install via Composer:
```bash
composer require erusev/parsedown
```

Then update `markdown_to_html()` in `php_utils.php`:
```php
require_once __DIR__ . '/vendor/autoload.php';
use Parsedown;

function markdown_to_html($markdown) {
    $parsedown = new Parsedown();
    return $parsedown->text($markdown);
}
```

### Use Composer for Dependencies

Create `composer.json`:
```json
{
    "require": {
        "erusev/parsedown": "^1.7"
    }
}
```

Then run: `composer install`

