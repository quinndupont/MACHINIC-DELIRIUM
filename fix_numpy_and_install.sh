#!/bin/bash
# Fix broken NumPy and install FAISS
# Run this on your production server

set -e

echo "================================================"
echo "Fixing broken NumPy and installing FAISS"
echo "================================================"

cd /home/public

# Activate venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo ""
echo "Step 1: Removing broken NumPy..."
pip uninstall numpy -y 2>/dev/null || true
rm -rf venv/lib/python3.11/site-packages/numpy* 2>/dev/null || true
pip cache purge

echo ""
echo "Step 2: Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo ""
echo "Step 3: Installing NumPy with pre-built wheel..."
if ! pip install --no-cache-dir --only-binary :all: numpy==1.26.4; then
    echo "Pre-built wheel failed, trying regular install..."
    pip install --no-cache-dir numpy==1.26.4
fi

echo ""
echo "Step 4: Verifying NumPy works..."
if ! python3 -c "import numpy; print('✅ NumPy version:', numpy.__version__)"; then
    echo ""
    echo "❌ ERROR: NumPy still broken!"
    echo ""
    echo "You need to install system BLAS libraries:"
    echo "  sudo apt-get install libopenblas-dev liblapack-dev libatlas-base-dev"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo ""
echo "Step 5: Installing torch..."
pip install torch --index-url https://download.pytorch.org/whl/cpu

echo ""
echo "Step 6: Installing sentence-transformers..."
pip install sentence-transformers

echo ""
echo "Step 7: Installing FAISS..."
if ! pip install faiss-cpu --no-build-isolation; then
    echo "Standard install failed, trying older version..."
    pip install faiss-cpu==1.7.4 --no-build-isolation || {
        echo ""
        echo "❌ ERROR: FAISS installation failed!"
        echo ""
        echo "Try installing system BLAS libraries:"
        echo "  sudo apt-get install libopenblas-dev liblapack-dev"
        echo ""
        echo "Or use conda if available on your system."
        exit 1
    }
fi

echo ""
echo "Step 8: Verifying all modules..."
python3 -c "
import numpy
import faiss
import sentence_transformers
print('✅ NumPy:', numpy.__version__)
print('✅ FAISS:', faiss.__version__)
print('✅ All modules installed successfully!')
"

echo ""
echo "================================================"
echo "✅ Installation complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Build FAISS index: python3 build_faiss_local.py Anti-Oedipus.md"
echo "2. Update config.php: 'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',"
echo "3. Test: php test_rag.php 'test query'"

