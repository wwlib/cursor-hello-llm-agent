"""
Entity Extractor

LLM-centric entity extraction with RAG-based entity matching.
Implements the LLM-centric approach for entity identification and matching,
using a two-stage process with RAG to find similar existing entities.
"""

import json
import re
import os
from typing import Dict, List, Any, Optional, Tuple
import logging


class EntityExtractor:
    """Entity extractor using LLM-centric approach with RAG matching."""
    
    def __init__(self, llm_service, domain_config: Optional[Dict[str, Any]] = None, 
                 graph_manager=None, logger=None):
        """
        Initialize entity extractor.
        
        Args:
            llm_service: LLM service for entity extraction and matching
            domain_config: Domain-specific configuration with entity types
            graph_manager: Graph manager for RAG-based entity lookup
            logger: Logger instance
        """
        self.llm_service = llm_service
        self.domain_config = domain_config or {}
        self.graph_manager = graph_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        # Get entity types from domain config
        self.entity_types = self._get_entity_types()
    
    def _load_prompt_template(self) -> str:
        """Load the entity extraction prompt template."""
        try:
            template_path = os.path.join(os.path.dirname(__file__), 
                                       'templates', 'entity_extraction.prompt')
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.warning(f"Failed to load prompt template: {e}")
            return self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> str:
        """Get default prompt template if file loading fails."""
        return """Analyze the conversation text and identify entities for knowledge graph storage.

Entity Types: {entity_types}

Conversation: {conversation_text}
Digest: {digest_text}

Extract entities as JSON array with fields: type, name, description, confidence.

Entities:"""
    
    def _get_entity_types(self) -> Dict[str, str]:
        """Get entity types from domain configuration."""
        graph_config = self.domain_config.get('graph_memory_config', {})
        entity_types_list = graph_config.get('entity_types', [])
        
        # Create descriptions based on domain
        domain_name = self.domain_config.get('domain_name', 'general')
        
        if 'dnd' in domain_name.lower():
            type_descriptions = {
                'character': 'People, NPCs, players, creatures, or any named individuals',
                'location': 'Places, regions, buildings, rooms, or geographical features',
                'object': 'Items, artifacts, weapons, tools, books, or physical things',
                'concept': 'Spells, abilities, rules, abstract ideas, or game mechanics',
                'event': 'Actions, occurrences, battles, meetings, or happenings',
                'organization': 'Groups, guilds, factions, or structured entities'
            }
        elif 'lab' in domain_name.lower():
            type_descriptions = {
                'equipment': 'Laboratory instruments, tools, or apparatus',
                'material': 'Chemicals, samples, reagents, or substances',
                'procedure': 'Experimental methods, protocols, or techniques',
                'result': 'Findings, measurements, observations, or outcomes',
                'concept': 'Theories, principles, or scientific concepts',
                'person': 'Researchers, technicians, or laboratory personnel'
            }
        else:
            type_descriptions = {
                'person': 'People, individuals, or characters',
                'location': 'Places, areas, or geographical features',
                'object': 'Items, tools, or physical things',
                'concept': 'Ideas, principles, or abstract concepts',
                'event': 'Actions, occurrences, or happenings',
                'organization': 'Groups, companies, or institutions'
            }
        
        # Use configured types or fall back to defaults
        result = {}
        for entity_type in entity_types_list:
            result[entity_type] = type_descriptions.get(entity_type, f"{entity_type.title()} entities")
        
        return result or type_descriptions
    
    def _write_verbose_log(self, message: str):
        """Write verbose log message to graph storage directory if available."""
        try:
            if self.graph_manager and hasattr(self.graph_manager, '_write_verbose_graph_log'):
                self.graph_manager._write_verbose_graph_log(message)
            else:
                # Fallback to regular logger if graph manager not available
                self.logger.debug(message)
        except Exception as e:
            # Don't fail the main operation if logging fails
            self.logger.debug(f"Failed to write verbose log: {e}")
    
    async def extract_entities_from_conversation_async(self, conversation_text: str, digest_text: str = "") -> List[Dict[str, Any]]:
        """
        Extract entities from full conversation entry using two-stage async LLM approach.
        
        Stage 1: Generate candidate entities from conversation + digest
        Stage 2: Use RAG to find similar existing entities, then LLM decides final entities
        
        Args:
            conversation_text: Full conversation entry text
            digest_text: Digest/summary of the conversation
            
        Returns:
            List of entities with existing/new classification
        """
        try:
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Starting async entity extraction")
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Conversation length: {len(conversation_text)}")
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Digest length: {len(digest_text)}")
            
            # Stage 1: Generate candidate entities (async)
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Stage 1: Extracting candidate entities")
            candidate_entities = await self._extract_candidate_entities_async(conversation_text, digest_text)
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Stage 1 complete: {len(candidate_entities) if candidate_entities else 0} candidates")
            
            if not candidate_entities:
                self.logger.debug("No candidate entities found")
                self._write_verbose_log(f"[ENTITY_EXTRACTOR] No candidate entities found, returning empty list")
                return []
            
            # Stage 2: Use RAG to find similar existing entities and make final decisions (async)
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Stage 2: Resolving entities with RAG")
            final_entities = await self._resolve_entities_with_rag_async(candidate_entities, conversation_text, digest_text)
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Stage 2 complete: {len(final_entities)} final entities")
            
            self.logger.debug(f"Extracted {len(final_entities)} final entities from conversation")
            return final_entities
            
        except Exception as e:
            self.logger.error(f"Error in async entity extraction: {e}")
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] ERROR: {e}")
            import traceback
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] ERROR TRACEBACK: {traceback.format_exc()}")
            return []

    def extract_entities_from_conversation(self, conversation_text: str, digest_text: str = "") -> List[Dict[str, Any]]:
        """
        # TODO: OBSOLETE - REMOVE
        Extract entities from full conversation entry using two-stage LLM approach.
        
        Stage 1: Generate candidate entities from conversation + digest
        Stage 2: Use RAG to find similar existing entities, then LLM decides final entities
        
        Args:
            conversation_text: Full conversation entry text
            digest_text: Digest/summary of the conversation
            
        Returns:
            List of entities with existing/new classification
        """
        try:
            # Stage 1: Generate candidate entities
            candidate_entities = self._extract_candidate_entities(conversation_text, digest_text)
            
            if not candidate_entities:
                self.logger.debug("No candidate entities found")
                return []
            
            # Stage 2: Use RAG to find similar existing entities and make final decisions
            final_entities = self._resolve_entities_with_rag(candidate_entities, conversation_text, digest_text)
            
            self.logger.debug(f"Extracted {len(final_entities)} final entities from conversation")
            return final_entities
            
        except Exception as e:
            self.logger.error(f"Error in alternative entity extraction: {e}")
            return []
    
    def _extract_candidate_entities(self, conversation_text: str, digest_text: str) -> List[Dict[str, Any]]:
        """# TODO: OBSOLETE - REMOVE
        Stage 1: Extract candidate entities from conversation text."""
        try:
            # Build entity types description
            entity_types_desc = "\n".join([
                f"- {etype}: {desc}" for etype, desc in self.entity_types.items()
            ])
            
            # Build prompt
            prompt = self.prompt_template.format(
                entity_types=entity_types_desc,
                conversation_text=conversation_text,
                digest_text=digest_text,
                existing_context=""  # No existing context in stage 1
            )
            
            # Get LLM response
            response = self.llm_service.generate(prompt)
            
            # Parse entities
            entities = self._parse_entity_response(response)
            
            self.logger.debug(f"Stage 1: Extracted {len(entities)} candidate entities")
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting candidate entities: {e}")
            return []

    async def _extract_candidate_entities_async(self, conversation_text: str, digest_text: str) -> List[Dict[str, Any]]:
        """Stage 1: Extract candidate entities from conversation text (async version)."""
        try:
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] _extract_candidate_entities_async: Starting")
            
            # Build entity types description
            entity_types_desc = "\n".join([
                f"- {etype}: {desc}" for etype, desc in self.entity_types.items()
            ])
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Entity types: {len(self.entity_types)} types")
            
            # Build prompt
            prompt = self.prompt_template.format(
                entity_types=entity_types_desc,
                conversation_text=conversation_text,
                digest_text=digest_text,
                existing_context=""  # No existing context in stage 1
            )
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Built prompt length: {len(prompt)} characters")
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Calling LLM service async...")
            
            # Get LLM response (async)
            response = await self.llm_service.generate_async(prompt)
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] LLM response received, length: {len(response) if response else 0}")
            
            # Parse entities
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Parsing entity response...")
            entities = self._parse_entity_response(response)
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] Parsed {len(entities)} entities")
            
            self.logger.debug(f"Stage 1: Extracted {len(entities)} candidate entities (async)")
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting candidate entities (async): {e}")
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] ERROR in _extract_candidate_entities_async: {e}")
            import traceback
            self._write_verbose_log(f"[ENTITY_EXTRACTOR] ERROR TRACEBACK: {traceback.format_exc()}")
            return []
    
    def _resolve_entities_with_rag(self, candidate_entities: List[Dict[str, Any]], 
                                  conversation_text: str, digest_text: str) -> List[Dict[str, Any]]:
        """# TODO: OBSOLETE - REMOVE
        Stage 2: Use RAG to find similar entities and make final entity decisions."""
        if not self.graph_manager:
            self.logger.warning("No graph manager available for RAG - returning candidates as new entities")
            return [{"status": "new", **entity} for entity in candidate_entities]
        
        try:
            # For each candidate, find similar existing entities using RAG
            existing_entities_context = []
            
            for candidate in candidate_entities:
                similar_entities = self._find_similar_existing_entities(candidate)
                if similar_entities:
                    existing_entities_context.extend(similar_entities)
            
            # Remove duplicates from existing entities
            seen_ids = set()
            unique_existing = []
            for entity in existing_entities_context:
                if entity['id'] not in seen_ids:
                    seen_ids.add(entity['id'])
                    unique_existing.append(entity)
            
            # Build context for existing entities
            if unique_existing:
                existing_context = "\n**Similar Existing Entities:**\n"
                for entity in unique_existing:
                    existing_context += f"- {entity['name']} ({entity['type']}): {entity['description']}\n"
                existing_context += "\n**Instructions:** For each candidate entity, decide if it matches an existing entity above or if it should be created as new. If it matches existing, use the existing entity's name exactly."
            else:
                existing_context = "\n**No similar existing entities found.**"
            
            # Build final prompt with existing context
            entity_types_desc = "\n".join([
                f"- {etype}: {desc}" for etype, desc in self.entity_types.items()
            ])
            
            prompt = self.prompt_template.format(
                entity_types=entity_types_desc,
                conversation_text=conversation_text,
                digest_text=digest_text,
                existing_context=existing_context
            )
            
            # Get LLM response for final entities
            response = self.llm_service.generate(prompt)
            final_entities = self._parse_entity_response(response)
            
            # Return candidates without classification - EntityResolver will handle all matching
            candidate_entities = []
            for entity in final_entities:
                candidate_entities.append({
                    'status': 'candidate',  # Mark as candidate for EntityResolver
                    **entity
                })
            
            self.logger.debug(f"Stage 2: Extracted {len(candidate_entities)} candidate entities for EntityResolver")
            return candidate_entities
            
        except Exception as e:
            self.logger.error(f"Error in entity extraction: {e}")
            return [{"status": "candidate", **entity} for entity in candidate_entities if candidate_entities] if 'candidate_entities' in locals() else []

    async def _resolve_entities_with_rag_async(self, candidate_entities: List[Dict[str, Any]], 
                                  conversation_text: str, digest_text: str) -> List[Dict[str, Any]]:
        """Stage 2: Use RAG to find similar entities and make final entity decisions (async version)."""
        if not self.graph_manager:
            self.logger.warning("No graph manager available for RAG - returning candidates as new entities")
            return [{"status": "new", **entity} for entity in candidate_entities]
        
        try:
            # For each candidate, find similar existing entities using RAG
            existing_entities_context = []
            
            for candidate in candidate_entities:
                similar_entities = self._find_similar_existing_entities(candidate)
                if similar_entities:
                    existing_entities_context.extend(similar_entities)
            
            # Remove duplicates from existing entities
            seen_ids = set()
            unique_existing = []
            for entity in existing_entities_context:
                if entity['id'] not in seen_ids:
                    seen_ids.add(entity['id'])
                    unique_existing.append(entity)
            
            # Build context for existing entities
            if unique_existing:
                existing_context = "\n**Similar Existing Entities:**\n"
                for entity in unique_existing:
                    existing_context += f"- {entity['name']} ({entity['type']}): {entity['description']}\n"
                existing_context += "\n**Instructions:** For each candidate entity, decide if it matches an existing entity above or if it should be created as new. If it matches existing, use the existing entity's name exactly."
            else:
                existing_context = "\n**No similar existing entities found.**"
            
            # Build final prompt with existing context
            entity_types_desc = "\n".join([
                f"- {etype}: {desc}" for etype, desc in self.entity_types.items()
            ])
            
            prompt = self.prompt_template.format(
                entity_types=entity_types_desc,
                conversation_text=conversation_text,
                digest_text=digest_text,
                existing_context=existing_context
            )
            
            # Get LLM response for final entities (async)
            response = await self.llm_service.generate_async(prompt)
            final_entities = self._parse_entity_response(response)
            
            # Return candidates without classification - EntityResolver will handle all matching
            candidate_entities_result = []
            for entity in final_entities:
                candidate_entities_result.append({
                    'status': 'candidate',  # Mark as candidate for EntityResolver
                    **entity
                })
            
            self.logger.debug(f"Stage 2: Extracted {len(candidate_entities_result)} candidate entities for EntityResolver (async)")
            return candidate_entities_result
            
        except Exception as e:
            self.logger.error(f"Error in entity extraction (async): {e}")
            return [{"status": "candidate", **entity} for entity in candidate_entities if candidate_entities] if 'candidate_entities' in locals() else []
    
    def _find_similar_existing_entities(self, candidate_entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use RAG to find existing entities similar to the candidate."""
        try:
            # Search query combining name and description
            search_query = f"{candidate_entity['name']} {candidate_entity.get('description', '')}"
            
            # Use graph manager's query method for RAG
            similar_results = self.graph_manager.query_for_context(search_query, max_results=3)
            
            # Convert to entity format
            similar_entities = []
            for result in similar_results:
                # Only include entities of the same type
                if result.get('type') == candidate_entity.get('type'):
                    similar_entities.append({
                        'id': f"{result['type']}_{result['name'].lower().replace(' ', '_')}",
                        'name': result['name'],
                        'type': result['type'],
                        'description': result['description'],
                        'relevance_score': result.get('relevance_score', 0.0)
                    })
            
            return similar_entities
            
        except Exception as e:
            self.logger.warning(f"Error finding similar entities for {candidate_entity.get('name', 'unknown')}: {e}")
            return []
    
    
    def _parse_entity_response(self, response: str) -> List[Dict[str, Any]]:
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
        
        # Check entity type is valid
        if entity['type'] not in self.entity_types:
            return False
        
        # Check confidence is reasonable (if provided)
        confidence = entity.get('confidence', 1.0)
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            entity['confidence'] = 1.0
        
        return True
    
    def get_entity_types(self) -> Dict[str, str]:
        """Get configured entity types."""
        return self.entity_types.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return {
            'extractor_type': 'alternative_llm_centric',
            'entity_types_count': len(self.entity_types),
            'has_graph_manager': self.graph_manager is not None,
            'domain': self.domain_config.get('domain_name', 'general')
        } 