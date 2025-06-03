import json
import uuid
import re
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from .content_segmenter import ContentSegmenter
from .topic_taxonomy import TopicTaxonomy
import logging

class DigestGenerator:
    """Handles the process of generating structured digests from conversation entries.
    
    The DigestGenerator implements a two-step process:
    1. Segment the conversation content into meaningful chunks
    2. Rate each segment's importance and assign topics
    
    This allows for memory compression while maintaining text in a format 
    natural for LLMs to process.
    """
    
    def __init__(self, llm_service, domain_name: str = "general", domain_config=None, logger=None):
        """Initialize the DigestGenerator.
        
        Args:
            llm_service: Service for LLM operations
            domain_name: Domain name for topic taxonomy (e.g., 'dnd_campaign', 'lab_assistant')
            domain_config: Optional domain configuration dictionary
            logger: Optional logger instance
        """
        self.llm = llm_service
        self.logger = logger or logging.getLogger(__name__)
        self.domain_name = domain_name
        self.content_segmenter = ContentSegmenter(llm_service, self.logger)
        self.topic_taxonomy = TopicTaxonomy(domain_name, domain_config, self.logger)
        self._load_templates()
        self.logger.debug(f"Initialized DigestGenerator for domain: {domain_name}")
    
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
                self.logger.debug(f"Loaded digest template: {filename}")
            except Exception as e:
                self.logger.error(f"Error loading digest template {filename}: {str(e)}")
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
                self.logger.debug("Warning: Empty content in conversation entry")
                return self._create_empty_digest(entry_guid, conversation_entry.get("role", "unknown"))
            
            # Step 1: Use provided segments or segment the content
            if segments is not None:
                segments_to_use = segments
            else:
                segments_to_use = self.content_segmenter.segment_content(content)
            
            # Print number of segments generated
            self.logger.debug(f"Generated {len(segments_to_use)} segments")
            
            # Step 2: Rate segments and assign topics
            rated_segments = self._rate_segments(segments_to_use, memory_state)
            
            # Step 2.5: Filter out non-memory-worthy segments
            memory_worthy_segments = self._filter_memory_worthy_segments(rated_segments)
            
            # Step 3: Clean the rated segments
            cleaned_segments = self._clean_segments(memory_worthy_segments)
            
            # Combine into final digest
            digest = {
                "conversation_history_entry_guid": entry_guid,
                "role": conversation_entry.get("role", "unknown"),
                "rated_segments": cleaned_segments,
                "timestamp": datetime.now().isoformat()
            }
            
            return digest
            
        except Exception as e:
            self.logger.error(f"Error generating digest: {str(e)}")
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
            
            # Add domain-specific topic guidance
            topic_guidance = self.topic_taxonomy.get_domain_prompt_guidance()
            
            prompt = self.templates["rate"].format(
                segments=json.dumps(segments),
                static_memory=static_memory,
                memory_context=memory_context,
                topic_guidance=topic_guidance
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
                    self.logger.debug("Rating failed: Response is not a list")
                    return self._create_default_rated_segments(segments)
                
                # Validate each rated segment
                for i, segment in enumerate(rated_segments):
                    if not isinstance(segment, dict):
                        self.logger.debug(f"Segment {i} is not a dictionary, using default")
                        rated_segments[i] = {
                            "text": segments[i] if i < len(segments) else "",
                            "importance": 3,
                            "topics": [],
                            "type": "information"  # Default type
                        }
                    elif "text" not in segment:
                        self.logger.debug(f"Segment {i} missing text, using original")
                        segment["text"] = segments[i] if i < len(segments) else ""
                    elif "importance" not in segment:
                        self.logger.debug(f"Segment {i} missing importance, using default")
                        segment["importance"] = 3
                    elif "topics" not in segment:
                        self.logger.debug(f"Segment {i} missing topics, using empty list")
                        segment["topics"] = []
                    elif "type" not in segment:
                        self.logger.debug(f"Segment {i} missing type, using default")
                        segment["type"] = "information"
                    elif segment["type"] not in ["query", "information", "action", "command"]:
                        self.logger.debug(f"Segment {i} has invalid type, using default")
                        segment["type"] = "information"
                    elif "memory_worthy" not in segment:
                        self.logger.debug(f"Segment {i} missing memory_worthy, using default")
                        segment["memory_worthy"] = True
                
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
                            self.logger.debug("Extracted rating is not a list")
                            return self._create_default_rated_segments(segments)
                        
                        # Validate each segment has required fields
                        for i, segment in enumerate(rated_segments):
                            if not isinstance(segment, dict) or "text" not in segment:
                                self.logger.debug(f"Segment {i} invalid, using default")
                                rated_segments[i] = {
                                    "text": segments[i] if i < len(segments) else "",
                                    "importance": 3,
                                    "topics": [],
                                    "type": "information",  # Default type
                                    "memory_worthy": True   # Default to memory worthy
                                }
                            elif "type" not in segment or segment["type"] not in ["query", "information", "action", "command"]:
                                self.logger.debug(f"Segment {i} has invalid type, using default")
                                segment["type"] = "information"
                            elif "memory_worthy" not in segment:
                                self.logger.debug(f"Segment {i} missing memory_worthy, using default")
                                segment["memory_worthy"] = True
                        
                        return rated_segments
                    except json.JSONDecodeError:
                        pass
                
                # Fall back to default rating
                self.logger.debug("Failed to parse rated segments, using defaults")
                return self._create_default_rated_segments(segments)
                
        except Exception as e:
            self.logger.error(f"Error in segment rating: {str(e)}")
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
                "type": "information",  # Default type
                "memory_worthy": True   # Default to memory worthy
            }
            for segment in segments
        ]

    def _filter_memory_worthy_segments(self, rated_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out non-memory-worthy segments before storage.
        
        Args:
            rated_segments: List of segments with memory_worthy field
            
        Returns:
            List[Dict[str, Any]]: Only segments marked as memory_worthy
        """
        memory_worthy = []
        excluded_count = 0
        
        for segment in rated_segments:
            if segment.get("memory_worthy", True):  # Default to True for safety
                memory_worthy.append(segment)
            else:
                excluded_count += 1
                self.logger.debug(f"Excluded non-memory-worthy segment: {segment.get('text', '')[:50]}...")
        
        self.logger.debug(f"Filtered out {excluded_count} non-memory-worthy segments, kept {len(memory_worthy)} segments")
        return memory_worthy

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
            
            # Ensure topics is a list of strings and normalize them
            if "topics" in segment:
                if not isinstance(segment["topics"], list):
                    segment["topics"] = []
                # Clean and normalize topics
                raw_topics = [str(topic).strip() for topic in segment["topics"] if topic]
                segment["topics"] = self.topic_taxonomy.normalize_topics(raw_topics)
            else:
                segment["topics"] = []
            
            # Ensure type is valid
            if "type" not in segment or segment["type"] not in ["query", "information", "action", "command"]:
                segment["type"] = "information"  # Default to information if invalid
            
            # Ensure memory_worthy is a boolean
            if "memory_worthy" not in segment:
                segment["memory_worthy"] = True  # Default to memory worthy if missing
            elif not isinstance(segment["memory_worthy"], bool):
                segment["memory_worthy"] = bool(segment["memory_worthy"])  # Convert to boolean
            
            cleaned_segments.append(segment)
        
        return cleaned_segments 