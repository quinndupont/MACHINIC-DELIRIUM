# Installing FAISS on Production Server

If you encounter BLAS/LAPACK errors when installing `faiss-cpu`, try these solutions:

## ⚠️ CRITICAL: Fix Broken NumPy First

If you see `Undefined symbol "cblas_sdot"` errors, your NumPy installation is broken. **Fix this first:**

### Step 1: Completely Remove Broken NumPy

```bash
source venv/bin/activate
pip uninstall numpy -y
rm -rf venv/lib/python3.11/site-packages/numpy*
pip cache purge
```

### Step 2: Install System BLAS Libraries (Recommended)

On Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install libopenblas-dev liblapack-dev libatlas-base-dev gfortran
```

On CentOS/RHEL:
```bash
sudo yum install openblas-devel lapack-devel atlas-devel gcc-gfortran
```

### Step 3: Reinstall NumPy with Pre-built Wheel

```bash
pip install --upgrade pip setuptools wheel
pip install --no-cache-dir numpy==1.26.4
python3 -c "import numpy; print('✅ NumPy works:', numpy.__version__)"
```

If NumPy still fails, try:
```bash
pip install --no-cache-dir --only-binary :all: numpy==1.26.4
```

### Step 4: Install FAISS

```bash
pip install faiss-cpu --no-build-isolation
```

## Solution 1: Complete Fresh Install (Recommended)

If NumPy is completely broken, start fresh:

```bash
cd /home/public
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install system libraries first (if you have sudo)
# sudo apt-get install libopenblas-dev liblapack-dev

# Install NumPy with pre-built wheel
pip install --only-binary :all: numpy==1.26.4

# Verify NumPy works
python3 -c "import numpy; print('NumPy version:', numpy.__version__)"

# Install other dependencies
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers
pip install faiss-cpu --no-build-isolation
```

## Solution 2: Use Pre-built FAISS Wheel (If Available)

Try installing from a pre-built wheel:

```bash
pip install --only-binary :all: faiss-cpu
```

## Solution 3: Install Older FAISS Version

Older versions may have better compatibility:

```bash
pip install faiss-cpu==1.7.4 --no-build-isolation
```

## Solution 4: Use Conda (If Available)

Conda handles BLAS dependencies better:

```bash
conda create -n anti-oedipus python=3.11
conda activate anti-oedipus
conda install -c conda-forge numpy=1.26.4 faiss-cpu
pip install sentence-transformers torch
```

## Solution 5: Alternative - Use faiss-cpu from conda-forge via pip

```bash
pip install --index-url https://pypi.anaconda.org/conda-forge/simple faiss-cpu
```

## Verify Installation

After installation, verify:

```bash
python3 -c "import numpy; print('NumPy:', numpy.__version__)"
python3 -c "import faiss; print('FAISS:', faiss.__version__)"
python3 -c "import sentence_transformers; print('✅ All modules installed!')"
```

## Troubleshooting

If you still get errors:

1. **Check if NumPy works**: `python3 -c "import numpy"` (must work first!)
2. **Check Python version**: `python3 --version` (should be 3.9-3.11)
3. **Check pip version**: `pip --version` (should be latest)
4. **Clear pip cache**: `pip cache purge`
5. **Try without cache**: `pip install --no-cache-dir <package>`
6. **Check system libraries**: `ldconfig -p | grep blas` (should show BLAS libraries)

## If Nothing Works: Use Alternative Embedding Library

If FAISS installation continues to fail, you can temporarily use a pure-Python alternative:

```bash
pip install annoy  # Pure Python, no BLAS required
```

Then modify `search_faiss.py` to use Annoy instead (though this is less optimal).

