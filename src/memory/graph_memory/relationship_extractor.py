"""
Relationship Extractor

LLM-centric relationship extraction that works with entity context from the entity extractor.
This extractor focuses on analyzing full conversation text with explicit entity context,
rather than working with pre-segmented text.
"""

import json
import re
import os
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime


class RelationshipExtractor:
    """Relationship extractor using LLM-centric approach with entity context."""
    
    def __init__(self, llm_service, domain_config: Optional[Dict[str, Any]] = None, logger=None):
        """
        Initialize relationship extractor.
        
        Args:
            llm_service: LLM service for relationship extraction
            domain_config: Domain-specific configuration with relationship types
            logger: Logger instance
        """
        self.llm_service = llm_service
        self.domain_config = domain_config or {}
        self.logger = logger or logging.getLogger(__name__)
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        # Get relationship types from domain config
        self.relationship_types = self._get_relationship_types()
    
    def _load_prompt_template(self) -> str:
        """Load the relationship extraction prompt template."""
        try:
            template_path = os.path.join(os.path.dirname(__file__), 
                                       'templates', 'relationship_extraction.prompt')
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.warning(f"Failed to load prompt template: {e}")
            return self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> str:
        """Get default prompt template if file loading fails."""
        return """Analyze the conversation text and identify relationships between the given entities.

Relationship Types: {relationship_types}

Conversation: {conversation_text}
Digest: {digest_text}

Entities: {entities_context}

Extract relationships as JSON array with fields: from_entity, to_entity, relationship, confidence, evidence.

Relationships:"""
    
    def _get_relationship_types(self) -> Dict[str, str]:
        """Get relationship types from domain configuration."""
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
    
    def extract_relationships_from_conversation(self, conversation_text: str, digest_text: str = "",
                                              entities: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extract relationships from full conversation entry with entity context.
        
        This method analyzes the full conversation text and digest to identify relationships
        between the provided entities, using LLM reasoning to understand context.
        
        Args:
            conversation_text: Full conversation entry text
            digest_text: Digest/summary of the conversation
            entities: List of entities from entity extraction phase
            
        Returns:
            List of relationships between entities
        """
        if not entities or len(entities) < 2:
            self.logger.debug("Need at least 2 entities to extract relationships")
            return []
        
        try:
            # Build entity context
            entities_context = self._build_entities_context(entities)
            
            # Build relationship types description
            relationship_types_desc = "\n".join([
                f"- {rtype}: {desc}" for rtype, desc in self.relationship_types.items()
            ])
            
            # Build prompt
            prompt = self.prompt_template.format(
                relationship_types=relationship_types_desc,
                conversation_text=conversation_text,
                digest_text=digest_text,
                entities_context=entities_context
            )
            
            # Get LLM response
            response = self.llm_service.generate(prompt)
            
            # Parse relationships
            relationships = self._parse_relationship_response(response, entities)
            
            self.logger.debug(f"Extracted {len(relationships)} relationships from conversation")
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error in alternative relationship extraction: {e}")
            return []
    
    def _build_entities_context(self, entities: List[Dict[str, Any]]) -> str:
        """Build formatted entity context for the prompt."""
        entities_lines = []
        for entity in entities:
            status = entity.get('status', 'new')
            name = entity.get('name', '')
            entity_type = entity.get('type', '')
            description = entity.get('description', '')
            
            line = f"- {name} ({entity_type})"
            if status == 'existing':
                line += " [EXISTING]"
            line += f": {description}"
            
            entities_lines.append(line)
        
        return "\n".join(entities_lines)
    
    def _parse_relationship_response(self, response: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    def _validate_relationship(self, relationship: Dict[str, Any], entity_names: set) -> bool:
        """Validate extracted relationship structure."""
        required_fields = ['from_entity', 'to_entity', 'relationship']
        
        # Check required fields exist
        for field in required_fields:
            if field not in relationship or not relationship[field]:
                return False
        
        # Check entities exist in the entity list (case-insensitive)
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
        
        # Ensure evidence exists
        if 'evidence' not in relationship:
            relationship['evidence'] = "Inferred from context"
        
        return True
    
    def extract_relationships_from_entities(self, entities: List[Dict[str, Any]], 
                                          context_text: str = "") -> List[Dict[str, Any]]:
        """
        Extract relationships between entities with optional context.
        
        This is a simplified version that works with just entity information
        and optional context text, useful for cross-conversation relationship detection.
        
        Args:
            entities: List of entities to analyze for relationships
            context_text: Optional context text for relationship inference
            
        Returns:
            List of relationships between entities
        """
        if not entities or len(entities) < 2:
            return []
        
        try:
            # Build simplified prompt
            entities_context = self._build_entities_context(entities)
            relationship_types_desc = "\n".join([
                f"- {rtype}: {desc}" for rtype, desc in self.relationship_types.items()
            ])
            
            prompt = f"""Analyze the following entities to identify likely relationships between them.

Relationship Types:
{relationship_types_desc}

Entities:
{entities_context}

Context: {context_text}

Based on the entity descriptions and any provided context, identify logical relationships.
Only include relationships that are clearly implied by the entity information.

Respond with a JSON array of relationships with fields: from_entity, to_entity, relationship, confidence, evidence.

Relationships:"""
            
            # Get LLM response
            response = self.llm_service.generate(prompt)
            
            # Parse relationships
            relationships = self._parse_relationship_response(response, entities)
            
            self.logger.debug(f"Extracted {len(relationships)} relationships from entity analysis")
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error extracting relationships from entities: {e}")
            return []
    
    def deduplicate_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate relationships based on from_entity, to_entity, and relationship type.
        
        Args:
            relationships: List of relationships to deduplicate
            
        Returns:
            List of unique relationships
        """
        seen_relationships = set()
        unique_relationships = []
        
        for rel in relationships:
            # Create a key for deduplication
            key = (
                rel['from_entity'].lower(),
                rel['to_entity'].lower(),
                rel['relationship']
            )
            
            if key not in seen_relationships:
                seen_relationships.add(key)
                unique_relationships.append(rel)
        
        return unique_relationships
    
    def get_relationship_types(self) -> Dict[str, str]:
        """Get configured relationship types."""
        return self.relationship_types.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return {
            'extractor_type': 'alternative_llm_centric',
            'relationship_types_count': len(self.relationship_types),
            'domain': self.domain_config.get('domain_name', 'general')
        } 