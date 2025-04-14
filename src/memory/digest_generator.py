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
    2. Extract structured data (facts and relationships) from segments
    
    This allows for more precise information extraction and better traceability
    between digests and the conversation entries they were derived from.
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
            "extract": "extract_digest.prompt"
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
    
    def generate_digest(self, conversation_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured digest from a conversation entry using a two-step process.
        
        Args:
            conversation_entry: Dictionary containing the conversation entry with role, content, etc.
            
        Returns:
            dict: A digest containing segmented content and extracted information
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
                return self._create_empty_digest(entry_guid)
            
            # Step 1: Segment the content
            segments = self._segment_content(content)
            
            # Step 2: Extract structured information from segments
            extracted_info = self._extract_information(segments)
            
            # Combine into final digest
            digest = {
                "conversationHistoryGuid": entry_guid,
                "segments": segments,
                "context": extracted_info.get("context", ""),
                "new_facts": extracted_info.get("new_facts", []),
                "new_relationships": extracted_info.get("new_relationships", [])
            }
            
            return digest
            
        except Exception as e:
            print(f"Error generating digest: {str(e)}")
            return self._create_empty_digest(entry_guid if entry_guid else str(uuid.uuid4()))
    
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
    
    def _extract_information(self, segments: List[str]) -> Dict[str, Any]:
        """Extract structured information from segments using LLM.
        
        Args:
            segments: List of segmented phrases
            
        Returns:
            dict: Structured information extract from segments
        """
        try:
            # Format the prompt with the segments
            prompt = self.templates["extract"].format(segments=json.dumps(segments))
            
            # Call LLM to extract information
            llm_response = self.llm.generate(prompt)
            
            # Parse the response as JSON
            try:
                extracted_info = json.loads(llm_response)
                # Validate the structure
                if not isinstance(extracted_info, dict):
                    print("Extraction failed: Response is not a dictionary")
                    return self._create_empty_extracted_info()
                
                # Ensure required fields exist
                if "new_facts" not in extracted_info:
                    extracted_info["new_facts"] = []
                if "new_relationships" not in extracted_info:
                    extracted_info["new_relationships"] = []
                if "context" not in extracted_info:
                    extracted_info["context"] = ""
                
                return extracted_info
            except json.JSONDecodeError:
                # Try to extract JSON if it's embedded in markdown or other text
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        # Remove any markdown code block markers
                        json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                        extracted_info = json.loads(json_str)
                        
                        # Ensure required fields exist
                        if "new_facts" not in extracted_info:
                            extracted_info["new_facts"] = []
                        if "new_relationships" not in extracted_info:
                            extracted_info["new_relationships"] = []
                        if "context" not in extracted_info:
                            extracted_info["context"] = ""
                        
                        return extracted_info
                    except json.JSONDecodeError:
                        pass
                
                # Fall back to empty response
                print("Failed to parse extracted information")
                return self._create_empty_extracted_info()
                
        except Exception as e:
            print(f"Error in information extraction: {str(e)}")
            return self._create_empty_extracted_info()
    
    def _create_empty_digest(self, entry_guid: str) -> Dict[str, Any]:
        """Create an empty digest structure with the given entry GUID."""
        return {
            "conversationHistoryGuid": entry_guid,
            "segments": [],
            "context": "",
            "new_facts": [],
            "new_relationships": []
        }
    
    def _create_empty_extracted_info(self) -> Dict[str, Any]:
        """Create an empty extracted information structure."""
        return {
            "context": "",
            "new_facts": [],
            "new_relationships": []
        } 