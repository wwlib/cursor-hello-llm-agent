from typing import Dict, Any, Optional, List
import json
import logging
import time

class LLMServiceError(Exception):
    """Custom exception for LLM service errors"""
    pass

class LLMService:
    """Base class for LLM service providers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the LLM service.
        
        Args:
            config: Configuration dictionary with service settings
                   Required fields depend on specific implementation
                   Optional fields:
                   - debug: bool - Enable debug logging
                   - debug_file: str - Path to debug log file
                   - debug_scope: str - Scope identifier for debug logs
                   - console_output: bool - Whether to also log to console
        """
        self.config = config or {}
        self.debug = self.config.get('debug', False)
        self.debug_scope = self.config.get('debug_scope', 'llm')
        self.debug_file = self.config.get('debug_file')
        self.console_output = self.config.get('console_output', False)
        
        # Set up logging if debug is enabled
        if self.debug:
            import logging
            
            # Create logger
            self.logger = logging.getLogger(f'llm_service:{self.debug_scope}')
            self.logger.setLevel(logging.DEBUG)
            self.logger.propagate = False  # Prevent propagation to root logger
            
            # Create formatters
            scope_prefix = f'[{self.debug_scope}]' if self.debug_scope else ''
            file_formatter = logging.Formatter(f'{scope_prefix}:[%(funcName)s]:%(message)s')
            console_formatter = logging.Formatter(f'{scope_prefix}:[%(funcName)s]:%(message)s')
            
            # Add file handler if debug_file specified
            if 'debug_file' in config:
                file_handler = logging.FileHandler(config['debug_file'])
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            
            # Add console handler if requested
            if config.get('console_output', False):
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)
            
            self.logger.debug(f":[init]:LLM service initialized with debug logging")
    
    def _clean_response(self, llm_response: str) -> str:
        """Clean up special characters and Unicode escape sequences from LLM response.
        
        Args:
            response: The raw response from the LLM
            
        Returns:
            str: Cleaned response with normalized characters
        """
        if not llm_response:
            return llm_response
            
        try:
            # Comprehensive dictionary of Unicode replacements
            replacements = {
                '\u2013': '-',  # en-dash
                '\u2014': '--', # em-dash
                '\u2018': "'",  # left single quote
                '\u2019': "'",  # right single quote
                '\u201c': '"',  # left double quote
                '\u201d': '"',  # right double quote
                '\u2026': '...', # ellipsis
                '\u00a0': ' ',  # non-breaking space
                '\u00b0': ' degrees', # degree symbol
                '\u00b7': '.',  # middle dot
                '\u00e9': 'e',  # e with acute
                '\u00e8': 'e',  # e with grave
                '\u00e0': 'a',  # a with grave
                '\u00e1': 'a',  # a with acute
                '\u00e2': 'a',  # a with circumflex
                '\u00e4': 'a',  # a with diaeresis
                '\u00e7': 'c',  # c with cedilla
                '\u00f1': 'n',  # n with tilde
                '\u00f3': 'o',  # o with acute
                '\u00f6': 'o',  # o with diaeresis
                '\u00fa': 'u',  # u with acute
                '\u00fc': 'u',  # u with diaeresis
            }

            # Apply all replacements
            cleaned = llm_response
            for unicode_char, ascii_char in replacements.items():
                cleaned = cleaned.replace(unicode_char, ascii_char)
            
            return cleaned
            
        except Exception as e:
            if self.debug:
                self.logger.warning(f"Error cleaning response: {str(e)}")
            return llm_response  # Return original response if cleaning fails
    
    def generate(self, prompt: str, options: Optional[Dict[str, Any]] = None, debug_generate_scope: str = "") -> str:
        """Generate a response for the given prompt.
        
        Args:
            prompt: The input prompt
            options: Optional dictionary of generation options:
                    - temperature: float - Sampling temperature (0.0 to 1.0)
                    - max_tokens: int - Maximum tokens to generate
                    - stream: bool - Whether to stream the response
            debug_generate_scope: Optional scope identifier for this specific generate call
            
        Returns:
            str: The generated response
        """
        if self.debug:
            self.logger.debug(f":[{debug_generate_scope}]:Generating response for prompt:\n{prompt}")
            if options:
                self.logger.debug(f":[{debug_generate_scope}]:Generation options:\n{json.dumps(options, indent=2)}")
        
        try:
            response = self._generate_impl(prompt, options or {}, debug_generate_scope)
            
            # Clean the response
            cleaned_response = self._clean_response(response)
            
            if self.debug:
                self.logger.debug(f":[{debug_generate_scope}]:Generated response:\n{response}\n\n\n\n\n")
            
            return cleaned_response
            
        except Exception as e:
            if self.debug:
                self.logger.debug(f":[{debug_generate_scope}]:Error generating response: {str(e)}")
            raise
    
    def _generate_impl(self, prompt: str, options: Dict[str, Any], debug_generate_scope: str = "") -> str:
        """Implementation specific generation logic.
        Must be implemented by derived classes.
        
        Args:
            prompt: The input prompt
            options: Dictionary of generation options
            debug_generate_scope: Optional scope identifier for debugging
            
        Returns:
            str: The generated response
        """
        raise NotImplementedError("_generate_impl must be implemented by derived class")
    
    def validate_response(self, response: str) -> bool:
        """Validate LLM response format.
        
        Args:
            response: The response to validate
            
        Returns:
            bool: True if response is valid, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def generate_embedding(self, text: str, options: Optional[Dict[str, Any]] = None) -> List[float]:
        """Generate an embedding vector for the given text.
        
        Args:
            text: The text to generate an embedding for
            options: Optional dictionary of embedding options:
                    - model: str - Specific embedding model to use
                    - normalize: bool - Whether to normalize the embedding vector
            
        Returns:
            List[float]: The embedding vector
            
        Raises:
            LLMServiceError: If embedding generation fails
        """
        if self.debug:
            self.logger.debug(f":[embedding]:Generating embedding for text:\n{text}")
            if options:
                self.logger.debug(f":[embedding]:Embedding options:\n{json.dumps(options, indent=2)}")
        
        try:
            embedding = self._generate_embedding_impl(text, options or {})
            
            if self.debug:
                self.logger.debug(f":[embedding]:Generated embedding vector of length {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            if self.debug:
                self.logger.debug(f":[embedding]:Error generating embedding: {str(e)}")
            raise LLMServiceError(f"Failed to generate embedding: {str(e)}")
    
    def _generate_embedding_impl(self, text: str, options: Dict[str, Any]) -> List[float]:
        """Implementation specific embedding generation logic.
        Must be implemented by derived classes.
        
        Args:
            text: The text to generate an embedding for
            options: Dictionary of embedding options
            
        Returns:
            List[float]: The embedding vector
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("_generate_embedding_impl must be implemented by derived class")
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate embedding vector format.
        
        Args:
            embedding: The embedding vector to validate
            
        Returns:
            bool: True if embedding is valid, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError
