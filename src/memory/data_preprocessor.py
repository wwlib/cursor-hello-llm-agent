import os
import json
import re
from typing import List, Optional, Tuple
import logging
from .content_segmenter import ContentSegmenter

class DataPreprocessor:
    """Transforms structured or unstructured world data into embeddable phrases using LLM and a prompt template."""

    def __init__(self, llm_service, logger=None):
        """Initialize the DataPreprocessor.
        
        Args:
            llm_service: Service for LLM operations
            logger: Logger instance for logging
        """
        self.llm = llm_service
        self.logger = logger or logging.getLogger(__name__)
        self._load_templates()
        self.segmenter = ContentSegmenter(llm_service, self.logger)

    def _load_templates(self) -> None:
        """Load the preprocess_data prompt template from file."""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        try:
            with open(os.path.join(template_dir, "preprocess_data.prompt"), 'r') as f:
                self.preprocess_template = f.read().strip()
            self.logger.debug("Loaded preprocess_data template")
        except Exception as e:
            self.logger.error(f"Error loading preprocess_data template: {str(e)}")
            raise Exception("Failed to load preprocess_data template")

    def preprocess_data(self, input_data: str) -> Tuple[str, List[str]]:
        """Turn input data into embeddable phrases using the LLM and the preprocess_data prompt.
        
        Args:
            input_data: The structured or unstructured text to process
        
        Returns:
            Tuple[str, List[str]]: (prose, segments)
        """
        try:
            if not input_data or not input_data.strip():
                return ("", [])

            prompt = self.preprocess_template.format(input_data=input_data)
            prose = self.llm.generate(
                prompt,
                options={
                    "temperature": 0,  # Consistent, deterministic output
                    "stream": False
                },
                debug_generate_scope="data_preprocessing"
            )

            segments = self.segmenter.segment_content(prose)
            return (prose, segments)
        except Exception as e:
            self.logger.error(f"Error in data preprocessing: {str(e)}")
            return (input_data, [input_data])
