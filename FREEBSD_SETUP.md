# FreeBSD Setup Guide (No PyTorch Available)

If you're on FreeBSD and PyTorch isn't available, you have two options:

## Option 1: Ask Hosting Provider to Install PyTorch (Recommended)

Ask your hosting provider to install PyTorch via FreeBSD's package manager:

```bash
pkg install py311-pytorch
```

Then install Python packages normally:

```bash
pip install sentence-transformers faiss-cpu
```

## Option 2: Use OpenAI Embeddings Instead (Fallback)

If PyTorch cannot be installed, you can use OpenAI's embeddings API instead of local embeddings.

### Step 1: Install Dependencies (No PyTorch Required)

```bash
cd /home/public
source venv/bin/activate
pip install openai numpy faiss-cpu
```

**Note**: FAISS may still fail if it needs to build from source. If so, see Option 3.

### Step 2: Build Index Using OpenAI Embeddings

Build the FAISS index using OpenAI embeddings:

```bash
# Make sure OPENAI_API_KEY is set
export OPENAI_API_KEY="sk-your-key-here"

# Or pass it as argument:
python build_faiss_openai.py Anti-Oedipus.md "sk-your-key-here"
```

This will create:
- `faiss_index.bin` (using OpenAI embeddings, 1536 dimensions)
- `chunks.json` (same format)

**Note**: This will make API calls to OpenAI (~$0.01-0.02 for a 300KB document, one-time cost).

### Step 3: Update config.php

Update your `config.php` to use OpenAI embedding scripts:

```php
'EMBED_SCRIPT' => __DIR__ . '/embed_query_openai.py',
'HYBRID_SCRIPT' => __DIR__ . '/search_hybrid_openai.py',  // Optional: for hybrid search
```

### Step 4: Set OpenAI API Key

Make sure `OPENAI_API_KEY` is set in your `config.php`:

```php
'OPENAI_API_KEY' => 'sk-your-key-here',
```

Or set it as an environment variable that PHP can access.

## Option 3: Use Alternative Library (If FAISS Also Fails)

If both PyTorch and FAISS fail, use `annoy` (pure Python):

```bash
pip install annoy numpy openai
```

Then modify the search scripts to use Annoy instead of FAISS.

## Cost Considerations

Using OpenAI embeddings means:
- **Index building**: ~$0.0001 per 1K tokens (one-time cost when building index)
- **Query embedding**: ~$0.0001 per query (very small cost per search)

For a 300KB document:
- Building index: ~$0.01-0.02 (one-time)
- Per query: ~$0.0001 (negligible)

## Recommendation

**Best**: Ask hosting provider to install PyTorch (Option 1)
**Fallback**: Use OpenAI embeddings (Option 2)
**Last resort**: Use Annoy (Option 3)

