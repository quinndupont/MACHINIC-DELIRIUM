#!/bin/bash
# Installation script for FreeBSD servers WITHOUT sudo access
# FreeBSD-specific approach

set -e

echo "================================================"
echo "Installing FAISS on FreeBSD (no sudo)"
echo "================================================"

cd /home/public

# Check if we're on FreeBSD
if [ "$(uname)" != "FreeBSD" ]; then
    echo "This script is for FreeBSD. Detected: $(uname)"
    exit 1
fi

echo "Detected FreeBSD system"
echo "Python version: $(python3 --version 2>&1 || echo 'Not found')"

# Method 1: Try using system Python with pip
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "Removing broken NumPy..."
pip uninstall numpy -y 2>/dev/null || true
rm -rf venv/lib/python3.*/site-packages/numpy* 2>/dev/null || true
pip cache purge

echo ""
echo "Installing NumPy (FreeBSD-compatible)..."
# Try installing NumPy - FreeBSD may have pre-built wheels
if pip install --no-cache-dir numpy==1.26.4; then
    echo "✅ Installed NumPy"
elif pip install --no-cache-dir "numpy<2.0.0"; then
    echo "✅ Installed compatible NumPy version"
else
    echo "❌ Cannot install NumPy"
    exit 1
fi

echo ""
echo "Verifying NumPy..."
NUMPY_ERROR=$(python3 -c "import numpy; print('✅ NumPy:', numpy.__version__)" 2>&1)
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ NumPy cannot be imported!"
    echo ""
    echo "Error:"
    echo "$NUMPY_ERROR" | head -10
    echo ""
    echo "FreeBSD-specific solutions:"
    echo ""
    echo "Option 1: Ask your hosting provider to install:"
    echo "  pkg install py311-numpy py311-scipy openblas"
    echo ""
    echo "Option 2: Try installing from FreeBSD ports (if available):"
    echo "  This requires sudo access"
    echo ""
    echo "Option 3: Use a different approach - build NumPy with OpenBLAS from source"
    echo "  This is complex and may not work without system libraries"
    echo ""
    echo "Option 4: Contact your hosting provider about BLAS/LAPACK libraries"
    exit 1
else
    echo "$NUMPY_ERROR"
fi

echo ""
echo "Installing torch (trying regular PyPI first)..."
# Try regular PyPI - may have FreeBSD wheels or will attempt to build
if pip install torch; then
    echo "✅ Installed torch from PyPI"
elif pip install --no-cache-dir torch; then
    echo "✅ Installed torch (built from source)"
else
    echo ""
    echo "⚠️  Warning: Could not install torch"
    echo "PyTorch doesn't have FreeBSD wheels. Trying to install sentence-transformers anyway..."
    echo "sentence-transformers may pull torch as a dependency or fail."
fi

echo ""
echo "Installing sentence-transformers..."
# sentence-transformers will try to install torch as a dependency if not present
if pip install sentence-transformers; then
    echo "✅ Installed sentence-transformers"
else
    echo ""
    echo "❌ Cannot install sentence-transformers!"
    echo ""
    echo "sentence-transformers requires PyTorch, which doesn't have FreeBSD wheels."
    echo ""
    echo "SOLUTIONS:"
    echo ""
    echo "Option 1 (Recommended): Ask your hosting provider to install PyTorch:"
    echo "   pkg install py311-pytorch"
    echo "   Then run: pip install sentence-transformers"
    echo ""
    echo "Option 2: Use OpenAI embeddings instead (see FREEBSD_SETUP.md)"
    echo "   pip install openai"
    echo "   Use embed_query_openai.py (already included)"
    echo ""
    echo "Option 3: Use alternative library 'annoy' (pure Python, no BLAS)"
    echo "   pip install annoy"
    echo "   Requires code modifications"
    echo ""
    echo "See FREEBSD_SETUP.md for detailed instructions."
    exit 1
fi

echo ""
echo "Installing FAISS..."
# Try multiple FAISS installation methods
if pip install faiss-cpu --no-build-isolation; then
    echo "✅ Installed FAISS"
elif pip install faiss-cpu==1.7.4 --no-build-isolation; then
    echo "✅ Installed older FAISS version"
else
    echo ""
    echo "❌ FAISS installation failed!"
    echo ""
    echo "FAISS may not have pre-built wheels for FreeBSD."
    echo "You may need to:"
    echo "1. Ask your hosting provider to install FAISS via pkg"
    echo "2. Use an alternative like 'annoy' (pure Python)"
    exit 1
fi

echo ""
echo "Verifying installation..."
python3 -c "
import numpy
import faiss
import sentence_transformers
print('✅ NumPy:', numpy.__version__)
print('✅ FAISS:', faiss.__version__)
print('✅ All modules installed!')
"

echo ""
echo "================================================"
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Build index: python3 build_pure_python.py Anti-Oedipus.md (recommended)"
echo "   OR if FAISS works: python3 build_faiss_openai.py Anti-Oedipus.md"
echo "2. Update config.php: 'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',"
echo "3. Test: php test_rag.php 'test query'"

