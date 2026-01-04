# Production Server Setup Guide

This guide covers setting up the refactored RAG system on your production VPS server.

## Overview

The system uses:
- **Local embeddings** (sentence-transformers, no API calls)
- **FAISS** for fast vector similarity search
- **JSON storage** for text chunks (easy to inspect/debug)
- **PHP orchestration** via small Python helper scripts

## Architecture

1. **Build Process** (run when markdown changes):
   - `build_faiss_local.py` splits markdown into ~800 char chunks
   - Generates 384-dim embeddings using local model
   - Saves FAISS index (`faiss_index.bin`) and chunks (`chunks.json`)

2. **Query Process** (per user request):
   - PHP calls `embed_query.py` to convert query to vector
   - PHP calls `search_faiss.py` to find similar chunks (returns indices)
   - PHP loads `chunks.json` and retrieves text by indices
   - PHP sends context + query to LLM

## Step 1: Install Python Dependencies

```bash
cd /path/to/your/project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Note**: The first time you install `sentence-transformers`, it will download the model (~90 MB). This is cached for future use.

## Step 2: Build FAISS Index

```bash
# Activate venv if not already active
source venv/bin/activate

# Build index (takes ~10-15 seconds)
python build_faiss_local.py Anti-Oedipus.md
```

This creates:
- `faiss_index.bin` (~2.3 MB)
- `chunks.json` (~1.3 MB)

## Step 3: Configure PHP

Update `config.php`:

```php
$config = [
    'PYTHON_PATH' => __DIR__ . '/venv/bin/python3', // Adjust path as needed
    'EMBED_SCRIPT' => __DIR__ . '/embed_query.py',
    'SEARCH_SCRIPT' => __DIR__ . '/search_faiss.py',
    'FAISS_INDEX' => __DIR__ . '/faiss_index.bin',
    'CHUNKS_JSON' => __DIR__ . '/chunks.json',
    // ... other config
];
```

## Step 4: Set File Permissions

```bash
# Make Python scripts executable
chmod 755 build_faiss_local.py embed_query.py search_faiss.py

# Ensure PHP can read index files
chmod 644 faiss_index.bin chunks.json
```

## Step 5: Test the System

Test embedding a query:
```bash
python embed_query.py "test query"
```

Test searching:
```bash
QUERY_VEC=$(python embed_query.py "test query")
python search_faiss.py faiss_index.bin "$QUERY_VEC" 5
```

## File Sizes

For a ~300KB markdown file:
- `faiss_index.bin`: ~2.3 MB
- `chunks.json`: ~1.3 MB
- Total: ~3.6 MB

## Performance

- **Index build**: ~10-15 seconds (one-time)
- **Query embedding**: ~50-100ms (local model)
- **FAISS search**: <10ms (very fast)
- **Total query time**: ~100-150ms

## Updating the Index

When `Anti-Oedipus.md` changes:

```bash
source venv/bin/activate
python build_faiss_local.py Anti-Oedipus.md
```

The old files will be overwritten.

## Troubleshooting

### Model Download Issues

If the model fails to download, it will be cached in `~/.cache/huggingface/`. You can also download it manually or use a different model:

```bash
python build_faiss_local.py Anti-Oedipus.md all-mpnet-base-v2
```

### Permission Errors

Ensure PHP can execute Python scripts:
```bash
chmod 755 embed_query.py search_faiss.py
```

### Index Not Found

Check that `faiss_index.bin` and `chunks.json` exist:
```bash
ls -lh faiss_index.bin chunks.json
```

### Slow Queries

First query may be slower as the model loads. Subsequent queries are fast. Consider keeping a Python process warm or using a process manager.

## Advantages of This System

1. **No API costs** for embeddings (uses local model)
2. **Fast queries** (FAISS search is milliseconds)
3. **Easy debugging** (chunks.json is human-readable)
4. **Production-ready** (no external API dependencies for search)
5. **Scalable** (can handle larger documents efficiently)

