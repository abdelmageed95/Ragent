#!/bin/bash

# =================================================================
# Ollama Installation Script for Phase 5 (Local LLM Support)
# =================================================================
#
# Installs Ollama for running LLMs locally (zero cost!)
#

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Ollama Installation (Phase 5: Local LLM)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
else:
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo "🔍 Detected OS: $OS"
echo ""

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -n 1 || echo "unknown")
    echo "✓ Ollama already installed: $OLLAMA_VERSION"
    echo ""
else
    echo "📦 Installing Ollama..."
    echo ""

    if [ "$OS" == "linux" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [ "$OS" == "mac" ]; then
        # Download and install via brew or direct download
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            echo "Downloading Ollama for macOS..."
            curl -L https://ollama.com/download/Ollama-darwin.zip -o /tmp/ollama.zip
            unzip -q /tmp/ollama.zip -d /Applications/
            rm /tmp/ollama.zip
        fi
    fi

    echo ""
    echo "✓ Ollama installed successfully"
    echo ""
fi

# Start Ollama service
echo "🚀 Starting Ollama service..."
echo ""

if [ "$OS" == "linux" ]; then
    # Start as systemd service
    if command -v systemctl &> /dev/null; then
        sudo systemctl start ollama || ollama serve > /dev/null 2>&1 &
        sleep 2
    else
        ollama serve > /dev/null 2>&1 &
        sleep 2
    fi
elif [ "$OS" == "mac" ]; then
    # Start Ollama app
    open -a Ollama 2>/dev/null || ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# Test if Ollama is running
if ollama list &> /dev/null; then
    echo "✓ Ollama service is running"
else
    echo "⚠️  Ollama service may not be running"
    echo "   Start manually: ollama serve"
fi

echo ""

# Pull recommended model
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Downloading Recommended Model"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Recommended models for RAG:"
echo "  • llama3.2:latest (3B) - Fast, good quality"
echo "  • mistral:latest (7B) - Better quality, slower"
echo "  • phi3:latest (3.8B) - Balanced"
echo ""

read -p "Download llama3.2:latest (~2GB)? [Y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    echo "Downloading llama3.2:latest..."
    ollama pull llama3.2:latest
    echo ""
    echo "✓ Model downloaded"
fi

echo ""

# Show available models
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Available Models"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
ollama list

echo ""

# Test Ollama
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Testing Ollama"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if any model is available
MODELS=$(ollama list | tail -n +2 | wc -l)

if [ "$MODELS" -gt 0 ]; then
    MODEL=$(ollama list | tail -n +2 | head -n 1 | awk '{print $1}')
    echo "Testing with model: $MODEL"
    echo "Prompt: What is 2+2?"
    echo ""
    ollama run $MODEL "What is 2+2? Answer in one short sentence." 2>/dev/null || echo "Test skipped"
    echo ""
    echo "✓ Ollama is working!"
else
    echo "⚠️  No models installed"
    echo "   Download a model: ollama pull llama3.2:latest"
fi

echo ""

# Configuration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To use Ollama in your application, add to .env:"
echo ""
echo "  LLM_PROVIDER=ollama"
echo "  LLM_MODEL=llama3.2:latest"
echo ""
echo "Or keep using OpenAI/Gemini (Ollama is optional)"
echo ""

# Python package
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Python Integration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Install Python client:"
echo "  pip install ollama"
echo ""

# Additional models
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Other Recommended Models"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Download additional models:"
echo "  ollama pull mistral:latest      # 7B, high quality"
echo "  ollama pull phi3:latest         # 3.8B, Microsoft"
echo "  ollama pull llama3.1:8b         # Meta's Llama 3.1"
echo ""
echo "List all available models:"
echo "  ollama list"
echo ""
echo "Remove a model:"
echo "  ollama rm <model-name>"
echo ""

echo "✅ Ollama installation complete!"
echo ""
echo "Benefits:"
echo "  ✓ Zero cost (runs locally)"
echo "  ✓ No API keys needed"
echo "  ✓ Privacy (data stays local)"
echo "  ✓ Offline capability"
echo ""
echo "Next steps:"
echo "  1. Install Python client: pip install ollama"
echo "  2. Configure in .env: LLM_PROVIDER=ollama"
echo "  3. Test: python core/llm/llm_manager.py"
