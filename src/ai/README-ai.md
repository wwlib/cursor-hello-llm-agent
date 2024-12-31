# LLM Service Interface

Provides a standardized interface for interacting with different LLM providers (OpenAI, Ollama, etc.).

## Overview

The LLM service architecture uses a base class that defines the common interface, with specialized implementations for different LLM providers. This allows the rest of the application to work with any LLM service transparently.

### Key Features

- **Provider Agnostic**: Common interface for all LLM providers
- **Easy Integration**: Simple to add new LLM providers
- **Consistent Error Handling**: Standardized error handling across providers
- **Configuration Management**: Provider-specific settings handled in subclasses
- **Response Formatting**: Consistent response format regardless of provider

## Architecture

### Components

```
ai/
├── llm.py              # Base LLM interface
├── llm_openai.py       # OpenAI implementation
├── llm_ollama.py       # Ollama implementation
└── README.md           # This documentation
```

## Base LLM Interface

```python
from typing import Dict, Any, Optional

class LLMService:
    """Base class for LLM service providers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def generate(self, prompt: str) -> str:
        """Generate a response from the LLM"""
        raise NotImplementedError
    
    def validate_response(self, response: str) -> bool:
        """Validate LLM response format"""
        raise NotImplementedError
```

## OpenAI Implementation

The OpenAI implementation (`llm_openai.py`) provides integration with OpenAI's API:

```python
from .llm import LLMService
import openai

class OpenAIService(LLMService):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        self.model = config.get('model', 'gpt-4')
        openai.api_key = self.api_key

    def generate(self, prompt: str) -> str:
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMServiceError(f"OpenAI API error: {str(e)}")
```

### OpenAI Configuration

```python
config = {
    "api_key": "your-api-key",  # Optional if using env var
    "model": "gpt-4",           # Or other OpenAI model
    "temperature": 0.7,
    "max_tokens": 1000
}
```

## Ollama Implementation

The Ollama implementation (`llm_ollama.py`) provides integration with local Ollama models:

```python
from .llm import LLMService
import requests

class OllamaService(LLMService):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model = config.get('model', 'llama2')

    def generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt
                }
            )
            return response.json()['response']
        except Exception as e:
            raise LLMServiceError(f"Ollama API error: {str(e)}")
```

### Ollama Configuration

```python
config = {
    "base_url": "http://localhost:11434",  # Ollama API endpoint
    "model": "llama2",                     # Or other installed model
    "temperature": 0.7
}
```

## Usage

### Basic Usage

```python
# Using OpenAI
from ai.llm_openai import OpenAIService

llm = OpenAIService({
    "model": "gpt-4",
    "temperature": 0.7
})

response = llm.generate("Your prompt here")

# Using Ollama
from ai.llm_ollama import OllamaService

llm = OllamaService({
    "model": "llama2"
})

response = llm.generate("Your prompt here")
```

### Error Handling

```python
from ai.exceptions import LLMServiceError

try:
    response = llm.generate("Your prompt")
except LLMServiceError as e:
    print(f"LLM error: {str(e)}")
```

## Best Practices

1. **Configuration Management**
   - Use environment variables for sensitive data
   - Provide sensible defaults
   - Allow runtime configuration

2. **Error Handling**
   - Catch and wrap provider-specific errors
   - Provide meaningful error messages
   - Include retry logic for transient failures

3. **Response Validation**
   - Verify response format
   - Handle incomplete or malformed responses
   - Implement timeout handling

## Future Enhancements

1. **Additional Providers**
   - Add support for other LLM providers
   - Implement provider-specific optimizations

2. **Advanced Features**
   - Streaming responses
   - Token counting
   - Cost tracking

3. **Performance Optimization**
   - Response caching
   - Request batching
   - Connection pooling
