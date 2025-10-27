#!/bin/bash

# Installation script for Local Embeddings (Phase 2)
# This script installs Sentence Transformers and dependencies

set -e  # Exit on error

echo "=========================================================="
echo "  Local Embeddings Installation (Phase 2)"
echo "  Sentence Transformers + CLIP"
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

echo "📦 Installing Local Embedding Dependencies..."
echo ""

# Install PyTorch (required for Sentence Transformers)
echo "1/2 Installing PyTorch..."
echo "   (This may take a few minutes, ~800MB download)"
pip install torch>=2.0.0 --no-cache-dir

echo ""
echo "2/2 Installing Sentence Transformers..."
pip install sentence-transformers>=2.2.0 --no-cache-dir

echo ""
echo "✅ Local embeddings installation complete!"
echo ""

# Verify installation
echo "🔍 Verifying installation..."
python -c "
try:
    import torch
    print('✓ PyTorch imported successfully')
    print(f'  Version: {torch.__version__}')
    if torch.cuda.is_available():
        print(f'  ✓ GPU available: {torch.cuda.get_device_name(0)}')
    else:
        print('  ℹ  No GPU detected (CPU mode)')
except ImportError as e:
    print('✗ PyTorch import failed:', e)
    exit(1)

try:
    from sentence_transformers import SentenceTransformer
    print('✓ Sentence Transformers imported successfully')
except ImportError as e:
    print('✗ Sentence Transformers import failed:', e)
    exit(1)

try:
    from rag_agent.local_embeddings import LocalEmbeddingManager
    print('✓ Local embedding manager imported successfully')
except ImportError as e:
    print('✗ Local embedding manager import failed:', e)
    exit(1)
"

echo ""
echo "=========================================================="
echo "  Installation Complete!"
echo "=========================================================="
echo ""
echo "✨ Benefits of Local Embeddings:"
echo "   • $0 API costs (vs Cohere fees)"
echo "   • 10-100x faster (no network latency)"
echo "   • Unlimited usage (no rate limits)"
echo "   • Better privacy (data stays local)"
echo ""
echo "Next steps:"
echo "1. Enable local embeddings:"
echo "   echo 'USE_LOCAL_EMBEDDINGS=true' >> .env"
echo ""
echo "2. Test the installation:"
echo "   python test_local_embeddings.py"
echo ""
echo "3. Rebuild your knowledge base with new embeddings:"
echo "   python migrate_to_local_embeddings.py"
echo ""
echo "4. See PHASE2_EMBEDDINGS.md for more details"
echo ""
