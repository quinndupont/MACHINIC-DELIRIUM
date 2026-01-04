# Pure Python RAG Setup (No FAISS/NumPy Required)

This is a **pure Python solution** that requires **NO external dependencies** except the OpenAI library. Perfect for FreeBSD servers where FAISS/NumPy won't install.

## What This Uses

- ✅ **OpenAI API** for embeddings (same as Option 2)
- ✅ **Pure Python cosine similarity** (no NumPy, no FAISS)
- ✅ **Standard library only** (math, json, re)
- ✅ **Fast enough** for ~1500 chunks (milliseconds)

## Setup Process

### Step 1: Build Index Locally (Mac Mini)

```bash
# On your Mac Mini
cd /path/to/anti-oedipus
python3 -m venv venv
source venv/bin/activate
pip install openai
export OPENAI_API_KEY="sk-your-key-here"
python build_pure_python.py Anti-Oedipus.md
```

This creates:
- `chunks.json` - Text chunks and metadata (~1-2 MB)
- `embeddings.json` - Embedding vectors (~5-10 MB)

**Cost**: ~$0.01-0.02 one-time (OpenAI API calls)

### Step 2: Install on Production Server

**Only one dependency needed:**

```bash
cd /home/public
python3 -m venv venv
source venv/bin/activate
pip install openai
```

That's it! No FAISS, no NumPy, no BLAS libraries.

### Step 3: Upload Files

Upload these files to production:
- ✅ `chunks.json` (built locally)
- ✅ `embeddings.json` (built locally)
- ✅ `embed_query_openai.py`
- ✅ `search_pure_python.py`
- ✅ `search_hybrid_pure_python.py` (optional, for hybrid search)
- ✅ Updated `config.php`

### Step 4: Update config.php

```php
$config = [
    'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',
    'EMBED_SCRIPT' => __DIR__ . '/embed_query_openai.py',
    // Use pure Python search (no FAISS needed)
    'SEARCH_PURE_PYTHON' => __DIR__ . '/search_pure_python.py',
    'HYBRID_PURE_PYTHON' => __DIR__ . '/search_hybrid_pure_python.py',
    'EMBEDDINGS_JSON' => __DIR__ . '/embeddings.json',
    'CHUNKS_JSON' => __DIR__ . '/chunks.json',
    'OPENAI_API_KEY' => 'sk-your-key-here',
    // ... other config
];
```

### Step 5: Set Permissions

```bash
chmod 755 embed_query_openai.py search_pure_python.py search_hybrid_pure_python.py
chmod 644 embeddings.json chunks.json
```

### Step 6: Test

```bash
php test_rag.php "test query"
```

## How It Works

1. **User queries** → PHP calls `embed_query_openai.py`
   - Converts query to embedding via OpenAI API (~$0.0001 per query)

2. **Search** → PHP calls `search_pure_python.py`
   - Loads embeddings from `embeddings.json`
   - Computes cosine similarity in pure Python (no NumPy)
   - Returns top k chunk indices

3. **Retrieve text** → PHP reads `chunks.json`
   - Uses chunk indices to get actual text chunks
   - Maps back to original document via metadata
   - Sends to LLM with context

## Performance

For ~1500 chunks:
- **Search time**: ~50-100ms (pure Python cosine similarity)
- **Memory**: ~10-15 MB (embeddings loaded in memory)
- **Accuracy**: Same as FAISS (uses same embeddings)

## Advantages

✅ **No BLAS libraries** needed
✅ **No NumPy** needed  
✅ **No FAISS** needed
✅ **Works on FreeBSD** without sudo
✅ **Same accuracy** as FAISS (same embeddings)
✅ **Fast enough** for production use

## Disadvantages

⚠️ **Slower than FAISS** (~50-100ms vs ~5-10ms)
⚠️ **Larger memory footprint** (embeddings in JSON vs binary)
⚠️ **Not optimized** for very large datasets (10k+ chunks)

For your use case (~1500 chunks), this is perfectly fine!

## Hybrid Search

For better results, use `search_hybrid_pure_python.py` which combines:
- Semantic search (pure Python cosine similarity)
- Keyword matching (exact phrase matching)
- Exact match boosting

Update config.php:
```php
'HYBRID_PURE_PYTHON' => __DIR__ . '/search_hybrid_pure_python.py',
```

Then PHP will automatically use hybrid search if available.

## Troubleshooting

### Embeddings file not found
Make sure `embeddings.json` is uploaded to production.

### Search is slow
For ~1500 chunks, ~50-100ms is normal. If you have 10k+ chunks, consider FAISS or a database solution.

### Memory issues
If you have very large embeddings.json, you might need to chunk it or use a database.

## Summary

This pure Python solution:
- ✅ Works without FAISS/NumPy
- ✅ Requires only OpenAI library
- ✅ Provides same functionality
- ✅ Fast enough for production
- ✅ Maps perfectly back to original document

Perfect for FreeBSD servers where FAISS won't install!

