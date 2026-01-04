#!/bin/bash
# Installation script for production server
# Handles FAISS installation issues

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

echo "Installing numpy (compatible version)..."
pip install "numpy<2.0.0"

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
        echo "ERROR: FAISS installation failed. See INSTALL_FAISS.md for troubleshooting."
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
echo "1. Build FAISS index: python build_faiss_local.py Anti-Oedipus.md"
echo "2. Update config.php with: 'PYTHON_PATH' => __DIR__ . '/venv/bin/python3',"
echo "3. Test: php test_rag.php 'test query'"

