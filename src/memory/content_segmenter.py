"""Content Segmenter for Agent System

This module provides functionality for segmenting text content into meaningful chunks.
The ContentSegmenter uses LLM to intelligently break down text while preserving context
and maintaining the original meaning.

Design Principles::

    1. Separation of Concerns
       - Focused solely on text segmentation
       - Clear interface for segmentation operations
       - Robust error handling and fallback mechanisms

    2. Quality Segmentation
       - Preserves context between related ideas
       - Maintains complete coverage of input text
       - Handles different types of content appropriately

    3. Error Recovery
       - Graceful degradation when segmentation fails
       - Fallback to simpler segmentation methods
       - Comprehensive validation of results
"""

from typing import List, Optional
import json
import re
import os
import logging

class ContentSegmenter:
    """Handles segmentation of text content into meaningful chunks."""
    
    def __init__(self, llm_service, logger=None):
        """Initialize the ContentSegmenter.
        
        Args:
            llm_service: Service for LLM operations
            logger: Logger instance for logging
        """
        self.llm = llm_service
        self.logger = logger or logging.getLogger(__name__)
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load prompt templates from files"""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        try:
            with open(os.path.join(template_dir, "segment_conversation.prompt"), 'r') as f:
                self.segment_template = f.read().strip()
            self.logger.debug("Loaded segmentation template")
        except Exception as e:
            self.logger.error(f"Error loading segmentation template: {str(e)}")
            raise Exception("Failed to load segmentation template")
    
    def segment_content(self, content: str) -> List[str]:
        """Segment the content into meaningful phrases using LLM.
        
        Args:
            content: The text content to segment
            
        Returns:
            list: A list of segmented phrases. Returns an empty list if input is empty.
        """
        try:
            # Return empty list for empty input
            if not content or not content.strip():
                return []
            
            # Format the prompt with the content
            prompt = self.segment_template.format(content=content)
            
            # Call LLM to segment the content with explicit options
            llm_response = self.llm.generate(
                prompt,
                options={
                    "temperature": 0,  # Lower temperature for more consistent segmentation
                    "stream": False  # Ensure streaming is off
                },
                debug_generate_scope="content_segmentation"
            )
            
            # Parse the response as JSON array
            try:
                segments = json.loads(llm_response)
                if not isinstance(segments, list):
                    self.logger.debug("Segmentation failed: Response is not a list")
                    return [content]  # Fall back to using the entire content as a single segment
                return segments
            except json.JSONDecodeError:
                # Try to extract JSON array if it's embedded in markdown or other text
                segments_match = re.search(r'\[\s*".*"\s*(?:,\s*".*"\s*)*\]', llm_response, re.DOTALL)
                if segments_match:
                    try:
                        segments = json.loads(segments_match.group(0))
                        return segments
                    except json.JSONDecodeError:
                        pass
                
                # Fall back to using the entire content as a single segment
                self.logger.debug("Failed to parse segments, using entire content")
                return [content]
                
        except Exception as e:
            self.logger.error(f"Error in content segmentation: {str(e)}")
            return [content]  # Fall back to using the entire content as a single segment 