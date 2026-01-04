#!/bin/bash
# Installation script for production server
# Handles FAISS installation issues
# NOTE: If NumPy is broken, use fix_numpy_and_install.sh instead

set -e

echo "Installing Python dependencies for RAG system..."
echo "================================================"

# Activate venv if it exists, otherwise create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

echo "Checking NumPy..."
if ! python3 -c "import numpy" 2>/dev/null; then
    echo "NumPy not installed or broken. Installing..."
    pip install --no-cache-dir --only-binary :all: numpy==1.26.4 || pip install --no-cache-dir numpy==1.26.4
else
    echo "NumPy already installed, checking version..."
    python3 -c "import numpy; print('NumPy version:', numpy.__version__)"
fi

echo "Installing torch..."
pip install torch --index-url https://download.pytorch.org/whl/cpu

echo "Installing sentence-transformers..."
pip install sentence-transformers

echo "Installing FAISS (this may take a few minutes)..."
# Try multiple installation methods
if ! pip install faiss-cpu --no-build-isolation 2>&1 | tee /tmp/faiss_install.log; then
    echo "First attempt failed, trying alternative method..."
    echo "Installing faiss-cpu==1.7.4 (older, more compatible version)..."
    pip install faiss-cpu==1.7.4 --no-build-isolation || {
        echo ""
        echo "ERROR: FAISS installation failed!"
        echo ""
        echo "Your NumPy may be broken. Try running:"
        echo "  bash fix_numpy_and_install.sh"
        echo ""
        echo "Or see INSTALL_FAISS.md for troubleshooting."
        exit 1
    }
fi

echo "Installing other dependencies..."
pip install flask python-dotenv openai tiktoken markdown gunicorn

echo ""
echo "Verifying installation..."
python3 -c "import faiss; import sentence_transformers; import numpy; print('✅ All modules installed successfully!')" || {
    echo "ERROR: Verification failed. Some modules are missing."
    exit 1
}

echo ""
echo "================================================"
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Build index: python build_pure_python.py Anti-Oedipus.md (recommended)"
echo "   OR if FAISS works: python build_faiss_openai.py Anti-Oedipus.md"
echo "2. Update config.php with: 'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',"
echo "3. Test: php test_rag.php 'test query'"

