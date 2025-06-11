"""
Entity Extractor

LLM-based extraction of entities from conversation segments.

This module provides the EntityExtractor class that uses Large Language Models
to identify and extract domain-specific entities from unstructured text.
The extractor supports configurable entity types for different domains
(D&D campaigns, laboratory work, software projects) and includes validation
and deduplication capabilities.

Example:
    Basic usage of EntityExtractor::

        from src.memory.graph_memory.entity_extractor import EntityExtractor
        
        # Initialize with LLM service and domain configuration
        extractor = EntityExtractor(
            llm_service=llm_service,
            domain_config=dnd_config
        )
        
        # Extract entities from text
        entities = extractor.extract_entities(
            "Eldara the fire wizard runs a magic shop in Riverwatch"
        )
        
        # Result: [
        #   {"name": "Eldara", "type": "character", "description": "..."},
        #   {"name": "Riverwatch", "type": "location", "description": "..."}
        # ]

Attributes:
    llm_service: LLM service for entity extraction prompts.
    domain_config (Dict[str, Any]): Domain-specific configuration.
    entity_types (Dict[str, str]): Mapping of entity types to descriptions.
    logger: Logger instance for debugging and monitoring.
"""

import json
import re
from typing import Dict, List, Any, Optional
import logging


class EntityExtractor:
    """Extracts entities from conversation segments using LLM.
    
    EntityExtractor provides LLM-driven identification of domain-specific entities
    from unstructured conversation text. It supports configurable entity types,
    validation of extracted entities, and basic deduplication.
    
    The extractor uses domain-specific prompting to identify entities relevant
    to the configured domain (e.g., characters and locations for D&D campaigns,
    equipment and procedures for laboratory work).
    
    Attributes:
        llm_service: LLM service for generating entity extraction prompts.
        domain_config: Domain configuration containing entity type definitions.
        entity_types: Dictionary mapping entity type names to descriptions.
        logger: Logger instance for debugging and error tracking.
    
    Example::

        # Initialize for D&D domain
        extractor = EntityExtractor(
            llm_service=gemma_service,
            domain_config={
                'domain_name': 'dnd_campaign',
                'entity_types': ['character', 'location', 'object']
            }
        )
        
        # Extract entities from conversation segment
        entities = extractor.extract_entities(
            "The party meets Eldara at her magic shop in Riverwatch"
        )
        
        # Process multiple segments
        segments = [
            {"text": "...", "importance": 4, "type": "information"},
            {"text": "...", "importance": 3, "type": "action"}
        ]
        all_entities = extractor.extract_entities_from_segments(segments)
    
    Note:
        Requires a configured LLM service for entity extraction.
        Domain configuration determines available entity types.
    """
    
    def __init__(self, llm_service, domain_config: Optional[Dict[str, Any]] = None, logger=None):
        """Initialize entity extractor with LLM service and domain configuration.
        
        Args:
            llm_service: LLM service instance for entity extraction.
                Must support text generation with structured prompts.
            domain_config: Domain-specific configuration dictionary.
                Should contain 'domain_name' and optionally custom entity types.
                If None, uses general-purpose entity types.
            logger: Logger instance for debugging and monitoring.
                If None, creates a default logger.
                   
        Example::

            # D&D campaign configuration
            dnd_config = {
                'domain_name': 'dnd_campaign',
                'entity_types': ['character', 'location', 'object', 'event']
            }
            
            extractor = EntityExtractor(
                llm_service=llm_service,
                domain_config=dnd_config,
                logger=custom_logger
            )
        """
        self.llm_service = llm_service
        self.domain_config = domain_config or {}
        self.logger = logger or logging.getLogger(__name__)
        
        # Define entity types based on domain
        self.entity_types = self._get_entity_types()
    
    def _get_entity_types(self) -> Dict[str, str]:
        """Get entity types based on domain configuration.
        
        Determines the appropriate entity types and their descriptions
        based on the configured domain. Supports predefined domains
        (D&D, laboratory, general) with fallback to general types.
        
        Returns:
            Dictionary mapping entity type names to their descriptions.
            Used for LLM prompting and entity validation.
            
        Example:
            For D&D domain::

                {
                    'character': 'People, NPCs, players, creatures, or any named individuals',
                    'location': 'Places, regions, buildings, rooms, or geographical features',
                    'object': 'Items, artifacts, weapons, tools, books, or physical things',
                    'concept': 'Spells, abilities, rules, abstract ideas, or game mechanics',
                    'event': 'Actions, occurrences, battles, meetings, or significant happenings',
                    'organization': 'Groups, guilds, factions, or structured entities'
                }
            
        Note:
            Domain is determined by checking if keywords ('dnd', 'lab') 
            appear in the domain_name configuration value.
        """
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
        """Extract entities from text using LLM with domain-specific prompting.
        
        Analyzes the provided text to identify entities of types defined
        in the domain configuration. Uses structured LLM prompting to
        extract entity names, types, and descriptions.
        
        Args:
            text: Text content to analyze for entities.
                Should be meaningful content (not empty or whitespace only).
            context: Optional additional context to improve extraction accuracy.
                Can include background information or conversation history.
                    
        Returns:
            List of entity dictionaries, each containing:
            
            - name (str): Entity name/identifier
            - type (str): Entity type from domain configuration
            - description (str): Detailed entity description
            - Additional fields may be present based on LLM output
            
        Example::

            # Basic extraction
            entities = extractor.extract_entities(
                "Eldara the fire wizard runs a magic shop in Riverwatch"
            )
            
            # With context for better accuracy
            entities = extractor.extract_entities(
                "She sells potions and scrolls",
                context="Previous: Eldara the fire wizard runs a magic shop"
            )
            
            # Typical result:
            # [
            #     {
            #         "name": "Eldara",
            #         "type": "character", 
            #         "description": "A fire wizard who runs a magic shop"
            #     },
            #     {
            #         "name": "Riverwatch",
            #         "type": "location",
            #         "description": "A town where Eldara's magic shop is located"
            #     }
            # ]
            
        Note:
            Returns empty list if text is empty or LLM extraction fails.
            All returned entities are validated against domain entity types.
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
        """Build structured prompt for LLM entity extraction.
        
        Creates a detailed prompt that instructs the LLM to extract entities
        according to the domain-specific entity types. Includes examples
        and formatting requirements for consistent JSON output.
        
        Args:
            text: Text to analyze for entities.
            context: Optional context for better understanding.
            
        Returns:
            Formatted prompt string ready for LLM processing.
            Includes entity type definitions, text to analyze,
            and response format instructions.
            
        Note:
            Prompt format is optimized for structured JSON output.
            Entity type descriptions are dynamically inserted from domain config.
        """
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
        """Parse LLM response to extract entity list from JSON.
        
        Processes the LLM's text response to extract structured entity data.
        Handles various response formats and validates entity structure.
        
        Args:
            response: Raw text response from LLM.
                Expected to contain JSON array of entities.
                     
        Returns:
            List of validated entity dictionaries.
            Invalid entities are filtered out with logging.
            
        Example:
            Input response::

                Here are the entities I found:
                [
                    {"type": "character", "name": "Eldara", "description": "..."},
                    {"type": "location", "name": "Riverwatch", "description": "..."}
                ]
            
            Output::

                [
                    {"type": "character", "name": "Eldara", "description": "..."},
                    {"type": "location", "name": "Riverwatch", "description": "..."}
                ]
            
        Note:
            Uses regex to find JSON arrays in free-form text responses.
            Gracefully handles JSON parsing errors and malformed responses.
        """
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
        """Validate extracted entity structure and content.
        
        Ensures that extracted entities meet minimum requirements
        for inclusion in the knowledge graph. Validates required
        fields, data types, and content quality.
        
        Args:
            entity: Entity dictionary to validate.
                Expected to have 'type', 'name', and 'description' fields.
                   
        Returns:
            True if entity is valid and should be included, False otherwise.
            
        Validation Rules:
            - Required fields: 'type', 'name', 'description' must be present and non-empty
            - Type validation: 'type' must match domain-configured entity types
            - Content validation: 'name' and 'description' must be strings of reasonable length
            - Minimum length: name >= 1 character, description >= 5 characters
            
        Example::

            # Valid entity
            valid = {
                "type": "character",
                "name": "Eldara", 
                "description": "A fire wizard who runs a magic shop"
            }
            assert extractor._validate_entity(valid) == True
            
            # Invalid entity (missing description)
            invalid = {
                "type": "character",
                "name": "Eldara"
            }
            assert extractor._validate_entity(invalid) == False
            
        Note:
            Invalid entities are logged with warning level for debugging.
        """
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
        """Extract entities from multiple conversation segments with filtering.
        
        Processes a list of conversation segments to extract entities,
        applying importance and type filtering to focus on meaningful content.
        Only segments meeting quality criteria are processed.
        
        Args:
            segments: List of conversation segment dictionaries.
                Each segment should contain:
                
                - text (str): Segment content
                - importance (int): Importance score (1-5)
                - type (str): Segment type ('information', 'action', etc.)
                - segment_id (str, optional): Unique identifier
                - topics (List[str], optional): Associated topics
                     
        Returns:
            List of all extracted entities with segment metadata.
            Each entity includes:
            
            - All standard entity fields (name, type, description)
            - source_segment (str): ID of originating segment
            - source_text (str): Original text containing the entity
            - segment_importance (int): Importance score of source segment
            - segment_topics (List[str]): Topics associated with source segment
            
        Filtering Criteria:
            - importance >= 3: Only process moderately to highly important content
            - type in ['information', 'action']: Skip queries and commands
            - text must be non-empty: Skip segments without content
            
        Example::

            segments = [
                {
                    "text": "Eldara runs a magic shop in Riverwatch",
                    "importance": 4,
                    "type": "information",
                    "segment_id": "seg_001",
                    "topics": ["characters", "locations"]
                },
                {
                    "text": "What time is it?",
                    "importance": 1,
                    "type": "query"  # Will be skipped
                }
            ]
            
            entities = extractor.extract_entities_from_segments(segments)
            # Returns entities only from the first segment
            
        Note:
            Segment filtering reduces processing load and improves entity quality
            by focusing on meaningful, informational content.
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
                entity['conversation_guid'] = segment.get('conversation_guid', '')
                all_entities.append(entity)
        
        self.logger.debug(f"Extracted {len(all_entities)} entities from {len(segments)} segments")
        return all_entities
    
    def group_entities_by_type(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group entities by their type for organized processing.
        
        Organizes a list of entities into a dictionary grouped by entity type.
        Useful for type-specific processing or analysis.
        
        Args:
            entities: List of entity dictionaries with 'type' field.
            
        Returns:
            Dictionary mapping entity types to lists of entities of that type.
            
        Example::

            entities = [
                {"name": "Eldara", "type": "character", "description": "..."},
                {"name": "Gareth", "type": "character", "description": "..."},
                {"name": "Riverwatch", "type": "location", "description": "..."}
            ]
            
            grouped = extractor.group_entities_by_type(entities)
            # Result:
            # {
            #     "character": [
            #         {"name": "Eldara", "type": "character", ...},
            #         {"name": "Gareth", "type": "character", ...}
            #     ],
            #     "location": [
            #         {"name": "Riverwatch", "type": "location", ...}
            #     ]
            # }
            
        Note:
            Entities with missing or invalid 'type' field are grouped under 'unknown'.
        """
        grouped = {}
        
        for entity in entities:
            entity_type = entity.get('type', 'unknown')
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(entity)
        
        return grouped
    
    def deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple deduplication of entities by name and type.
        
        Removes basic duplicates from a list of entities using case-insensitive
        name matching within the same entity type. This provides simple
        deduplication before more sophisticated similarity matching in GraphManager.
        
        Args:
            entities: List of entity dictionaries to deduplicate.
                Each entity should have 'name' and 'type' fields.
                     
        Returns:
            List of unique entities with duplicates removed.
            First occurrence of each (type, name) combination is preserved.
            
        Example::

            entities = [
                {"name": "Eldara", "type": "character", "description": "Fire wizard"},
                {"name": "ELDARA", "type": "character", "description": "Magic shop owner"},
                {"name": "Riverwatch", "type": "location", "description": "Eastern town"}
            ]
            
            unique = extractor.deduplicate_entities(entities)
            # Result: Only first "Eldara" and "Riverwatch" are kept
            # [
            #     {"name": "Eldara", "type": "character", "description": "Fire wizard"},
            #     {"name": "Riverwatch", "type": "location", "description": "Eastern town"}
            # ]
            
        Note:
            This is basic deduplication. More sophisticated semantic similarity
            matching happens in GraphManager._find_similar_node().
            Case-insensitive matching treats "Eldara" and "ELDARA" as duplicates.
        """
        seen_names = set()
        unique_entities = []
        
        for entity in entities:
            name_key = (entity['type'], entity['name'].lower())
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_entities.append(entity)
        
        return unique_entities