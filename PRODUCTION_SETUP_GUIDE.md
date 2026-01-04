# Production Server Setup Guide (Option 2: OpenAI Embeddings)

## Overview

**Option 2 uses FAISS for retrieval** - even though embeddings come from OpenAI API, FAISS is still needed on your production server to search the pre-built index.

## What You Can Build Locally (Mac Mini)

You can build the FAISS index on your Mac Mini and upload it:

```bash
# On your Mac Mini
python build_faiss_openai.py Anti-Oedipus.md
```

This creates:
- `faiss_index.bin` - The FAISS vector index (can upload to production)
- `chunks.json` - Text chunks and metadata (can upload to production)

**Cost**: ~$0.01-0.02 one-time (OpenAI API calls)

## What You MUST Install on Production Server

Even though you build the index locally, you still need these on production:

### Required Python Packages:
```bash
pip install faiss-cpu numpy openai
```

**Why FAISS is needed:**
- `search_faiss.py` uses FAISS to search the pre-built index
- `search_hybrid_openai.py` uses FAISS to search the pre-built index
- FAISS performs the fast vector similarity search (milliseconds)

**What you DON'T need:**
- ❌ PyTorch (not needed)
- ❌ sentence-transformers (not needed)
- ❌ torch (not needed)

### Required Python Scripts (upload these):
- `embed_query_openai.py` - Converts queries to embeddings via OpenAI API
- `search_faiss.py` - Searches FAISS index (uses FAISS library)
- `search_hybrid_openai.py` - Hybrid search (uses FAISS + OpenAI)

## Complete Setup Process

### Step 1: Build Index Locally (Mac Mini)

```bash
# On your Mac Mini
cd /path/to/anti-oedipus
python3 -m venv venv
source venv/bin/activate
pip install openai numpy faiss-cpu
export OPENAI_API_KEY="sk-your-key-here"
python build_faiss_openai.py Anti-Oedipus.md
```

This creates:
- `faiss_index.bin` (~2-3 MB)
- `chunks.json` (~1-2 MB)

### Step 2: Install Dependencies on Production Server

```bash
# On your FreeBSD production server
cd /home/public
python3 -m venv venv
source venv/bin/activate
pip install faiss-cpu numpy openai
```

**Note**: If `faiss-cpu` fails to install, see FREEBSD_SETUP.md for alternatives.

### Step 3: Upload Files to Production

Upload these files to your production server:
- ✅ `faiss_index.bin` (built locally)
- ✅ `chunks.json` (built locally)
- ✅ `embed_query_openai.py`
- ✅ `search_faiss.py`
- ✅ `search_hybrid_openai.py`
- ✅ `config.php` (updated with correct paths)
- ✅ All other PHP files

### Step 4: Update config.php

```php
$config = [
    'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',
    'EMBED_SCRIPT' => __DIR__ . '/embed_query_openai.py',
    'SEARCH_SCRIPT' => __DIR__ . '/search_faiss.py',
    'HYBRID_SCRIPT' => __DIR__ . '/search_hybrid_openai.py',
    'FAISS_INDEX' => __DIR__ . '/faiss_index.bin',
    'CHUNKS_JSON' => __DIR__ . '/chunks.json',
    'OPENAI_API_KEY' => 'sk-your-key-here',
    // ... other config
];
```

### Step 5: Set Permissions

```bash
chmod 755 embed_query_openai.py search_faiss.py search_hybrid_openai.py
chmod 644 faiss_index.bin chunks.json
```

### Step 6: Test

```bash
php test_rag.php "test query"
```

## How It Works

1. **User queries** → PHP calls `embed_query_openai.py`
   - Converts query to embedding via OpenAI API (~$0.0001 per query)

2. **Search** → PHP calls `search_faiss.py` or `search_hybrid_openai.py`
   - Uses FAISS to search the pre-built index (fast, local)
   - Returns chunk IDs

3. **Retrieve text** → PHP reads `chunks.json`
   - Uses chunk IDs to get actual text chunks
   - Sends to LLM with context

## Summary

| Component | Build Locally? | Needed on Production? |
|-----------|---------------|---------------------|
| `faiss_index.bin` | ✅ Yes | ✅ Upload to production |
| `chunks.json` | ✅ Yes | ✅ Upload to production |
| FAISS library | ✅ Install locally | ✅ Install on production |
| NumPy | ✅ Install locally | ✅ Install on production |
| OpenAI library | ✅ Install locally | ✅ Install on production |
| PyTorch | ❌ Not needed | ❌ Not needed |
| sentence-transformers | ❌ Not needed | ❌ Not needed |

## Troubleshooting

### FAISS Installation Fails on FreeBSD

If `pip install faiss-cpu` fails:
1. Try: `pip install faiss-cpu==1.7.4 --no-build-isolation`
2. Or ask hosting provider: `pkg install py311-faiss` (if available)
3. Or use alternative: See FREEBSD_SETUP.md for `annoy` option

### Index Not Found

Make sure `faiss_index.bin` and `chunks.json` are in the same directory as `config.php`.

### Embedding Dimension Mismatch

If you rebuild the index, make sure to use the same embedding model:
- `build_faiss_openai.py` uses `text-embedding-3-small` (1536 dims)
- `embed_query_openai.py` uses `text-embedding-3-small` (1536 dims)

They must match!

