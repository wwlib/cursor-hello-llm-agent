import pytest
from unittest.mock import Mock, patch
import os
import json
import requests
from src.ai.llm import LLMService, LLMServiceError
from src.ai.llm_openai import OpenAIService
from src.ai.llm_ollama import OllamaService

# Base LLMService Tests
def test_base_llm_init():
    config = {"test": "config"}
    service = LLMService(config)
    assert service.config == config

def test_base_llm_init_no_config():
    service = LLMService()
    assert service.config == {}

def test_base_llm_generate():
    service = LLMService()
    with pytest.raises(NotImplementedError):
        service.generate("test prompt")

def test_base_llm_validate():
    service = LLMService()
    with pytest.raises(NotImplementedError):
        service.validate_response("test response")

# OpenAI Service Tests
def test_openai_init():
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        service = OpenAIService()
        assert service.api_key == 'test-key'
        assert service.model == 'gpt-4'
        assert service.temperature == 0.7

def test_openai_init_with_config():
    config = {
        'api_key': 'config-key',
        'model': 'gpt-3.5-turbo',
        'temperature': 0.5
    }
    service = OpenAIService(config)
    assert service.api_key == 'config-key'
    assert service.model == 'gpt-3.5-turbo'
    assert service.temperature == 0.5

def test_openai_init_no_api_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(LLMServiceError):
            OpenAIService()

@patch('openai.ChatCompletion.create')
def test_openai_generate_success(mock_create):
    mock_create.return_value.choices = [
        Mock(message=Mock(content="test response"))
    ]
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        service = OpenAIService()
        response = service.generate("test prompt")
        
        assert response == "test response"
        mock_create.assert_called_once()

@patch('openai.ChatCompletion.create')
def test_openai_generate_failure(mock_create):
    mock_create.side_effect = Exception("API error")
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        service = OpenAIService()
        with pytest.raises(LLMServiceError):
            service.generate("test prompt")

def test_openai_validate_response():
    service = OpenAIService({'api_key': 'test-key'})
    assert service.validate_response("valid response") is True
    assert service.validate_response("") is False
    assert service.validate_response("  ") is False
    assert service.validate_response(None) is False

# Ollama Service Tests
def test_ollama_init():
    service = OllamaService()
    assert service.base_url == 'http://localhost:11434'
    assert service.model == 'llama3'
    assert service.temperature == 0.7

def test_ollama_init_with_config():
    config = {
        'base_url': 'http://custom:11434',
        'model': 'custom-model',
        'temperature': 0.5
    }
    service = OllamaService(config)
    assert service.base_url == 'http://custom:11434'
    assert service.model == 'custom-model'
    assert service.temperature == 0.5

@patch('requests.post')
def test_ollama_generate_success(mock_post):
    # Create a Mock response object with proper structure
    mock_response = Mock()
    # Make the response iterable by setting the iter method
    mock_response.iter_lines.return_value = [
        b'{"response": "test response"}'
    ]
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    service = OllamaService()
    response = service.generate("test prompt")
    
    assert response == "test response"
    mock_post.assert_called_once()

@patch('requests.post')
def test_ollama_generate_request_failure(mock_post):
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")
    
    service = OllamaService()
    with pytest.raises(LLMServiceError):
        service.generate("test prompt")

@patch('requests.post')
def test_ollama_generate_invalid_response(mock_post):
    mock_response = Mock()
    # Return an invalid JSON string that will cause a JSON decode error
    mock_response.iter_lines.return_value = [
        b'{"invalid json'
    ]
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    service = OllamaService()
    with pytest.raises(LLMServiceError):
        service.generate("test prompt")

def test_ollama_validate_response():
    service = OllamaService()
    assert service.validate_response("valid response") is True
    assert service.validate_response("") is False
    assert service.validate_response("  ") is False
    assert service.validate_response(None) is False
