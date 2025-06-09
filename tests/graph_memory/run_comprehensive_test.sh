#!/bin/bash

# Set environment variables for Ollama LLM testing
export DEV_MODE=true
export OLLAMA_BASE_URL=http://192.168.1.173:11434
export OLLAMA_MODEL=gemma3
export OLLAMA_EMBED_MODEL=mxbai-embed-large

echo "Environment variables set:"
echo "  DEV_MODE=$DEV_MODE"
echo "  OLLAMA_BASE_URL=$OLLAMA_BASE_URL"
echo "  OLLAMA_MODEL=$OLLAMA_MODEL"
echo "  OLLAMA_EMBED_MODEL=$OLLAMA_EMBED_MODEL"
echo ""

# Run the comprehensive test
python test_alternative_extractors_comprehensive.py 