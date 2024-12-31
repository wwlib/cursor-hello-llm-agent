import pytest
import requests
from src.ai.llm_ollama import OllamaService, LLMServiceError
from unittest.mock import patch, Mock

def is_ollama_running():
    """Check if Ollama is running locally"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

@pytest.mark.integration
@pytest.mark.skipif(not is_ollama_running(), reason="Ollama is not running locally")
def test_ollama_real_integration_streaming():
    """Integration test with real Ollama instance using streaming.
    Requires Ollama to be running locally with llama3 model installed.
    """
    service = OllamaService({
        "model": "llama3",
        "temperature": 0.1,  # Lower temperature for more deterministic results
        "stream": True
    })
    
    # Simple prompt that should get a consistent response
    prompt = "What is 2+2? Answer with just the number."
    
    try:
        response = service.generate(prompt)
        print("\nStreaming response:")
        print(response)
        
        # Basic validation
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        
        # The response should contain "4" somewhere
        # Note: Even with low temperature, LLMs might format the answer differently
        assert "4" in response.strip(), f"Expected '4' in response, got: {response}"
        
    except LLMServiceError as e:
        pytest.fail(f"Ollama API call failed: {str(e)}")
    except Exception as e:
        pytest.fail(f"Unexpected error: {str(e)}")

@pytest.mark.integration
@pytest.mark.skipif(not is_ollama_running(), reason="Ollama is not running locally")
def test_ollama_real_integration_non_streaming():
    """Integration test with real Ollama instance without streaming.
    Requires Ollama to be running locally with llama3 model installed.
    """
    service = OllamaService({
        "model": "llama3",
        "temperature": 0.1,
        "stream": False
    })
    
    prompt = "What is 2+2? Answer with just the number."
    
    try:
        response = service.generate(prompt)
        print("\nNon-streaming response:")
        print(response)
        
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        assert "4" in response.strip(), f"Expected '4' in response, got: {response}"
        
    except LLMServiceError as e:
        pytest.fail(f"Ollama API call failed: {str(e)}")
    except Exception as e:
        pytest.fail(f"Unexpected error: {str(e)}")

@pytest.mark.integration
@pytest.mark.skipif(not is_ollama_running(), reason="Ollama is not running locally")
def test_ollama_real_json_response():
    """Test Ollama's ability to generate JSON-formatted responses.
    Requires Ollama to be running locally with llama3 model installed.
    """
    service = OllamaService({
        "model": "llama3",
        "temperature": 0.1,
        "stream": True
    })
    
    prompt = """Return a JSON object with this structure:
{
    "number": 42,
    "text": "Hello, World!"
}
Return ONLY the JSON, no other text."""
    
    try:
        response = service.generate(prompt)
        print("\nJSON response:")
        print(response)
        
        # Basic validation
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        
        # Response should contain both expected values
        assert "42" in response
        assert "Hello, World!" in response
        
    except LLMServiceError as e:
        pytest.fail(f"Ollama API call failed: {str(e)}")
    except Exception as e:
        pytest.fail(f"Unexpected error: {str(e)}")

# Add unit tests for non-integration scenarios
@patch('requests.post')
def test_ollama_generate_streaming_success(mock_post):
    """Unit test for successful streaming generation"""
    mock_response = Mock()
    mock_response.iter_lines.return_value = [
        b'{"response": "This "}\n',
        b'{"response": "is "}\n',
        b'{"response": "a test"}\n'
    ]
    mock_post.return_value = mock_response
    
    service = OllamaService({"stream": True})
    response = service.generate("test prompt")
    
    assert response == "This is a test"
    mock_post.assert_called_once()

@patch('requests.post')
def test_ollama_generate_non_streaming_success(mock_post):
    """Unit test for successful non-streaming generation"""
    mock_response = Mock()
    mock_response.json.return_value = {"response": "test response"}
    mock_post.return_value = mock_response
    
    service = OllamaService({"stream": False})
    response = service.generate("test prompt")
    
    assert response == "test response"
    mock_post.assert_called_once()
