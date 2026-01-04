# Installing FAISS on Production Server

If you encounter BLAS/LAPACK errors when installing `faiss-cpu`, try these solutions:

## Solution 1: Install Pre-built Wheel (Easiest)

Try installing from a pre-built wheel instead of building from source:

```bash
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install numpy==1.26.4  # Use compatible numpy version
pip install faiss-cpu --no-build-isolation
```

## Solution 2: Install System BLAS Libraries

On Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install libopenblas-dev liblapack-dev
```

Then retry:
```bash
pip install faiss-cpu
```

## Solution 3: Use Compatible NumPy Version

The error shows NumPy 2.4.0 has BLAS issues. Try downgrading:

```bash
source venv/bin/activate
pip install numpy==1.26.4
pip install faiss-cpu
```

## Solution 4: Install All Dependencies Separately

Install in this order:

```bash
source venv/bin/activate
pip install --upgrade pip
pip install numpy==1.26.4
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers
pip install faiss-cpu --no-build-isolation
```

## Solution 5: Use Conda (If Available)

If conda is available on your server:

```bash
conda create -n anti-oedipus python=3.11
conda activate anti-oedipus
conda install -c conda-forge faiss-cpu
pip install sentence-transformers torch
```

## Verify Installation

After installation, verify:

```bash
python3 -c "import faiss; import sentence_transformers; print('✅ All modules installed!')"
```

## Troubleshooting

If you still get errors:

1. **Check Python version**: `python3 --version` (should be 3.9-3.11)
2. **Check pip version**: `pip --version` (should be latest)
3. **Upgrade pip**: `pip install --upgrade pip`
4. **Clear pip cache**: `pip cache purge`
5. **Try without cache**: `pip install --no-cache-dir faiss-cpu`

## Alternative: Use CPU-Only Build

If faiss-cpu still fails, you can try installing the CPU-only version explicitly:

```bash
pip install faiss-cpu==1.7.4 --no-build-isolation
```

This older version may have better compatibility.

