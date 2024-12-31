#!/usr/bin/env python3

# CURL example
# curl http://localhost:11434/api/generate -d '{
#   "model": "llama3",
#   "prompt": "Tell me a joke.",
#   "temperature": 0.7
# }'

import requests
import json
from typing import Optional

def test_ollama_call(prompt: str = "Tell me a short joke", model: str = "llama3") -> Optional[str]:
    """Make a test call to Ollama API.
    
    Args:
        prompt: The prompt to send to Ollama
        model: The model to use (default: llama3)
        
    Returns:
        The response text if successful, None if failed
    """
    url = "http://localhost:11434/api/generate"
    
    try:
        print("Sending request to Ollama...")
        response = requests.post(
            url,
            json={
                "model": model,
                "prompt": prompt,
                "temperature": 0.7
            },
            stream=True  # Enable streaming response
        )
        response.raise_for_status()
        
        # Process the streaming response
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    json_response = json.loads(line)
                    if 'response' in json_response:
                        chunk = json_response['response']
                        full_response += chunk
                        # Print the chunk as it comes in
                        print(chunk, end='', flush=True)
                except json.JSONDecodeError as e:
                    print(f"\nError parsing response chunk: {str(e)}")
        
        print("\n")  # Add newline after streaming completes
        return full_response
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama: {str(e)}")
        return None

def main():
    """Main function to test Ollama."""
    print("Testing Ollama API...")
    
    # First check if Ollama is running
    try:
        health_check = requests.get("http://localhost:11434/api/tags")
        health_check.raise_for_status()
    except requests.exceptions.RequestException:
        print("Error: Ollama is not running. Please start Ollama first.")
        return
    
    # Make the test call
    response = test_ollama_call()
    
    if response:
        print("\nFull response received successfully!")
        print("-" * 40)
    else:
        print("Failed to get response from Ollama")

if __name__ == "__main__":
    main()
