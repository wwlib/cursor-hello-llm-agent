import json
import uuid
import re
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

class DigestGenerator:
    """Handles the process of generating structured digests from conversation entries.
    
    The DigestGenerator implements a two-step process:
    1. Segment the conversation content into meaningful chunks
    2. Rate each segment's importance and assign topics
    
    This allows for memory compression while maintaining text in a format 
    natural for LLMs to process.
    """
    
    def __init__(self, llm_service):
        """Initialize the DigestGenerator.
        
        Args:
            llm_service: Service for LLM operations
        """
        self.llm = llm_service
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load prompt templates from files"""
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = {}
        
        template_files = {
            "segment": "segment_conversation.prompt",
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
    
    def generate_digest(self, conversation_entry: Dict[str, Any], memory_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a digest from a conversation entry by segmenting and rating importance.
        
        Args:
            conversation_entry: Dictionary containing the conversation entry with role, content, etc.
            memory_state: Optional current memory state for context
            
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
            
            # Step 1: Segment the content
            segments = self._segment_content(content)
            
            print(f"\n\ngenerate_digest: Segments:")
            for segment in segments:
                print(segment)
            print(f"\n\n")
            
            # Step 2: Rate segments and assign topics
            rated_segments = self._rate_segments(segments, memory_state)
            
            # Combine into final digest
            digest = {
                "conversation_history_entry_guid": entry_guid,
                "role": conversation_entry.get("role", "unknown"),
                "rated_segments": rated_segments,
                "timestamp": datetime.now().isoformat()
            }
            
            return digest
            
        except Exception as e:
            print(f"Error generating digest: {str(e)}")
            return self._create_empty_digest(entry_guid if entry_guid else str(uuid.uuid4()), 
                                            conversation_entry.get("role", "unknown"))
    
    def _segment_content(self, content: str) -> List[str]:
        """Segment the content into meaningful phrases using LLM.
        
        Args:
            content: The text content to segment
            
        Returns:
            list: A list of segmented phrases
        """
        try:
            # Format the prompt with the content
            prompt = self.templates["segment"].format(content=content)
            
            # Call LLM to segment the content
            llm_response = self.llm.generate(prompt)
            
            # Parse the response as JSON array
            try:
                segments = json.loads(llm_response)
                if not isinstance(segments, list):
                    print("Segmentation failed: Response is not a list")
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
                print("Failed to parse segments, using entire content")
                return [content]
                
        except Exception as e:
            print(f"Error in content segmentation: {str(e)}")
            return [content]  # Fall back to using the entire content as a single segment
    
    def _rate_segments(self, segments: List[str], memory_state: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Rate segments for importance and assign topics using LLM.
        
        Args:
            segments: List of segmented phrases
            memory_state: Optional current memory state for context
            
        Returns:
            list: List of rated segments with importance and topics
        """
        try:
            # Format the prompt with the segments and memory state
            memory_context = "" if memory_state is None else json.dumps(memory_state.get("context", ""), indent=2)
            prompt = self.templates["rate"].format(
                segments=json.dumps(segments),
                memory_context=memory_context
            )
            
            # Call LLM to rate segments
            llm_response = self.llm.generate(prompt)
            
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
                            "topics": []
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
                                    "topics": []
                                }
                        
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
                "topics": []
            }
            for segment in segments
        ] 