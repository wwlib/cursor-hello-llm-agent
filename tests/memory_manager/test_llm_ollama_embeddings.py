"""Tests for Ollama embeddings generation functionality."""

import pytest
import os
import json
import numpy as np
from src.ai.llm_ollama import OllamaService, LLMServiceError

ollama_base_url = "http://192.168.1.173:11434"
ollama_embed_model = "mxbai-embed-large"

@pytest.fixture
def llm_service():
    """Create an OllamaService instance for testing."""
    return OllamaService({
        "base_url": os.getenv("OLLAMA_BASE_URL", ollama_base_url),
        "model": os.getenv("OLLAMA_MODEL", ollama_embed_model),
        "debug": True,
        "debug_scope": "test_embeddings"
    })

def test_generate_embedding_basic(llm_service):
    """Test basic embedding generation."""
    # Generate embedding for a simple text
    text = "This is a test sentence for embedding generation."
    embedding = llm_service.generate_embedding(text)
    
    # Check that we got a valid embedding
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, (int, float)) for x in embedding)
    
    # Check that the embedding is normalized
    norm = np.linalg.norm(embedding)
    assert abs(norm - 1.0) < 1e-6  # Should be normalized to unit length

def test_generate_embedding_options(llm_service):
    """Test embedding generation with different options."""
    text = "Testing embedding options."
    
    # Test with normalization disabled
    embedding = llm_service.generate_embedding(text, {"normalize": False})
    norm = np.linalg.norm(embedding)
    assert norm != 1.0  # Should not be normalized
    
    # Test with different model
    try:
        embedding = llm_service.generate_embedding(text, {"model": "gemma"})
        assert isinstance(embedding, list)
        assert len(embedding) > 0
    except LLMServiceError:
        # Skip if model not available
        pass

def test_generate_embedding_empty_text(llm_service):
    """Test embedding generation with empty text."""
    with pytest.raises(LLMServiceError):
        llm_service.generate_embedding("")

def test_generate_embedding_long_text(llm_service):
    """Test embedding generation with long text."""
    # Create a long text
    long_text = "This is a test. " * 1000
    
    # Should still work with long text
    embedding = llm_service.generate_embedding(long_text)
    assert isinstance(embedding, list)
    assert len(embedding) > 0

def test_validate_embedding(llm_service):
    """Test embedding validation."""
    # Valid embedding
    valid_embedding = [0.1, 0.2, 0.3]
    assert llm_service.validate_embedding(valid_embedding)
    
    # Invalid embeddings
    assert not llm_service.validate_embedding([])  # Empty list
    assert not llm_service.validate_embedding(["not", "a", "number"])  # Non-numeric
    assert not llm_service.validate_embedding(None)  # None
    assert not llm_service.validate_embedding("not a list")  # Not a list

def test_embedding_consistency(llm_service):
    """Test that same text produces consistent embeddings."""
    text = "Testing embedding consistency."
    
    # Generate two embeddings for the same text
    embedding1 = llm_service.generate_embedding(text)
    embedding2 = llm_service.generate_embedding(text)
    
    # They should be very similar
    similarity = np.dot(embedding1, embedding2)
    assert similarity > 0.99  # Should be almost identical

def test_embedding_similarity(llm_service):
    """Test that similar texts produce similar embeddings."""
    text1 = "The cat sat on the mat."
    text2 = "A cat was sitting on the mat."
    text3 = "The weather is nice today."
    
    # Generate embeddings
    embedding1 = llm_service.generate_embedding(text1)
    embedding2 = llm_service.generate_embedding(text2)
    embedding3 = llm_service.generate_embedding(text3)
    
    # Calculate similarities
    similarity_same = np.dot(embedding1, embedding2)
    similarity_different = np.dot(embedding1, embedding3)
    
    # Similar texts should have higher similarity
    assert similarity_same > similarity_different

def test_embedding_error_handling(llm_service):
    """Test error handling in embedding generation."""
    # Test with invalid model
    with pytest.raises(LLMServiceError):
        llm_service.generate_embedding("test", {"model": "nonexistent_model"})
    
    # Test with invalid URL
    bad_service = OllamaService({
        "base_url": "http://nonexistent:11434",
        "model": ollama_embed_model
    })
    with pytest.raises(LLMServiceError):
        bad_service.generate_embedding("test")
