"""
Alternative Graph Manager

LLM-centric graph management that uses the alternative entity and relationship extractors.
Implements the alternative approach described in ALT_ENTITY_AND_RELATIONSHIP_EXTRACTION_APPROACH.md

This manager focuses on full conversation analysis rather than segment-based processing,
and relies more heavily on LLM reasoning for entity and relationship identification.
"""

import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

from .graph_manager import GraphManager, GraphNode, GraphEdge
from .alt_entity_extractor import AltEntityExtractor
from .alt_relationship_extractor import AltRelationshipExtractor


class AltGraphManager(GraphManager):
    """Alternative graph manager using LLM-centric extractors."""
    
    def __init__(self, storage_path: str, embeddings_manager=None, 
                 similarity_threshold: float = 0.8, logger=None,
                 llm_service=None, embeddings_llm_service=None, domain_config=None):
        """
        Initialize alternative graph manager with LLM-centric extractors.
        
        Args:
            storage_path: Directory path for JSON graph storage.
            embeddings_manager: EmbeddingsManager for semantic similarity matching.
            similarity_threshold: Cosine similarity threshold for entity matching.
            logger: Logger instance for debugging and monitoring.
            llm_service: LLM service for entity/relationship extraction.
            embeddings_llm_service: LLM service for embeddings.
            domain_config: Domain-specific configuration.
        """
        # Initialize parent class
        super().__init__(storage_path, embeddings_manager, similarity_threshold, 
                        logger, llm_service, embeddings_llm_service, domain_config)
        
        # Override with alternative extractors
        if llm_service and domain_config:
            self.alt_entity_extractor = AltEntityExtractor(
                llm_service, domain_config, graph_manager=self, logger=logger)
            self.alt_relationship_extractor = AltRelationshipExtractor(
                llm_service, domain_config, logger)
        else:
            self.alt_entity_extractor = None
            self.alt_relationship_extractor = None
        
        self.logger.info("Initialized AltGraphManager with LLM-centric extractors")
    
    def process_conversation_entry(self, conversation_text: str, digest_text: str = "") -> Dict[str, Any]:
        """
        Process a full conversation entry using the alternative LLM-centric approach.
        
        This method implements the two-stage process described in the alternative approach:
        1. Extract entities from conversation + digest using RAG for existing entity matching
        2. Extract relationships between the identified entities
        
        Args:
            conversation_text: Full conversation entry text
            digest_text: Digest/summary of the conversation
            
        Returns:
            Dictionary with processing results including entities and relationships
        """
        if not self.alt_entity_extractor or not self.alt_relationship_extractor:
            self.logger.error("Alternative extractors not available - missing LLM service or domain config")
            return {"entities": [], "relationships": [], "error": "Extractors not available"}
        
        try:
            results = {
                "entities": [],
                "relationships": [],
                "new_entities": [],
                "existing_entities": [],
                "stats": {}
            }
            
            # Stage 1: Extract entities using alternative approach
            self.logger.debug("Stage 1: Extracting entities from conversation")
            extracted_entities = self.alt_entity_extractor.extract_entities_from_conversation(
                conversation_text, digest_text)
            
            if not extracted_entities:
                self.logger.info("No entities extracted from conversation")
                return results
            
            # Process and add entities to graph
            processed_entities = []
            for entity in extracted_entities:
                try:
                    if entity.get('status') == 'existing':
                        # Update existing entity
                        existing_node = self._update_existing_entity(entity)
                        if existing_node:
                            processed_entities.append({
                                'node': existing_node,
                                'status': 'existing',
                                **entity
                            })
                            results["existing_entities"].append(existing_node.to_dict())
                    else:
                        # Create new entity
                        new_node, is_new = self.add_or_update_node(
                            name=entity.get("name", ""),
                            node_type=entity.get("type", "concept"),
                            description=entity.get("description", ""),
                            confidence=entity.get("confidence", 1.0)
                        )
                        processed_entities.append({
                            'node': new_node,
                            'status': 'new' if is_new else 'updated',
                            **entity
                        })
                        if is_new:
                            results["new_entities"].append(new_node.to_dict())
                
                except Exception as e:
                    self.logger.error(f"Error processing entity {entity.get('name', 'unknown')}: {e}")
                    continue
            
            results["entities"] = [item['node'].to_dict() for item in processed_entities]
            
            # Stage 2: Extract relationships using alternative approach
            self.logger.debug("Stage 2: Extracting relationships from conversation")
            if len(processed_entities) >= 2:
                entity_list = [item for item in extracted_entities]  # Use original entity format
                extracted_relationships = self.alt_relationship_extractor.extract_relationships_from_conversation(
                    conversation_text, digest_text, entity_list)
                
                # Process and add relationships to graph
                for relationship in extracted_relationships:
                    try:
                        edge = self._add_relationship_to_graph(relationship, processed_entities)
                        if edge:
                            results["relationships"].append(edge.to_dict())
                    except Exception as e:
                        self.logger.error(f"Error processing relationship: {e}")
                        continue
            
            # Generate stats
            results["stats"] = {
                "entities_extracted": len(extracted_entities),
                "entities_new": len(results["new_entities"]),
                "entities_existing": len(results["existing_entities"]),
                "relationships_extracted": len(results["relationships"]),
                "conversation_length": len(conversation_text),
                "digest_length": len(digest_text)
            }
            
            self.logger.info(f"Processed conversation: {results['stats']}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing conversation entry: {e}")
            return {"entities": [], "relationships": [], "error": str(e)}
    
    def _update_existing_entity(self, entity_info: Dict[str, Any]) -> Optional[GraphNode]:
        """Update an existing entity with new information from the conversation."""
        try:
            existing_id = entity_info.get('existing_id')
            if not existing_id:
                self.logger.warning("No existing_id provided for existing entity")
                return None
            
            # Find the existing node
            existing_node = self.nodes.get(existing_id)
            if not existing_node:
                self.logger.warning(f"Existing entity {existing_id} not found in graph")
                return None
            
            # Update with new information
            new_description = entity_info.get('description', '')
            if new_description and new_description != existing_node.description:
                existing_node.description = new_description
                
                # Update embedding if available
                if self.embeddings_manager:
                    try:
                        embedding = self.embeddings_manager.generate_embedding(new_description)
                        existing_node.embedding = embedding
                    except Exception as e:
                        self.logger.warning(f"Failed to update embedding: {e}")
            
            # Update metadata
            existing_node.mention_count += 1
            existing_node.updated_at = datetime.now().isoformat()
            
            # Add confidence as attribute if provided
            confidence = entity_info.get('confidence')
            if confidence is not None:
                existing_node.attributes['last_confidence'] = confidence
            
            # Save changes
            self._save_graph()
            
            return existing_node
            
        except Exception as e:
            self.logger.error(f"Error updating existing entity: {e}")
            return None
    
    def _add_relationship_to_graph(self, relationship: Dict[str, Any], 
                                  processed_entities: List[Dict[str, Any]]) -> Optional[GraphEdge]:
        """Add a relationship to the graph."""
        try:
            # Find the entity nodes by name
            from_node = None
            to_node = None
            
            entity_name_to_node = {
                item['name'].lower(): item['node'] 
                for item in processed_entities
            }
            
            from_name = relationship['from_entity'].lower()
            to_name = relationship['to_entity'].lower()
            
            if from_name in entity_name_to_node:
                from_node = entity_name_to_node[from_name]
            if to_name in entity_name_to_node:
                to_node = entity_name_to_node[to_name]
            
            if not from_node or not to_node:
                self.logger.warning(f"Could not find nodes for relationship {relationship}")
                return None
            
            # Check if relationship already exists
            existing_edge = self._find_edge(from_node.id, to_node.id, relationship['relationship'])
            if existing_edge:
                # Update existing relationship
                existing_edge.confidence = max(existing_edge.confidence, 
                                             relationship.get('confidence', 1.0))
                existing_edge.evidence = relationship.get('evidence', existing_edge.evidence)
                existing_edge.updated_at = datetime.now().isoformat()
                self._save_graph()
                return existing_edge
            
            # Create new relationship
            edge_id = f"edge_{str(uuid.uuid4())[:8]}"
            new_edge = GraphEdge(
                edge_id=edge_id,
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                relationship=relationship['relationship'],
                confidence=relationship.get('confidence', 1.0),
                evidence=relationship.get('evidence', ''),
                created_at=datetime.now().isoformat()
            )
            
            self.edges.append(new_edge)
            self._save_graph()
            
            return new_edge
            
        except Exception as e:
            self.logger.error(f"Error adding relationship to graph: {e}")
            return None
    
    def compare_with_baseline(self, conversation_text: str, digest_text: str = "") -> Dict[str, Any]:
        """
        Compare alternative approach results with baseline approach.
        
        This method runs both the alternative and baseline approaches on the same input
        to enable A/B testing and performance comparison.
        
        Args:
            conversation_text: Full conversation entry text
            digest_text: Digest/summary of the conversation
            
        Returns:
            Dictionary comparing both approaches
        """
        comparison = {
            "alternative": {},
            "baseline": {},
            "comparison_stats": {}
        }
        
        try:
            # Run alternative approach
            self.logger.info("Running alternative approach...")
            alt_results = self.process_conversation_entry(conversation_text, digest_text)
            comparison["alternative"] = alt_results
            
            # Run baseline approach (using parent class methods)
            self.logger.info("Running baseline approach...")
            baseline_results = self._run_baseline_approach(conversation_text, digest_text)
            comparison["baseline"] = baseline_results
            
            # Generate comparison statistics
            comparison["comparison_stats"] = {
                "alt_entities": len(alt_results.get("entities", [])),
                "baseline_entities": len(baseline_results.get("entities", [])),
                "alt_relationships": len(alt_results.get("relationships", [])),
                "baseline_relationships": len(baseline_results.get("relationships", [])),
                "alt_new_entities": len(alt_results.get("new_entities", [])),
                "baseline_new_entities": len(baseline_results.get("new_entities", [])),
            }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Error in comparison: {e}")
            comparison["error"] = str(e)
            return comparison
    
    def _run_baseline_approach(self, conversation_text: str, digest_text: str) -> Dict[str, Any]:
        """Run the baseline segment-based approach for comparison."""
        # This would need to be implemented to create segments and use the original extractors
        # For now, return a placeholder
        return {
            "entities": [],
            "relationships": [],
            "new_entities": [],
            "stats": {
                "approach": "baseline_segment_based",
                "note": "Baseline comparison not yet implemented"
            }
        }
    
    def get_extractor_stats(self) -> Dict[str, Any]:
        """Get statistics about the alternative extractors."""
        stats = {
            "manager_type": "alternative_llm_centric",
            "has_alt_entity_extractor": self.alt_entity_extractor is not None,
            "has_alt_relationship_extractor": self.alt_relationship_extractor is not None,
        }
        
        if self.alt_entity_extractor:
            stats["entity_extractor"] = self.alt_entity_extractor.get_stats()
        
        if self.alt_relationship_extractor:
            stats["relationship_extractor"] = self.alt_relationship_extractor.get_stats()
        
        return stats 