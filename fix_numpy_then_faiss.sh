#!/bin/bash
# Fix broken NumPy and install FAISS on FreeBSD
# Run this on your production server

set -e

echo "================================================"
echo "Fixing NumPy and Installing FAISS"
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
rm -rf venv/lib/python3.*/site-packages/numpy* 2>/dev/null || true
pip cache purge

echo ""
echo "Step 2: Installing compatible NumPy..."
# Try installing NumPy 1.x (more compatible)
if pip install --no-cache-dir numpy==1.26.4; then
    echo "✅ Installed NumPy 1.26.4"
elif pip install --no-cache-dir "numpy<2.0.0"; then
    echo "✅ Installed compatible NumPy version"
else
    echo ""
    echo "❌ Cannot install NumPy!"
    echo "You may need to ask your hosting provider to install BLAS libraries."
    exit 1
fi

echo ""
echo "Step 3: Verifying NumPy works..."
if ! python3 -c "import numpy; print('✅ NumPy:', numpy.__version__)"; then
    echo ""
    echo "❌ NumPy still broken!"
    echo "Ask your hosting provider to install: pkg install py311-numpy openblas"
    exit 1
fi

echo ""
echo "Step 4: Installing OpenAI library..."
pip install openai

echo ""
echo "Step 5: Installing FAISS..."
# Try multiple FAISS versions
if pip install faiss-cpu --no-build-isolation; then
    echo "✅ Installed FAISS"
elif pip install faiss-cpu==1.7.4 --no-build-isolation; then
    echo "✅ Installed older FAISS version"
else
    echo ""
    echo "❌ FAISS installation failed!"
    echo ""
    echo "Options:"
    echo "1. Ask hosting provider: pkg install py311-faiss"
    echo "2. Use alternative: pip install annoy (pure Python, no BLAS)"
    echo "   Then modify search scripts to use Annoy instead"
    exit 1
fi

echo ""
echo "Step 6: Verifying installation..."
python3 -c "
import numpy
import faiss
import openai
print('✅ NumPy:', numpy.__version__)
print('✅ FAISS:', faiss.__version__)
print('✅ OpenAI library installed')
print('✅ All required modules installed!')
"

echo ""
echo "================================================"
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Upload faiss_index.bin and chunks.json (built locally)"
echo "2. Upload embed_query_openai.py and search_faiss.py"
echo "3. Update config.php with correct paths"
echo "4. Test: php test_rag.php 'test query'"

