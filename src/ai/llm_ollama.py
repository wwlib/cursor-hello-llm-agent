from typing import Dict, Any, Optional, List
import requests
import json
from .llm import LLMService, LLMServiceError
import time
import numpy as np
import os
import asyncio

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

# See: examples/call_ollama_to_generate_embeddings.py for examples of how to call the Ollama API


class OllamaService(LLMService):
    """LLM service implementation using Ollama"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Ollama service.
        
        Args:
            config: Configuration dictionary with required fields:
                   - base_url: str - Ollama server URL
                   - model: str - Model name to use
                   Optional fields:
                   - stream: bool - Whether to stream the response
                   - logger: logging.Logger - Logger to use for logging
                   - default_temperature: float - Default sampling temperature (0.0 to 1.0)
        """
        # Ensure /logs directory exists if debug_file is specified
        debug_file = config.get('debug_file')
        if debug_file:
            logs_dir = os.path.dirname(debug_file)
            if logs_dir and not os.path.exists(logs_dir):
                os.makedirs(logs_dir, exist_ok=True)
            
        super().__init__(config)
        
        # Required config
        self.base_url = config['base_url']
        self.model = config['model']

        self.stream = config.get('stream', False)
        
        self.logger.debug(f"[init]:Initialized Ollama service with model: {self.model}")
    
    def _generate_impl(self, prompt: str, options: Dict[str, Any], debug_generate_scope: str = "") -> str:
        """Generate a response using Ollama with performance tracking.
        
        Args:
            prompt: The input prompt
            options: Dictionary of generation options:
                    - temperature: float - Sampling temperature (0.0 to 1.0)
                    - ... other options are passed to the Ollama API
            debug_generate_scope: Optional scope identifier for debugging
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If the API call fails
        """
        import requests
        
        # Track overall LLM generation performance
        start_time = time.time()
        
        try:
            # Prepare request
            url = f"{self.base_url}/api/generate"

            # Build Ollama options dict (temperature, etc.)
            ollama_options = options.copy() if options else {}
            if 'temperature' not in ollama_options:
                ollama_options['temperature'] = self.default_temperature
            
            # Remove 'stream' from options if present (it's a top-level parameter)
            stream_value = ollama_options.pop('stream', self.stream)
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "options": ollama_options,
                "stream": stream_value
            }
            
            self.logger.debug(f"[{debug_generate_scope}]:Sending request to Ollama API:\nURL: {url}\nData: {json.dumps(data, indent=2)}")
            
            # Make request with timing
            request_start = time.time()
            try:
                response = requests.post(url, json=data)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                duration = time.time() - start_time
                self.logger.debug(f"[{debug_generate_scope}]:TIMING - Request failed after {duration:.3f}s: {str(e)}")
                raise LLMServiceError(f"Failed to make request to Ollama API: {str(e)}")
            
            request_duration = time.time() - request_start
            
            # Parse response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                duration = time.time() - start_time
                self.logger.debug(f"[{debug_generate_scope}]:TIMING - JSON parse failed after {duration:.3f}s: {str(e)}")
                raise LLMServiceError(f"Failed to parse Ollama API response: {str(e)}")
            
            # Extract and log timing metrics from Ollama response
            total_duration = time.time() - start_time
            ollama_metrics = {}
            
            if isinstance(result, dict):
                # Extract Ollama's internal timing metrics (in nanoseconds, convert to seconds)
                ollama_metrics = {
                    "total_duration": result.get("total_duration", 0) / 1e9,
                    "load_duration": result.get("load_duration", 0) / 1e9,
                    "prompt_eval_duration": result.get("prompt_eval_duration", 0) / 1e9,
                    "eval_duration": result.get("eval_duration", 0) / 1e9,
                    "prompt_eval_count": result.get("prompt_eval_count", 0),
                    "eval_count": result.get("eval_count", 0),
                    "network_duration": request_duration
                }
                
                # Calculate tokens per second
                if ollama_metrics["eval_duration"] > 0 and ollama_metrics["eval_count"] > 0:
                    ollama_metrics["tokens_per_second"] = ollama_metrics["eval_count"] / ollama_metrics["eval_duration"]
                else:
                    ollama_metrics["tokens_per_second"] = 0
            
            # Clean up context data before logging
            debug_result = result.copy()
            if 'context' in debug_result:
                del debug_result['context']
            
            # Enhanced logging with performance metrics
            self.logger.debug(f"[{debug_generate_scope}]:Received response from Ollama API:\n{json.dumps(debug_result, indent=2)}")
            self.logger.debug(f"[{debug_generate_scope}]:TIMING BREAKDOWN - "
                            f"Total: {total_duration:.3f}s, "
                            f"Ollama Total: {ollama_metrics.get('total_duration', 0):.3f}s, "
                            f"Model Load: {ollama_metrics.get('load_duration', 0):.3f}s, "
                            f"Prompt Eval: {ollama_metrics.get('prompt_eval_duration', 0):.3f}s ({ollama_metrics.get('prompt_eval_count', 0)} tokens), "
                            f"Generation: {ollama_metrics.get('eval_duration', 0):.3f}s ({ollama_metrics.get('eval_count', 0)} tokens), "
                            f"Network: {ollama_metrics.get('network_duration', 0):.3f}s, "
                            f"Tokens/sec: {ollama_metrics.get('tokens_per_second', 0):.1f}")
            
            if not isinstance(result, dict) or 'response' not in result:
                raise LLMServiceError("Invalid response format from Ollama API")
            
            return result['response']
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.debug(f"[{debug_generate_scope}]:TIMING - Error after {duration:.3f}s: {str(e)}")
            
            if not isinstance(e, LLMServiceError):
                raise LLMServiceError(f"Unexpected error in Ollama API call: {str(e)}")
            raise

    def validate_response(self, response: str) -> bool:
        """Validate the Ollama response.
        
        Args:
            response: The response to validate
            
        Returns:
            bool: True if response is valid (non-empty string)
        """
        is_valid = isinstance(response, str) and len(response.strip()) > 0
        self.logger.error(f"Invalid response format: {response}")
        return is_valid

    async def _generate_impl_async(self, prompt: str, options: Dict[str, Any], debug_generate_scope: str = "") -> str:
        """Generate a response using Ollama asynchronously with performance tracking.
        
        Args:
            prompt: The input prompt
            options: Dictionary of generation options:
                    - temperature: float - Sampling temperature (0.0 to 1.0)
                    - stream: bool - Whether to stream the response
            debug_generate_scope: Optional scope identifier for debugging
            
        Returns:
            str: The generated response
            
        Raises:
            LLMServiceError: If the API call fails
        """
        import httpx
        import json
        import time
        
        # Track overall LLM generation performance
        start_time = time.time()
        
        try:
            # Prepare request
            url = f"{self.base_url}/api/generate"
            
            # Use options to override defaults - enable streaming by default for better progress monitoring
            use_streaming = options.get("stream", True)  # Default to streaming for async calls
            request_data = {
                "model": options.get("model", self.model),
                "prompt": prompt,
                "stream": use_streaming,
                "options": {
                    "temperature": options.get("temperature", self.default_temperature)
                }
            }
            
            self.logger.debug(f"[{debug_generate_scope}]:🚀 Starting Ollama request - {url}")
            self.logger.debug(f"[{debug_generate_scope}]:📋 Request: {request_data['model']}, streaming={use_streaming}, prompt={len(prompt)} chars")
            if len(prompt) < 200:
                self.logger.debug(f"[{debug_generate_scope}]:💬 Prompt: {prompt}")
            else:
                self.logger.debug(f"[{debug_generate_scope}]:💬 Prompt preview: {prompt[:200]}...")
            
            # Make async HTTP request with retry logic and better timeout configuration
            timeout = httpx.Timeout(
                timeout=300.0,  # 5 minute timeout
                connect=30.0,   # 30 second connect timeout
                read=300.0,     # 5 minute read timeout
                write=60.0      # 1 minute write timeout
            )
            
            # Retry up to 3 times for connection issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        if use_streaming:
                            # Streaming request with progress monitoring
                            connect_start = time.time()
                            self.logger.debug(f"[{debug_generate_scope}]:⏳ Connecting to Ollama (may queue if server busy)...")
                            
                            response_text = ""
                            last_progress_time = time.time()
                            
                            async with client.stream('POST', url, json=request_data) as response:
                                response.raise_for_status()
                                
                                connect_time = time.time() - connect_start
                                self.logger.debug(f"[{debug_generate_scope}]:✅ Connected! (waited {connect_time:.1f}s) Starting stream...")
                                
                                chunk_count = 0
                                async for chunk in response.aiter_text():
                                    if chunk.strip():
                                        chunk_count += 1
                                        try:
                                            chunk_data = json.loads(chunk.strip())
                                            if "response" in chunk_data:
                                                response_text += chunk_data["response"]
                                            
                                            # Progress logging every 2 seconds or every 20 chunks
                                            current_time = time.time()
                                            if (chunk_count % 20 == 0 or 
                                                current_time - last_progress_time > 2.0):
                                                elapsed = current_time - start_time
                                                rate = len(response_text) / elapsed if elapsed > 0 else 0
                                                self.logger.debug(f"[{debug_generate_scope}]:📊 Progress: {len(response_text)} chars ({rate:.0f} chars/s), {chunk_count} chunks, {elapsed:.1f}s")
                                                last_progress_time = current_time
                                            
                                            # Check if done
                                            if chunk_data.get("done", False):
                                                elapsed = time.time() - start_time
                                                rate = len(response_text) / elapsed if elapsed > 0 else 0
                                                self.logger.debug(f"[{debug_generate_scope}]:✅ Streaming complete! {len(response_text)} chars in {elapsed:.1f}s ({rate:.0f} chars/s)")
                                                break
                                                
                                        except json.JSONDecodeError:
                                            # Skip invalid JSON chunks
                                            continue
                            
                            if not response_text:
                                raise LLMServiceError("No response received from Ollama streaming API")
                            
                            return response_text
                            
                        else:
                            # Non-streaming request (original behavior)
                            response = await client.post(url, json=request_data)
                            response.raise_for_status()
                            
                            response_data = response.json()
                            
                            self.logger.debug(f"[{debug_generate_scope}]:Received non-streaming response from Ollama")
                            
                            if "response" not in response_data:
                                raise LLMServiceError("Invalid response format from Ollama API")
                            
                            return response_data["response"]
                        
                except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        self.logger.debug(f"[{debug_generate_scope}]:Connection error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Re-raise on final attempt
                        raise
                
        except httpx.RequestError as e:
            raise LLMServiceError(f"Ollama async API request error: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise LLMServiceError(f"Ollama async API HTTP error: {e.response.status_code}")
        except Exception as e:
            raise LLMServiceError(f"Ollama async API error: {str(e)}")
            
        finally:
            total_time = time.time() - start_time
            self.logger.debug(f"[{debug_generate_scope}]:🏁 Total async LLM generation time: {total_time:.1f}s")

    def _generate_embedding_impl(self, text: str, options: Dict[str, Any]) -> List[float]:
        """Generate an embedding vector using Ollama.
        
        Args:
            text: The text to generate an embedding for
            options: Dictionary of embedding options:
                    - model: str - Specific embedding model to use (defaults to self.model)
                    - normalize: bool - Whether to normalize the embedding vector
            
        Returns:
            List[float]: The embedding vector
            
        Raises:
            LLMServiceError: If the API call fails
        """
        import requests
        
        try:
            # Prepare request
            url = f"{self.base_url}/api/embeddings"
            data = {
                "model": options.get('model', self.model),
                "prompt": text
            }
            
            self.logger.debug(f"[embedding]:Sending request to Ollama API:\nURL: {url}\nData: {json.dumps(data, indent=2)}")
            
            # Make request
            try:
                response = requests.post(url, json=data)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise LLMServiceError(f"Failed to make request to Ollama API: {str(e)}")
            
            # Parse response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                raise LLMServiceError(f"Failed to parse Ollama API response: {str(e)}")
            
            if not isinstance(result, dict) or 'embedding' not in result:
                raise LLMServiceError("Invalid response format from Ollama API")
            
            embedding = result['embedding']
            
            # Normalize if requested
            if options.get('normalize', True):
                embedding = np.array(embedding)
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = (embedding / norm).tolist()
            
            return embedding
            
        except Exception as e:
            if not isinstance(e, LLMServiceError):
                raise LLMServiceError(f"Unexpected error in Ollama API call: {str(e)}")
            raise
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate the Ollama embedding vector.
        
        Args:
            embedding: The embedding vector to validate
            
        Returns:
            bool: True if embedding is valid (non-empty list of floats)
        """
        is_valid = (
            isinstance(embedding, list) and 
            len(embedding) > 0 and 
            all(isinstance(x, (int, float)) for x in embedding)
        )
        self.logger.error(f"Invalid embedding format: {embedding}")
        return is_valid
