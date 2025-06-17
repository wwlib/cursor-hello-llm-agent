"""
Relationship Extractor

LLM-centric relationship extraction that works with entity context from the entity extractor.
This extractor analyzes full conversation text with explicit entity context to identify
meaningful relationships between entities in knowledge graphs.
"""

import json
import re
import os
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime


class RelationshipExtractor:
    """Relationship extractor using LLM-centric approach with entity context."""
    
    def __init__(self, llm_service, domain_config: Optional[Dict[str, Any]] = None, logger=None,
                 relationship_llm_service=None):
        """
        Initialize relationship extractor.
        
        Args:
            llm_service: Default LLM service for relationship extraction
            domain_config: Domain-specific configuration with relationship types
            logger: Logger instance
            relationship_llm_service: Optional dedicated LLM service for relationship extraction.
                                    If provided, this will be used instead of llm_service.
                                    This allows for separate logging and model configuration.
        """
        # Use dedicated relationship LLM service if provided, otherwise fall back to default
        self.llm_service = relationship_llm_service if relationship_llm_service else llm_service
        self.domain_config = domain_config or {}
        self.logger = logger or logging.getLogger(__name__)
        
        # Store reference to the default LLM service for backwards compatibility
        self._default_llm_service = llm_service
        self._dedicated_relationship_llm = relationship_llm_service is not None
        
        if self._dedicated_relationship_llm:
            self.logger.info("RelationshipExtractor initialized with dedicated LLM service")
        else:
            self.logger.debug("RelationshipExtractor initialized with default LLM service")
        
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

Extract relationships as JSON array with fields: from_entity_id, to_entity_id, relationship, confidence, evidence.

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
        """Build formatted entity context for the prompt with resolved node IDs."""
        entities_lines = ["AVAILABLE ENTITIES (use exact IDs):"]
        
        for entity in entities:
            name = entity.get('name', '')
            entity_type = entity.get('type', '')
            description = entity.get('description', '')
            node_id = entity.get('resolved_node_id', '')
            status = entity.get('status', 'resolved')
            
            # Format: "- ID: node_id | Name: EntityName (type): description"
            if node_id:
                line = f"- ID: {node_id} | Name: {name} ({entity_type}): {description}"
            else:
                # Fallback if no ID available
                line = f"- Name: {name} ({entity_type}): {description} [NO ID]"
            
            # Add status indicator for clarity
            if status == 'existing':
                line += " [EXISTING]"
            elif status == 'new':
                line += " [NEW]"
            
            entities_lines.append(line)
        
        entities_lines.append("\nIMPORTANT: Only create relationships between entities listed above.")
        entities_lines.append("Use the exact entity IDs as shown (from_entity_id and to_entity_id fields).")
        entities_lines.append("Do not reference any entities not in this list.")
        
        return "\n".join(entities_lines)
    
    def _parse_relationship_response(self, response: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse LLM response to extract relationship list."""
        try:
            # Create entity ID lookup for validation
            entity_ids = {entity.get('resolved_node_id', '') for entity in entities if entity.get('resolved_node_id')}
            
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
                    if self._validate_relationship(rel, entity_ids):
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
    
    def _validate_relationship(self, relationship: Dict[str, Any], entity_ids: set) -> bool:
        """Validate extracted relationship structure and entity references."""
        required_fields = ['from_entity_id', 'to_entity_id', 'relationship']
        
        # Check required fields exist
        for field in required_fields:
            if field not in relationship or not relationship[field]:
                self.logger.debug(f"Relationship missing required field: {field}")
                return False
        
        # Check entities exist in the entity list by ID
        from_id = relationship['from_entity_id'].strip()
        to_id = relationship['to_entity_id'].strip()
        
        if from_id not in entity_ids or to_id not in entity_ids:
            self.logger.debug(f"Relationship references unknown entity IDs: {relationship['from_entity_id']} -> {relationship['to_entity_id']}")
            available_ids = ", ".join(sorted(entity_ids))
            self.logger.debug(f"Available entity IDs: {available_ids}")
            return False
        
        # Check relationship type is valid
        if relationship['relationship'] not in self.relationship_types:
            self.logger.debug(f"Invalid relationship type: {relationship['relationship']}")
            return False
        
        # Check confidence is reasonable (if provided)
        confidence = relationship.get('confidence', 1.0)
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            relationship['confidence'] = 1.0
        
        # Ensure evidence exists
        if 'evidence' not in relationship:
            relationship['evidence'] = "Inferred from context"
        
        return True
    

    
    def get_relationship_types(self) -> Dict[str, str]:
        """Get configured relationship types."""
        return self.relationship_types.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        stats = {
            'extractor_type': 'llm_centric',
            'relationship_types_count': len(self.relationship_types),
            'domain': self.domain_config.get('domain_name', 'general'),
            'uses_dedicated_llm': self._dedicated_relationship_llm
        }
        
        # Add LLM service information if available
        if hasattr(self.llm_service, 'model'):
            stats['llm_model'] = self.llm_service.model
        if hasattr(self.llm_service, 'debug_scope'):
            stats['llm_debug_scope'] = self.llm_service.debug_scope
        if hasattr(self.llm_service, 'debug_file'):
            stats['llm_debug_file'] = self.llm_service.debug_file
        
        # Add core features
        stats['features'] = {
            'entity_context_validation': True,
            'domain_specific_relationships': True,
            'dedicated_llm_support': True
        }
            
        return stats
    
    def analyze_entity_context(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the entity context to provide debugging information.
        
        Args:
            entities: List of entities from entity extraction phase
            
        Returns:
            Dictionary with entity context analysis
        """
        if not entities:
            return {
                'total_entities': 0,
                'entities_with_ids': 0,
                'entity_types': {},
                'status_breakdown': {}
            }
        
        analysis = {
            'total_entities': len(entities),
            'entities_with_ids': 0,
            'entity_types': {},
            'status_breakdown': {}
        }
        
        for entity in entities:
            # Count entities with resolved node IDs
            if entity.get('resolved_node_id'):
                analysis['entities_with_ids'] += 1
            
            # Count by entity type
            entity_type = entity.get('type', 'unknown')
            analysis['entity_types'][entity_type] = analysis['entity_types'].get(entity_type, 0) + 1
            
            # Count by status
            status = entity.get('status', 'unknown')
            analysis['status_breakdown'][status] = analysis['status_breakdown'].get(status, 0) + 1
        
        return analysis
    
    def is_using_dedicated_llm(self) -> bool:
        """Check if this extractor is using a dedicated LLM service."""
        return self._dedicated_relationship_llm
    
    def get_llm_service_info(self) -> Dict[str, Any]:
        """Get information about the LLM service being used."""
        info = {
            'using_dedicated_service': self._dedicated_relationship_llm,
            'service_type': type(self.llm_service).__name__
        }
        
        # Add model information if available
        if hasattr(self.llm_service, 'model'):
            info['model'] = self.llm_service.model
        if hasattr(self.llm_service, 'temperature'):
            info['temperature'] = self.llm_service.temperature
        if hasattr(self.llm_service, 'debug_scope'):
            info['debug_scope'] = self.llm_service.debug_scope
        if hasattr(self.llm_service, 'debug_file'):
            info['debug_file'] = self.llm_service.debug_file
            
        return info 