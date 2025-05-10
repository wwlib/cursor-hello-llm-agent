import json
import uuid
import re
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from .content_segmenter import ContentSegmenter
import logging

class DigestGenerator:
    """Handles the process of generating structured digests from conversation entries.
    
    The DigestGenerator implements a two-step process:
    1. Segment the conversation content into meaningful chunks
    2. Rate each segment's importance and assign topics
    
    This allows for memory compression while maintaining text in a format 
    natural for LLMs to process.
    """
    
    def __init__(self, llm_service, logger=None):
        """Initialize the DigestGenerator.
        
        Args:
            llm_service: Service for LLM operations
            logger: Optional logger instance
        """
        self.llm = llm_service
        self.logger = logger or logging.getLogger(__name__)
        self.content_segmenter = ContentSegmenter(llm_service)
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load prompt templates from files"""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = {}
        
        template_files = {
            "rate": "rate_segments.prompt"
        }
        
        for key, filename in template_files.items():
            path = os.path.join(template_dir, filename)
            try:
                with open(path, 'r') as f:
                    self.templates[key] = f.read().strip()
                print(f"Loaded digest template: {filename}")
            except Exception as e:
                print(f"Error loading digest template {filename}: {str(e)}")
                # Raise an exception if the template cannot be loaded
                raise Exception(f"Failed to load template: {filename}")
    
    def generate_digest(self, conversation_entry: Dict[str, Any], memory_state: Optional[Dict[str, Any]] = None, segments: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate a digest from a conversation entry by segmenting and rating importance.
        
        Args:
            conversation_entry: Dictionary containing the conversation entry with role, content, etc.
            memory_state: Optional current memory state for context
            segments: Optional list of pre-segmented content strings. If provided, skips segmentation step.
            
        Returns:
            dict: A digest containing rated and topically organized text segments
        """
        try:
            entry_guid = conversation_entry.get("guid")
            if not entry_guid:
                # Generate a GUID if not present
                entry_guid = str(uuid.uuid4())
                conversation_entry["guid"] = entry_guid
            
            content = conversation_entry.get("content", "")
            if not content.strip():
                print("Warning: Empty content in conversation entry")
                return self._create_empty_digest(entry_guid, conversation_entry.get("role", "unknown"))
            
            # Step 1: Use provided segments or segment the content
            if segments is not None:
                segments_to_use = segments
            else:
                segments_to_use = self.content_segmenter.segment_content(content)
            
            # Print number of segments generated
            print(f"Generated {len(segments_to_use)} segments")
            # print(f"\n\ngenerate_digest: Segments:")
            # for segment in segments_to_use:
            #     print(segment)
            # print(f"\n\n")

            # print(f"\n\ngenerate_digest: Memory state: static_memory")
            # static_memory = "" if memory_state is None else memory_state.get("static_memory", "")
            # print(static_memory)
            # print(f"\n\n")
            
            # Step 2: Rate segments and assign topics
            rated_segments = self._rate_segments(segments_to_use, memory_state)
            
            # Step 3: Clean the rated segments
            cleaned_segments = self._clean_segments(rated_segments)
            
            # Combine into final digest
            digest = {
                "conversation_history_entry_guid": entry_guid,
                "role": conversation_entry.get("role", "unknown"),
                "rated_segments": cleaned_segments,
                "timestamp": datetime.now().isoformat()
            }
            
            return digest
            
        except Exception as e:
            print(f"Error generating digest: {str(e)}")
            return self._create_empty_digest(entry_guid if entry_guid else str(uuid.uuid4()), 
                                            conversation_entry.get("role", "unknown"))
    
    def _rate_segments(self, segments: List[str], memory_state: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Rate segments for importance and assign topics using LLM.
        
        Args:
            segments: List of segmented phrases
            memory_state: Optional current memory state for context
            
        Returns:
            list: List of rated segments with importance, topics, and type
        """
        try:
            # Format the prompt with the segments and memory state
            static_memory = "" if memory_state is None else memory_state.get("static_memory", "")
            memory_context = "" if memory_state is None else json.dumps(memory_state.get("context", ""), indent=2)
            prompt = self.templates["rate"].format(
                segments=json.dumps(segments),
                static_memory=static_memory,
                memory_context=memory_context
            )
            
            # Call LLM to rate segments with explicit options
            llm_response = self.llm.generate(
                prompt, 
                options={
                    "temperature": 0,  # Lower temperature for more consistent ratings
                    "stream": False  # Ensure streaming is off
                },
                debug_generate_scope="segment_rating"
            )
            
            # Parse the response as JSON
            try:
                rated_segments = json.loads(llm_response)
                # Validate the structure
                if not isinstance(rated_segments, list):
                    print("Rating failed: Response is not a list")
                    return self._create_default_rated_segments(segments)
                
                # Validate each rated segment
                for i, segment in enumerate(rated_segments):
                    if not isinstance(segment, dict):
                        print(f"Segment {i} is not a dictionary, using default")
                        rated_segments[i] = {
                            "text": segments[i] if i < len(segments) else "",
                            "importance": 3,
                            "topics": [],
                            "type": "information"  # Default type
                        }
                    elif "text" not in segment:
                        print(f"Segment {i} missing text, using original")
                        segment["text"] = segments[i] if i < len(segments) else ""
                    elif "importance" not in segment:
                        print(f"Segment {i} missing importance, using default")
                        segment["importance"] = 3
                    elif "topics" not in segment:
                        print(f"Segment {i} missing topics, using empty list")
                        segment["topics"] = []
                    elif "type" not in segment:
                        print(f"Segment {i} missing type, using default")
                        segment["type"] = "information"
                    elif segment["type"] not in ["query", "information", "action", "command"]:
                        print(f"Segment {i} has invalid type, using default")
                        segment["type"] = "information"
                
                return rated_segments
            except json.JSONDecodeError:
                # Try to extract JSON if it's embedded in markdown or other text
                json_match = re.search(r'\[[\s\S]*\]', llm_response)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        # Remove any markdown code block markers
                        json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                        rated_segments = json.loads(json_str)
                        
                        # Do basic validation
                        if not isinstance(rated_segments, list):
                            print("Extracted rating is not a list")
                            return self._create_default_rated_segments(segments)
                        
                        # Validate each segment has required fields
                        for i, segment in enumerate(rated_segments):
                            if not isinstance(segment, dict) or "text" not in segment:
                                print(f"Segment {i} invalid, using default")
                                rated_segments[i] = {
                                    "text": segments[i] if i < len(segments) else "",
                                    "importance": 3,
                                    "topics": [],
                                    "type": "information"  # Default type
                                }
                            elif "type" not in segment or segment["type"] not in ["query", "information", "action", "command"]:
                                print(f"Segment {i} has invalid type, using default")
                                segment["type"] = "information"
                        
                        return rated_segments
                    except json.JSONDecodeError:
                        pass
                
                # Fall back to default rating
                print("Failed to parse rated segments, using defaults")
                return self._create_default_rated_segments(segments)
                
        except Exception as e:
            print(f"Error in segment rating: {str(e)}")
            return self._create_default_rated_segments(segments)
    
    def _create_empty_digest(self, entry_guid: str, role: str) -> Dict[str, Any]:
        """Create an empty digest structure with the given entry GUID."""
        return {
            "conversation_history_entry_guid": entry_guid,
            "role": role,
            "rated_segments": [],
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_default_rated_segments(self, segments: List[str]) -> List[Dict[str, Any]]:
        """Create default rated segments with medium importance."""
        return [
            {
                "text": segment,
                "importance": 3,  # Medium importance by default
                "topics": [],
                "type": "information"  # Default type
            }
            for segment in segments
        ]

    def _clean_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and validate segments.
        
        Args:
            segments: List of segment dictionaries
            
        Returns:
            List[Dict[str, Any]]: Cleaned segments
        """
        cleaned_segments = []
        
        for segment in segments:            
            # Ensure importance is an integer between 1-5
            if "importance" in segment:
                try:
                    importance = int(segment["importance"])
                    segment["importance"] = max(1, min(5, importance))
                except (ValueError, TypeError):
                    segment["importance"] = 3  # Default to middle importance
            
            # Ensure topics is a list of strings
            if "topics" in segment:
                if not isinstance(segment["topics"], list):
                    segment["topics"] = []
                segment["topics"] = [str(topic).strip() for topic in segment["topics"] if topic]
            else:
                segment["topics"] = []
            
            # Ensure type is valid
            if "type" not in segment or segment["type"] not in ["query", "information", "action", "command"]:
                segment["type"] = "information"  # Default to information if invalid
            
            cleaned_segments.append(segment)
        
        return cleaned_segments 