#!/bin/bash
# Installation script for servers WITHOUT sudo access
# Uses conda or alternative methods

set -e

echo "================================================"
echo "Installing FAISS without sudo access"
echo "================================================"

cd /home/public

# Method 1: Try using conda/miniconda (if available)
if command -v conda &> /dev/null; then
    echo "✅ Conda found! Using conda (best option without sudo)..."
    
    # Create or activate conda environment
    if conda env list | grep -q "anti-oedipus"; then
        echo "Activating existing conda environment..."
        conda activate anti-oedipus
    else
        echo "Creating conda environment..."
        conda create -n anti-oedipus python=3.11 -y
        conda activate anti-oedipus
    fi
    
    echo "Installing NumPy and FAISS via conda..."
    conda install -c conda-forge numpy=1.26.4 faiss-cpu -y
    
    echo "Installing other dependencies via pip..."
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install sentence-transformers
    
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
    echo "✅ Installation complete via conda!"
    echo "Update config.php: 'PYTHON_PATH' => '$(which python3)',"
    exit 0
fi

# Method 2: Try installing from conda-forge via pip
echo ""
echo "Conda not found. Trying conda-forge via pip..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "Removing broken NumPy..."
pip uninstall numpy -y 2>/dev/null || true
rm -rf venv/lib/python3.11/site-packages/numpy* 2>/dev/null || true
pip cache purge

echo "Trying to install NumPy from conda-forge..."
# Try conda-forge index
if pip install --index-url https://pypi.anaconda.org/conda-forge/simple --no-cache-dir numpy==1.26.4 2>/dev/null; then
    echo "✅ Installed NumPy from conda-forge"
elif pip install --no-cache-dir "numpy<2.0.0" 2>/dev/null; then
    echo "✅ Installed compatible NumPy version"
else
    echo ""
    echo "❌ Cannot install NumPy without system libraries!"
    echo ""
    echo "Options:"
    echo "1. Install miniconda (no sudo needed):"
    echo "   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    echo "   bash Miniconda3-latest-Linux-x86_64.sh -b -p ~/miniconda3"
    echo "   ~/miniconda3/bin/conda init"
    echo "   source ~/.bashrc"
    echo "   Then run this script again."
    echo ""
    echo "2. Ask your hosting provider to install BLAS libraries"
    echo ""
    echo "3. Use alternative embedding library (see INSTALL_FAISS.md)"
    exit 1
fi

echo "Verifying NumPy..."
if ! python3 -c "import numpy; print('✅ NumPy:', numpy.__version__)" 2>/dev/null; then
    echo ""
    echo "❌ NumPy installation failed!"
    echo "You need conda or system BLAS libraries."
    exit 1
fi

echo ""
echo "Installing torch..."
pip install torch --index-url https://download.pytorch.org/whl/cpu

echo ""
echo "Installing sentence-transformers..."
pip install sentence-transformers

echo ""
echo "Installing FAISS from conda-forge..."
if pip install --index-url https://pypi.anaconda.org/conda-forge/simple faiss-cpu --no-build-isolation 2>/dev/null; then
    echo "✅ Installed FAISS from conda-forge"
elif pip install faiss-cpu==1.7.4 --no-build-isolation 2>/dev/null; then
    echo "✅ Installed older FAISS version"
else
    echo ""
    echo "❌ FAISS installation failed!"
    echo "Try installing miniconda (see instructions above)."
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

