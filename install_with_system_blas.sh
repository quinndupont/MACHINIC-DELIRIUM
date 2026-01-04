#!/bin/bash
# Complete installation guide when pre-built wheels aren't available
# This requires system BLAS libraries to be installed first

set -e

echo "================================================"
echo "FAISS Installation Guide"
echo "================================================"
echo ""
echo "If pre-built wheels aren't available, you need to:"
echo ""
echo "1. Install system BLAS libraries (REQUIRED):"
echo ""
echo "   On Debian/Ubuntu:"
echo "   sudo apt-get update"
echo "   sudo apt-get install libopenblas-dev liblapack-dev libatlas-base-dev gfortran"
echo ""
echo "   On CentOS/RHEL:"
echo "   sudo yum install openblas-devel lapack-devel atlas-devel gcc-gfortran"
echo ""
echo "2. Then run these commands:"
echo ""
echo "   cd /home/public"
echo "   source venv/bin/activate"
echo "   pip install --upgrade pip setuptools wheel"
echo "   pip uninstall numpy -y"
echo "   rm -rf venv/lib/python3.11/site-packages/numpy*"
echo "   pip cache purge"
echo "   pip install --no-cache-dir numpy==1.26.4"
echo "   python3 -c 'import numpy; print(\"NumPy:\", numpy.__version__)'"
echo "   pip install torch --index-url https://download.pytorch.org/whl/cpu"
echo "   pip install sentence-transformers"
echo "   pip install faiss-cpu --no-build-isolation"
echo ""
echo "================================================"
echo ""
echo "Would you like me to attempt the installation now? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    cd /home/public
    
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    echo ""
    echo "Removing broken NumPy..."
    pip uninstall numpy -y 2>/dev/null || true
    rm -rf venv/lib/python3.11/site-packages/numpy* 2>/dev/null || true
    pip cache purge
    
    echo ""
    echo "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    echo ""
    echo "Installing NumPy (this will compile if no wheels available)..."
    pip install --no-cache-dir numpy==1.26.4 || pip install --no-cache-dir "numpy<2.0.0"
    
    echo ""
    echo "Verifying NumPy..."
    if ! python3 -c "import numpy; print('✅ NumPy:', numpy.__version__)"; then
        echo ""
        echo "❌ NumPy installation failed!"
        echo "You MUST install system BLAS libraries first (see instructions above)."
        exit 1
    fi
    
    echo ""
    echo "Installing torch..."
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    
    echo ""
    echo "Installing sentence-transformers..."
    pip install sentence-transformers
    
    echo ""
    echo "Installing FAISS..."
    pip install faiss-cpu --no-build-isolation || pip install faiss-cpu==1.7.4 --no-build-isolation
    
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
else
    echo "Installation cancelled. Follow the manual steps above."
fi

