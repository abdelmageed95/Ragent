#!/bin/bash

# Installation script for ChromaDB (Phase 3)
# Vector database for better persistence and metadata management

set -e  # Exit on error

echo "=========================================================="
echo "  ChromaDB Installation (Phase 3)"
echo "  Modern Vector Database"
echo "=========================================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Recommended: Activate your virtual environment first"
    echo "   Example: source .ragenv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 Installing ChromaDB..."
echo ""

# Install ChromaDB
pip install chromadb>=0.4.0 --no-cache-dir

echo ""
echo "✅ ChromaDB installation complete!"
echo ""

# Verify installation
echo "🔍 Verifying installation..."
python -c "
try:
    import chromadb
    print('✓ ChromaDB imported successfully')
    print(f'  Version: {chromadb.__version__}')
except ImportError as e:
    print('✗ ChromaDB import failed:', e)
    exit(1)

try:
    from rag_agent.vector_store import ChromaVectorStore
    print('✓ Vector store module imported successfully')
except ImportError as e:
    print('✗ Vector store import failed:', e)
    exit(1)
"

echo ""
echo "=========================================================="
echo "  Installation Complete!"
echo "=========================================================="
echo ""
echo "✨ Benefits of ChromaDB:"
echo "   • Automatic persistence (no manual save/load)"
echo "   • Rich metadata filtering"
echo "   • Incremental updates"
echo "   • Better developer experience"
echo "   • Production-ready features"
echo ""
echo "Next steps:"
echo "1. Test the installation:"
echo "   python test_chromadb.py"
echo ""
echo "2. Migrate from FAISS (if you have existing data):"
echo "   python migrate_to_chromadb.py"
echo ""
echo "3. See PHASE3_COMPLETE.md for usage examples"
echo ""
