#!/usr/bin/env python3

# CURL example
# curl http://localhost:11434/api/embed -d '{
#   "model": "mxbai-embed-large",
#   "input": "Llamas are members of the camelid family"
# }'

# batch embeddings - returns a list of embeddings
# curl http://192.168.1.173:11434/api/embed -d '{
#   "model": "mxbai-embed-large",
#   "input": "Llamas are members of the camelid family"
# }'

# one embedding at a time - returns a single embedding
# curl http://192.168.1.173:11434/api/embeddings -d '{
#   "model": "mxbai-embed-large",
#   "prompt": "Llamas are members of the camelid family"
# }'

import requests
import json
import numpy as np
from typing import Optional, List, Dict
import os

ollama_base_url = "http://192.168.1.173:11434"

# Example texts to compare against
test_texts = [
    "The cat sat on the mat.",
    "A cat was sitting on the mat.",
    "The weather is nice today.",
    "The world is a simple, flat world with a single continent.",
    "The monster is known as the Mountain Troll.",
    "The village has offered a reward of 1000 gold coins."
]

def generate_embedding(text: str, model: str = "mxbai-embed-large", normalize: bool = True) -> Optional[List[float]]:
    """Generate an embedding for the given text using Ollama.
    
    Args:
        text: The text to generate an embedding for
        model: The model to use (default: mxbai-embed-large)
        normalize: Whether to normalize the embedding vector (default: True)
        
    Returns:
        The embedding vector if successful, None if failed
    """
    url = os.getenv("OLLAMA_BASE_URL", ollama_base_url)
    url = f"{url}/api/embed" # batch embeddings
    # url = f"{url}/api/embeddings" # one embedding at a time
    
    try:
        print(f"Generating embedding for: {text[:50]}...")
        response = requests.post(
            url,
            json={
                "model": model,
                "input": text
            }
        )
        response.raise_for_status()
        
        print(response.json())
        
        # Parse response
        result = response.json()
        if not isinstance(result, dict) or 'embeddings' not in result:
            print("Invalid response format from Ollama API")
            return None
            
        embedding = result['embeddings'][0]

        # Print embedding vector size
        print(f"Embedding vector size: {len(embedding)}")
        
        # Normalize if requested
        if normalize:
            embedding = np.array(embedding)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = (embedding / norm).tolist()
        
        return embedding
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {str(e)}")
        return None

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        float: Cosine similarity score between 0 and 1
    """
    return np.dot(embedding1, embedding2)

def analyze_similarities(input_text: str, input_embedding: List[float], test_embeddings: Dict[str, List[float]]):
    """Analyze and print similarities between input text and all test texts.
    
    Args:
        input_text: The input text to compare against
        input_embedding: The embedding of the input text
        test_embeddings: Dictionary mapping test texts to their embeddings
    """
    print("\nSimilarity Analysis:")
    print("-" * 40)
    print(f"Input Text: {input_text}")
    print("-" * 40)
    
    # Calculate and print similarities
    similarities = []
    for text, embedding in test_embeddings.items():
        similarity = calculate_similarity(input_embedding, embedding)
        similarities.append((text, similarity))
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Print results
    for text, similarity in similarities:
        print(f"\nTest Text: {text[:50]}...")
        print(f"Similarity: {similarity:.4f}")

def main():
    """Main function to test Ollama embeddings."""
    print("Testing Ollama Embeddings API...")
    
    # First check if Ollama is running
    try:
        base_url = os.getenv("OLLAMA_BASE_URL", ollama_base_url)
        health_check = requests.get(f"{base_url}/api/tags")
        health_check.raise_for_status()
        print(f"Ollama is running at {base_url}")
    except requests.exceptions.RequestException:
        print("Error: Ollama is not running. Please start Ollama first.")
        return
    
    # Get input text from user
    input_text = input("\nEnter text to compare: ")
    if not input_text.strip():
        print("No input text provided. Exiting.")
        return
    
    # Generate embedding for input text
    input_embedding = generate_embedding(input_text)
    if not input_embedding:
        print("Failed to generate embedding for input text.")
        return
    
    # Generate embeddings for all test texts
    test_embeddings = {}
    for text in test_texts:
        embedding = generate_embedding(text)
        if embedding:
            test_embeddings[text] = embedding
            print(f"Generated embedding of length {len(embedding)}")
        else:
            print(f"Failed to generate embedding for: {text[:50]}...")
    
    # Analyze similarities if we have embeddings
    if test_embeddings:
        analyze_similarities(input_text, input_embedding, test_embeddings)
    else:
        print("No test embeddings were generated successfully")

if __name__ == "__main__":
    main()
