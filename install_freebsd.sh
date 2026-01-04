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
echo "Installing torch..."
pip install torch --index-url https://download.pytorch.org/whl/cpu

echo ""
echo "Installing sentence-transformers..."
pip install sentence-transformers

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
echo "1. Build FAISS index: python3 build_faiss_local.py Anti-Oedipus.md"
echo "2. Update config.php: 'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',"
echo "3. Test: php test_rag.php 'test query'"

