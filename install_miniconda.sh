#!/bin/bash
# Install Miniconda without sudo (for shared hosting)

set -e

echo "================================================"
echo "Installing Miniconda (no sudo required)"
echo "================================================"

cd ~

echo "Downloading Miniconda..."
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh

echo ""
echo "Installing Miniconda to ~/miniconda3..."
bash miniconda.sh -b -p ~/miniconda3

echo ""
echo "Initializing conda..."
~/miniconda3/bin/conda init bash

echo ""
echo "================================================"
echo "✅ Miniconda installed!"
echo ""
echo "Next steps:"
echo "1. Reload your shell: source ~/.bashrc"
echo "2. Create environment: conda create -n anti-oedipus python=3.11 -y"
echo "3. Activate: conda activate anti-oedipus"
echo "4. Install packages: conda install -c conda-forge numpy=1.26.4 faiss-cpu -y"
echo "5. Install others: pip install torch sentence-transformers"
echo ""
echo "Or run: bash install_without_sudo.sh"

