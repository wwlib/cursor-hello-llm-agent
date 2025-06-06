"""
Entity Extractor

LLM-based extraction of entities from conversation segments.
"""

import json
import re
from typing import Dict, List, Any, Optional
import logging


class EntityExtractor:
    """Extracts entities from conversation segments using LLM."""
    
    def __init__(self, llm_service, domain_config: Optional[Dict[str, Any]] = None, logger=None):
        """
        Initialize entity extractor.
        
        Args:
            llm_service: LLM service for entity extraction
            domain_config: Domain-specific configuration
            logger: Logger instance
        """
        self.llm_service = llm_service
        self.domain_config = domain_config or {}
        self.logger = logger or logging.getLogger(__name__)
        
        # Define entity types based on domain
        self.entity_types = self._get_entity_types()
    
    def _get_entity_types(self) -> Dict[str, str]:
        """Get entity types based on domain configuration."""
        domain_name = self.domain_config.get('domain_name', 'general')
        
        if 'dnd' in domain_name.lower():
            return {
                'character': 'People, NPCs, players, creatures, or any named individuals',
                'location': 'Places, regions, buildings, rooms, or geographical features',
                'object': 'Items, artifacts, weapons, tools, books, or physical things',
                'concept': 'Spells, abilities, rules, abstract ideas, or game mechanics',
                'event': 'Actions, occurrences, battles, meetings, or significant happenings',
                'organization': 'Groups, guilds, factions, or structured entities'
            }
        elif 'lab' in domain_name.lower():
            return {
                'equipment': 'Laboratory instruments, tools, devices, or apparatus',
                'material': 'Chemical compounds, biological samples, reagents, or substances',
                'procedure': 'Experimental methods, protocols, techniques, or processes',
                'result': 'Measurements, observations, outcomes, or data points',
                'person': 'Researchers, collaborators, or individuals involved',
                'concept': 'Scientific theories, principles, or abstract ideas'
            }
        else:
            return {
                'person': 'Individuals, people, or named entities',
                'place': 'Locations, regions, or geographical entities',
                'thing': 'Objects, items, or physical entities',
                'concept': 'Ideas, principles, or abstract entities',
                'event': 'Actions, occurrences, or happenings'
            }
    
    def extract_entities(self, text: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract entities from text using LLM.
        
        Args:
            text: Text to extract entities from
            context: Optional context for better extraction
            
        Returns:
            List of extracted entities with type, name, and description
        """
        if not text.strip():
            return []
        
        try:
            prompt = self._build_extraction_prompt(text, context)
            response = self.llm_service.generate(prompt)
            
            entities = self._parse_extraction_response(response)
            self.logger.debug(f"Extracted {len(entities)} entities from text")
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return []
    
    def _build_extraction_prompt(self, text: str, context: Optional[str] = None) -> str:
        """Build prompt for entity extraction."""
        entity_types_desc = "\\n".join([
            f"- {etype}: {desc}" for etype, desc in self.entity_types.items()
        ])
        
        prompt = f"""Extract entities from the following text. For each entity, provide:
1. type: one of the defined types
2. name: the entity name/identifier
3. description: a brief description suitable for semantic matching

Entity Types:
{entity_types_desc}

Text to analyze:
{text}
"""
        
        if context:
            prompt += f"""
Context (for better understanding):
{context}
"""
        
        prompt += """
Respond with a JSON array of entities. Each entity should have "type", "name", and "description" fields.
Only include entities that are clearly mentioned or implied in the text.
Avoid generic terms - focus on specific, identifiable entities.

Example response format:
[
    {"type": "character", "name": "Eldara", "description": "A fire wizard who runs the magic shop in Riverwatch"},
    {"type": "location", "name": "Riverwatch", "description": "A town with a magic shop"}
]

Entities:"""
        
        return prompt
    
    def _parse_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract entity list."""
        try:
            # Clean up response - look for JSON array
            response = response.strip()
            
            # Find JSON array in response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                entities = json.loads(json_str)
                
                # Validate and clean entities
                valid_entities = []
                for entity in entities:
                    if self._validate_entity(entity):
                        valid_entities.append(entity)
                
                return valid_entities
            
            else:
                self.logger.warning("No JSON array found in entity extraction response")
                return []
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse entity extraction JSON: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing entity extraction response: {e}")
            return []
    
    def _validate_entity(self, entity: Dict[str, Any]) -> bool:
        """Validate extracted entity structure."""
        required_fields = ['type', 'name', 'description']
        
        # Check required fields exist
        for field in required_fields:
            if field not in entity or not entity[field]:
                return False
        
        # Check type is valid
        if entity['type'] not in self.entity_types:
            return False
        
        # Check name and description are strings and reasonable length
        if (not isinstance(entity['name'], str) or 
            not isinstance(entity['description'], str) or
            len(entity['name']) < 1 or 
            len(entity['description']) < 5):
            return False
        
        return True
    
    def extract_entities_from_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract entities from conversation segments.
        
        Args:
            segments: List of conversation segments
            
        Returns:
            List of all extracted entities with segment references
        """
        all_entities = []
        
        for segment in segments:
            # Skip low-importance or non-informational segments
            if (segment.get('importance', 0) < 3 or 
                segment.get('type') not in ['information', 'action']):
                continue
            
            text = segment.get('text', '')
            if not text:
                continue
            
            # Extract entities from segment
            entities = self.extract_entities(text)
            
            # Add segment reference to each entity
            for entity in entities:
                entity['source_segment'] = segment.get('segment_id', '')
                entity['source_text'] = text
                entity['segment_importance'] = segment.get('importance', 0)
                entity['segment_topics'] = segment.get('topics', [])
                all_entities.append(entity)
        
        self.logger.debug(f"Extracted {len(all_entities)} entities from {len(segments)} segments")
        return all_entities
    
    def group_entities_by_type(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group entities by their type."""
        grouped = {}
        
        for entity in entities:
            entity_type = entity.get('type', 'unknown')
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(entity)
        
        return grouped
    
    def deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simple deduplication of entities by name (case-insensitive).
        More sophisticated deduplication happens in GraphManager.
        """
        seen_names = set()
        unique_entities = []
        
        for entity in entities:
            name_key = (entity['type'], entity['name'].lower())
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_entities.append(entity)
        
        return unique_entities