#!/bin/bash
set -e

echo ""
echo "🕵️  agentJ — AI-Powered Talent Scouting Agent"
echo "================================================"
echo ""
echo "Choose setup method:"
echo "  1) Python venv (recommended — works everywhere)"
echo "  2) Docker (requires Docker installed)"
echo ""
read -p "Enter 1 or 2: " method

if [ "$method" = "2" ]; then
    echo ""
    echo "🐳 Docker Setup"
    echo "----------------"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Install Docker first: https://docs.docker.com/get-docker/"
        echo "   Or try Method 1 (Python venv) instead."
        exit 1
    fi

    # Check for API key
    if [ -z "$GROQ_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
        echo ""
        read -p "Enter your Groq API Key (or press Enter to set later in UI): " api_key
        if [ -n "$api_key" ]; then
            export GROQ_API_KEY="$api_key"
        fi
    fi

    echo ""
    echo "📦 Building Docker image (this may take a few minutes first time)..."
    docker build -t agentj .

    echo ""
    echo "🚀 Starting agentJ..."
    echo "   Open http://localhost:8501 in your browser"
    echo "   Press Ctrl+C to stop"
    echo ""

    docker run -p 8501:8501 \
        -e GROQ_API_KEY="${GROQ_API_KEY:-}" \
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        -e LLM_PROVIDER="${LLM_PROVIDER:-groq}" \
        -v agentj_data:/app/db \
        agentj

else
    echo ""
    echo "🐍 Python venv Setup"
    echo "---------------------"

    # Check GCC version
    if command -v gcc &> /dev/null; then
        gcc_ver=$(gcc -dumpversion | cut -d. -f1)
        if [ "$gcc_ver" -lt 8 ]; then
            echo "⚠️  GCC version $gcc_ver detected. GCC 8+ is required for some dependencies."
            echo "   Upgrade with: sudo apt install gcc-12 g++-12"
            echo "   Or: sudo yum install gcc-toolset-12"
            exit 1
        fi
    else
        echo "⚠️  GCC not found. Some Python packages need GCC to compile."
        echo "   Install with: sudo apt install build-essential"
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Install Python 3.10+ first."
        exit 1
    fi

    # Create venv
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi

    echo "📦 Activating virtual environment..."
    source venv/bin/activate

    echo "📦 Installing dependencies..."
    pip install -r requirements.txt --quiet

    # Create dirs
    mkdir -p data/candidates data/sample_jds db/chroma docs/sample_outputs

    # Check .env
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo "⚠️  Created .env from .env.example — edit it to add your API key"
        else
            echo ""
            read -p "Enter your Groq API Key (or press Enter to set later in UI): " api_key
            cat > .env << ENVEOF
LLM_PROVIDER=groq
GROQ_API_KEY=${api_key}
OPENAI_API_KEY=
MODE=cloud
ENVEOF
            echo "✅ Created .env file"
        fi
    fi

    # Seed data if empty
    if [ ! "$(ls -A data/candidates/ 2>/dev/null)" ]; then
        echo "🧑‍💻 Generating synthetic candidates..."
        PYTHONPATH="${PWD}:${PYTHONPATH}" python3 scripts/generate_candidates.py
    else
        echo "✅ Candidates already exist ($(ls data/candidates/*.json 2>/dev/null | wc -l) files)"
    fi

    # Seed vector DB
    if [ ! "$(ls db/chroma/ 2>/dev/null | grep -v .gitkeep)" ]; then
        echo "🔍 Seeding ChromaDB..."
        PYTHONPATH="${PWD}:${PYTHONPATH}" python3 scripts/seed_vectordb.py
    else
        echo "✅ ChromaDB already seeded"
    fi

    echo ""
    echo "================================================"
    echo "✅ Setup complete!"
    echo ""
    echo "Run this command to start the app:"
    echo ""
    echo "   source venv/bin/activate && PYTHONPATH=\"\${PWD}:\${PYTHONPATH}\" streamlit run app.py"
    echo ""
    echo "Then open http://localhost:8501 in your browser"
    echo "================================================"
fi
