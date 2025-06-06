"""
Relationship Extractor

LLM-based extraction of relationships between entities.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
import logging


class RelationshipExtractor:
    """Extracts relationships between entities using LLM."""
    
    def __init__(self, llm_service, domain_config: Optional[Dict[str, Any]] = None, logger=None):
        """
        Initialize relationship extractor.
        
        Args:
            llm_service: LLM service for relationship extraction
            domain_config: Domain-specific configuration
            logger: Logger instance
        """
        self.llm_service = llm_service
        self.domain_config = domain_config or {}
        self.logger = logger or logging.getLogger(__name__)
        
        # Define relationship types based on domain
        self.relationship_types = self._get_relationship_types()
    
    def _get_relationship_types(self) -> Dict[str, str]:
        """Get relationship types based on domain configuration."""
        domain_name = self.domain_config.get('domain_name', 'general')
        
        if 'dnd' in domain_name.lower():
            return {
                'located_in': 'Entity is physically located within another entity',
                'owns': 'Character possesses or controls an object',
                'member_of': 'Character belongs to an organization or group',
                'allies_with': 'Characters are allied or friendly',
                'enemies_with': 'Characters are hostile or opposed',
                'uses': 'Character uses an object, spell, or ability',
                'created_by': 'Object or concept was created by a character',
                'leads_to': 'Event or action causes another event',
                'participates_in': 'Character takes part in an event',
                'related_to': 'General association between entities',
                'mentions': 'Entity is mentioned in context of another'
            }
        elif 'lab' in domain_name.lower():
            return {
                'used_in': 'Equipment or material used in procedure',
                'produces': 'Procedure or reaction produces a result',
                'requires': 'Procedure requires specific materials or equipment',
                'measures': 'Equipment measures or detects something',
                'contains': 'Sample or material contains a substance',
                'performed_by': 'Procedure performed by a person',
                'collaborates_with': 'Person works with another person',
                'based_on': 'Procedure based on a concept or theory',
                'leads_to': 'One result leads to another finding',
                'related_to': 'General association between entities'
            }
        else:
            return {
                'located_in': 'Entity is located within another',
                'part_of': 'Entity is part of a larger entity',
                'owns': 'Entity possesses another entity',
                'created_by': 'Entity was created by another',
                'uses': 'Entity uses or employs another',
                'causes': 'Entity causes or leads to another',
                'participates_in': 'Entity participates in an event',
                'related_to': 'General association between entities',
                'mentions': 'Entity is mentioned in context'
            }
    
    def extract_relationships(self, text: str, entities: List[Dict[str, Any]], 
                            context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract relationships between entities in the given text.
        
        Args:
            text: Text to analyze for relationships
            entities: List of entities found in the text
            context: Optional context for better understanding
            
        Returns:
            List of extracted relationships
        """
        if not text.strip() or len(entities) < 2:
            return []
        
        try:
            prompt = self._build_relationship_prompt(text, entities, context)
            response = self.llm_service.generate(prompt)
            
            relationships = self._parse_relationship_response(response, entities)
            self.logger.debug(f"Extracted {len(relationships)} relationships from text")
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error extracting relationships: {e}")
            return []
    
    def _build_relationship_prompt(self, text: str, entities: List[Dict[str, Any]], 
                                 context: Optional[str] = None) -> str:
        """Build prompt for relationship extraction."""
        relationship_types_desc = "\\n".join([
            f"- {rtype}: {desc}" for rtype, desc in self.relationship_types.items()
        ])
        
        entities_list = "\\n".join([
            f"- {entity['name']} ({entity['type']}): {entity['description']}"
            for entity in entities
        ])
        
        prompt = f"""Analyze the following text to identify relationships between the given entities.

Relationship Types:
{relationship_types_desc}

Entities in the text:
{entities_list}

Text to analyze:
{text}
"""
        
        if context:
            prompt += f"""
Context:
{context}
"""
        
        prompt += """
Identify relationships between the entities based on what is explicitly stated or clearly implied in the text.
Only include relationships that are directly supported by the text content.

Respond with a JSON array of relationships. Each relationship should have:
- "from_entity": name of the source entity
- "to_entity": name of the target entity  
- "relationship": type of relationship (from the defined types)
- "confidence": confidence score from 0.0 to 1.0
- "evidence": brief quote or description from text supporting this relationship

Example response format:
[
    {
        "from_entity": "Eldara",
        "to_entity": "Riverwatch", 
        "relationship": "located_in",
        "confidence": 0.9,
        "evidence": "Eldara runs the magic shop in Riverwatch"
    }
]

Relationships:"""
        
        return prompt
    
    def _parse_relationship_response(self, response: str, 
                                   entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse LLM response to extract relationship list."""
        try:
            # Create entity name lookup for validation
            entity_names = {entity['name'].lower() for entity in entities}
            
            # Clean up response - look for JSON array
            response = response.strip()
            
            # Find JSON array in response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                relationships = json.loads(json_str)
                
                # Validate and clean relationships
                valid_relationships = []
                for rel in relationships:
                    if self._validate_relationship(rel, entity_names):
                        valid_relationships.append(rel)
                
                return valid_relationships
            
            else:
                self.logger.warning("No JSON array found in relationship extraction response")
                return []
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse relationship extraction JSON: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing relationship extraction response: {e}")
            return []
    
    def _validate_relationship(self, relationship: Dict[str, Any], 
                             entity_names: set) -> bool:
        """Validate extracted relationship structure."""
        required_fields = ['from_entity', 'to_entity', 'relationship']
        
        # Check required fields exist
        for field in required_fields:
            if field not in relationship or not relationship[field]:
                return False
        
        # Check entities exist in the entity list
        from_name = relationship['from_entity'].lower()
        to_name = relationship['to_entity'].lower()
        
        if from_name not in entity_names or to_name not in entity_names:
            return False
        
        # Check relationship type is valid
        if relationship['relationship'] not in self.relationship_types:
            return False
        
        # Check confidence is reasonable (if provided)
        confidence = relationship.get('confidence', 1.0)
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            relationship['confidence'] = 1.0
        
        return True
    
    def extract_relationships_from_segments(self, segments: List[Dict[str, Any]], 
                                          entities_by_segment: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Extract relationships from conversation segments with their entities.
        
        Args:
            segments: List of conversation segments
            entities_by_segment: Dict mapping segment IDs to their entities
            
        Returns:
            List of all extracted relationships with segment references
        """
        all_relationships = []
        
        for segment in segments:
            # Skip low-importance or non-informational segments
            if (segment.get('importance', 0) < 3 or 
                segment.get('type') not in ['information', 'action']):
                continue
            
            segment_id = segment.get('segment_id', '')
            text = segment.get('text', '')
            entities = entities_by_segment.get(segment_id, [])
            
            if not text or len(entities) < 2:
                continue
            
            # Extract relationships from segment
            relationships = self.extract_relationships(text, entities)
            
            # Add segment reference to each relationship
            for rel in relationships:
                rel['source_segment'] = segment_id
                rel['source_text'] = text
                rel['segment_importance'] = segment.get('importance', 0)
                rel['segment_topics'] = segment.get('topics', [])
                all_relationships.append(rel)
        
        self.logger.debug(f"Extracted {len(all_relationships)} relationships from {len(segments)} segments")
        return all_relationships
    
    def extract_temporal_relationships(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract temporal relationships between events across segments.
        
        Args:
            segments: Ordered list of conversation segments
            
        Returns:
            List of temporal relationships between events
        """
        temporal_relationships = []
        event_segments = []
        
        # Find segments that contain events
        for segment in segments:
            if (segment.get('type') == 'action' or 
                segment.get('importance', 0) >= 4):
                event_segments.append(segment)
        
        # Create temporal relationships between consecutive events
        for i in range(len(event_segments) - 1):
            current_segment = event_segments[i]
            next_segment = event_segments[i + 1]
            
            # Create a simple temporal relationship
            temporal_rel = {
                'from_entity': f"event_{current_segment.get('segment_id', i)}",
                'to_entity': f"event_{next_segment.get('segment_id', i+1)}",
                'relationship': 'occurs_before',
                'confidence': 0.8,
                'evidence': 'Sequential order in conversation',
                'source_segments': [
                    current_segment.get('segment_id', ''),
                    next_segment.get('segment_id', '')
                ],
                'temporal_order': i
            }
            
            temporal_relationships.append(temporal_rel)
        
        return temporal_relationships
    
    def find_cross_segment_relationships(self, segments: List[Dict[str, Any]], 
                                       all_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find relationships between entities that appear in different segments.
        
        Args:
            segments: List of conversation segments
            all_entities: All entities extracted from segments
            
        Returns:
            List of cross-segment relationships
        """
        cross_relationships = []
        
        # Group entities by name/type for cross-referencing
        entity_mentions = {}
        for entity in all_entities:
            key = (entity['name'].lower(), entity['type'])
            if key not in entity_mentions:
                entity_mentions[key] = []
            entity_mentions[key].append(entity)
        
        # Find entities mentioned in multiple segments
        for (name, etype), mentions in entity_mentions.items():
            if len(mentions) > 1:
                # Create "mentions" relationships across segments
                for i, mention in enumerate(mentions):
                    for j, other_mention in enumerate(mentions[i+1:], i+1):
                        cross_rel = {
                            'from_entity': mention['name'],
                            'to_entity': other_mention['name'],
                            'relationship': 'co_mentioned',
                            'confidence': 0.6,
                            'evidence': f"Both mentioned across segments",
                            'source_segments': [
                                mention.get('source_segment', ''),
                                other_mention.get('source_segment', '')
                            ],
                            'cross_segment': True
                        }
                        cross_relationships.append(cross_rel)
        
        return cross_relationships