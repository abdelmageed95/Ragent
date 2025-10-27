#!/bin/bash

# =================================================================
# Redis Installation Script for Phase 4 Performance Optimization
# =================================================================
#
# This script installs Redis for caching layer
# Required for: Embedding cache, Query cache, Session cache
#

set -e  # Exit on error

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Redis Installation (Phase 4: Performance)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo "🔍 Detected OS: $OS"
echo ""

# Check if Redis is already installed
if command -v redis-server &> /dev/null; then
    REDIS_VERSION=$(redis-server --version | head -n 1)
    echo "✓ Redis already installed: $REDIS_VERSION"
    echo ""

    # Check if Redis is running
    if redis-cli ping &> /dev/null; then
        echo "✓ Redis is running"
        echo ""
        echo "Installation complete! Redis is ready to use."
        exit 0
    else
        echo "⚠️ Redis installed but not running"
        echo ""
    fi
else
    echo "📦 Installing Redis..."
    echo ""

    if [ "$OS" == "linux" ]; then
        # Ubuntu/Debian
        if command -v apt-get &> /dev/null; then
            echo "Using apt-get (Ubuntu/Debian)..."
            sudo apt-get update
            sudo apt-get install -y redis-server
        # Fedora/CentOS/RHEL
        elif command -v dnf &> /dev/null; then
            echo "Using dnf (Fedora/RHEL)..."
            sudo dnf install -y redis
        elif command -v yum &> /dev/null; then
            echo "Using yum (CentOS)..."
            sudo yum install -y redis
        else
            echo "❌ No supported package manager found"
            echo "Please install Redis manually: https://redis.io/download"
            exit 1
        fi
    elif [ "$OS" == "mac" ]; then
        if command -v brew &> /dev/null; then
            echo "Using Homebrew..."
            brew install redis
        else
            echo "❌ Homebrew not found"
            echo "Install Homebrew first: https://brew.sh"
            exit 1
        fi
    fi

    echo ""
    echo "✓ Redis installed successfully"
    echo ""
fi

# Start Redis
echo "🚀 Starting Redis server..."
echo ""

if [ "$OS" == "linux" ]; then
    # Check if systemd is available
    if command -v systemctl &> /dev/null; then
        echo "Using systemd..."
        sudo systemctl start redis-server || sudo systemctl start redis
        sudo systemctl enable redis-server || sudo systemctl enable redis
        echo "✓ Redis started and enabled on boot"
    else
        # Fallback to manual start
        echo "Starting Redis manually..."
        redis-server --daemonize yes
        echo "✓ Redis started as daemon"
    fi
elif [ "$OS" == "mac" ]; then
    echo "Using brew services..."
    brew services start redis
    echo "✓ Redis started"
fi

echo ""

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
sleep 2

# Test connection
if redis-cli ping &> /dev/null; then
    echo "✓ Redis is responding"
    echo ""

    # Get Redis info
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Redis Information"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    REDIS_VERSION=$(redis-cli info server | grep redis_version | cut -d':' -f2 | tr -d '\r')
    REDIS_MODE=$(redis-cli info server | grep redis_mode | cut -d':' -f2 | tr -d '\r')
    echo "  Version: $REDIS_VERSION"
    echo "  Mode: $REDIS_MODE"
    echo "  Port: 6379"
    echo ""

    echo "✅ Redis installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Install Python Redis client: pip install redis"
    echo "  2. Configure Redis in .env (optional):"
    echo "     REDIS_HOST=localhost"
    echo "     REDIS_PORT=6379"
    echo "     REDIS_ENABLED=true"
    echo ""
else
    echo "❌ Redis is not responding"
    echo ""
    echo "Troubleshooting:"
    echo "  • Check if Redis is running: redis-cli ping"
    echo "  • View Redis logs: sudo journalctl -u redis"
    echo "  • Restart Redis: sudo systemctl restart redis"
    exit 1
fi

# Optional: Set Redis configuration for production
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Optional: Production Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "For production, consider configuring:"
echo "  • Max memory limit (maxmemory)"
echo "  • Eviction policy (maxmemory-policy)"
echo "  • Persistence (appendonly)"
echo "  • Password authentication (requirepass)"
echo ""
echo "Edit Redis config: /etc/redis/redis.conf"
echo ""

echo "🎉 Setup complete! Redis is ready for Phase 4 caching."
