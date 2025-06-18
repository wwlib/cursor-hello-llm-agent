#!/bin/bash

# Quick Documentation Setup Script for LLM Agent Framework
# Run this script from the docs/ directory: ./setup.sh

echo "Setting up documentation for LLM Agent Framework..."

# Check if we're in the docs directory
if [[ ! -f "conf.py" ]] && [[ ! -f "Makefile" ]]; then
    echo "Note: This script should be run from the docs/ directory"
    echo "Current directory: $(pwd)"
fi

# 1. Install required packages
echo "Installing Sphinx and dependencies..."
pip install sphinx sphinx-autobuild sphinx-rtd-theme

# 2. Initialize Sphinx if not already done
if [[ ! -f "conf.py" ]]; then
    echo "Initializing Sphinx documentation..."
    sphinx-quickstart --quiet \
      --project='LLM Agent Framework' \
      --author='Your Name' \
      --release='1.0' \
      --language='en' \
      --makefile \
      --no-batchfile .
fi

# 3. Update conf.py for better configuration
cat >> conf.py << 'EOF'

# Additional configuration for automatic documentation
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

extensions.extend([
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode', 
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.githubpages',
])

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False

# Auto-documentation settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

html_theme = 'sphinx_rtd_theme'
EOF

# 4. Generate API documentation from source code
echo "Generating API documentation..."
sphinx-apidoc -o api ../src/ --separate --no-toc

# 5. Build the documentation
echo "Building HTML documentation..."
make html

echo "Documentation setup complete!"
echo "To view documentation:"
echo "  python -m http.server 8000 --directory _build/html"
echo "  Then open http://localhost:8000 in your browser"

echo "To rebuild documentation after changes:"
echo "  make html" 