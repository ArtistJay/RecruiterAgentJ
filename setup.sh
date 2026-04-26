#!/bin/bash
set -e

echo "🚀 agentJ — One-Command Setup"
echo "=============================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+."
    exit 1
fi

# Create virtual env
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# Check .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "⚠️  No .env found. Copying .env.example → .env"
        echo "   Please edit .env and add your GROQ_API_KEY!"
        cp .env.example .env
    else
        echo "❌ No .env or .env.example found!"
        exit 1
    fi
fi

# Create dirs
mkdir -p data/candidates data/sample_jds db/chroma docs/sample_outputs

# Generate candidates if not present
if [ ! "$(ls -A data/candidates/ 2>/dev/null)" ]; then
    echo "🧑‍💻 Generating synthetic candidates..."
    PYTHONPATH="${PWD}:${PYTHONPATH}" python3 scripts/generate_candidates.py
else
    echo "✅ Candidates already exist ($(ls data/candidates/*.json 2>/dev/null | wc -l) files)"
fi

# Seed vector DB if not present
if [ ! -d "db/chroma/chroma.sqlite3" ] && [ ! "$(ls -A db/chroma/ 2>/dev/null)" ]; then
    echo "🔍 Seeding ChromaDB vector store..."
    PYTHONPATH="${PWD}:${PYTHONPATH}" python3 scripts/seed_vectordb.py
else
    echo "✅ ChromaDB already seeded"
fi

echo ""
echo "=============================="
echo "✅ Setup complete!"
echo ""
echo "To run agentJ:"
echo "  source venv/bin/activate"
echo "  export PYTHONPATH=\"\${PWD}:\${PYTHONPATH}\""
echo "  streamlit run app.py"
echo ""
echo "To run tests:"
echo "  python tests/test_scoring.py"
echo "  python tests/test_full_pipeline.py"
