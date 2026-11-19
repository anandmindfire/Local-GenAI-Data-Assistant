#!/usr/bin/env bash
# Script to download and verify required local Ollama models.
set -euo pipefail

OLLAMA_HOST="${OLLAMA_BASE_URL:-http://localhost:11434}"
CHAT_MODEL="${CHAT_MODEL:-qwen3:1.7b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"

echo "=================================================="
echo "Local GenAI Assistant: Model Setup"
echo "Target Ollama Instance: $OLLAMA_HOST"
echo "Chat Model:             $CHAT_MODEL"
echo "Embedding Model:        $EMBEDDING_MODEL"
echo "=================================================="

# 1. Verify Ollama connectivity
echo "Checking Ollama connectivity..."
if ! curl -sf "$OLLAMA_HOST/api/tags" >/dev/null; then
    echo "ERROR: Cannot connect to Ollama at $OLLAMA_HOST."
    echo "Please ensure Ollama is running ('ollama serve' or via Docker Compose)."
    exit 1
fi
echo "Ollama is online."

# Helper function to check if model exists
is_model_present() {
    local model_name="$1"
    curl -sf "$OLLAMA_HOST/api/tags" | grep -q "\"name\":\"$model_name"
}

# 2. Pull Embedding Model
echo "Checking embedding model: $EMBEDDING_MODEL..."
if is_model_present "$EMBEDDING_MODEL"; then
    echo "Embedding model '$EMBEDDING_MODEL' is already present."
else
    echo "Pulling embedding model '$EMBEDDING_MODEL'..."
    curl -X POST "$OLLAMA_HOST/api/pull" -d "{\"name\": \"$EMBEDDING_MODEL\"}"
    echo ""
    echo "Embedding model '$EMBEDDING_MODEL' pulled successfully."
fi

# 3. Pull Chat Model
echo "Checking chat model: $CHAT_MODEL..."
if is_model_present "$CHAT_MODEL"; then
    echo "Chat model '$CHAT_MODEL' is already present."
else
    echo "Pulling chat model '$CHAT_MODEL'..."
    # Note: If qwen3:8b is not yet in public library or unavailable, fallback message is provided
    if ! curl -X POST "$OLLAMA_HOST/api/pull" -d "{\"name\": \"$CHAT_MODEL\"}"; then
        echo "WARNING: Failed to pull '$CHAT_MODEL'."
        echo "If this model name is experimental, consider setting CHAT_MODEL=qwen2.5:7b or llama3.1:8b in .env"
    fi
    echo ""
    echo "Chat model setup completed."
fi

echo "=================================================="
echo "Available models on Ollama:"
curl -sf "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' || true
echo "=================================================="
echo "Model initialization finished."
