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
from .entity_resolver import EntityResolver


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
            
            # Initialize EntityResolver for enhanced duplicate detection in alt processing
            graph_config = domain_config.get("graph_memory_config", {})
            resolver_enabled = graph_config.get("enable_entity_resolver", True)
            
            if resolver_enabled and embeddings_manager:
                confidence_threshold = graph_config.get("similarity_threshold", 0.8)
                self.alt_entity_resolver = EntityResolver(
                    llm_service=llm_service,
                    embeddings_manager=embeddings_manager,
                    storage_path=storage_path,
                    confidence_threshold=confidence_threshold,
                    logger=logger
                )
                self.logger.info("EntityResolver enabled for AltGraphManager")
            else:
                self.alt_entity_resolver = None
                if not embeddings_manager:
                    self.logger.warning("EntityResolver disabled in AltGraphManager: embeddings_manager not available")
                else:
                    self.logger.info("EntityResolver disabled in AltGraphManager by configuration")
        else:
            self.alt_entity_extractor = None
            self.alt_relationship_extractor = None
            self.alt_entity_resolver = None
        
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
    
    def process_conversation_entry_with_resolver(self, conversation_text: str, digest_text: str = "", 
                                                conversation_guid: str = None) -> Dict[str, Any]:
        """
        Process conversation entry using EntityResolver for enhanced duplicate detection.
        
        This method combines the alternative LLM-centric approach with EntityResolver's
        sophisticated duplicate detection capabilities. It extracts entities, resolves them
        against existing nodes with confidence scoring, and then processes relationships.
        
        Args:
            conversation_text: Full conversation entry text
            digest_text: Digest/summary of the conversation
            conversation_guid: GUID for tracking conversation mentions
            
        Returns:
            Dictionary with processing results including resolved entities and relationships
        """
        if not self.alt_entity_extractor:
            self.logger.error("Alternative entity extractor not available")
            return {"entities": [], "relationships": [], "error": "Alt entity extractor not available"}
        
        # Use basic processing if EntityResolver is not available
        if not self.alt_entity_resolver:
            self.logger.debug("EntityResolver not available, falling back to basic processing")
            return self.process_conversation_entry(conversation_text, digest_text)
        
        try:
            results = {
                "entities": [],
                "relationships": [],
                "new_entities": [],
                "existing_entities": [],
                "resolved_entities": [],
                "stats": {}
            }
            
            # Stage 1: Extract entities using alternative approach
            self.logger.debug("Stage 1: Extracting entities from conversation with AltEntityExtractor")
            raw_entities = self.alt_entity_extractor.extract_entities_from_conversation(
                conversation_text, digest_text)
            
            if not raw_entities:
                self.logger.info("No entities extracted from conversation")
                return results
            
            # Filter out entities that the alt_entity_extractor already marked as existing
            # But verify that "existing" entities actually exist in the graph
            unresolved_entities = []
            for entity in raw_entities:
                if entity.get('status') != 'existing':
                    unresolved_entities.append(entity)
                else:
                    # Verify that "existing" entities actually exist in the graph
                    existing_node = self._update_existing_entity(entity)
                    if existing_node:
                        # Entity truly exists, add to results
                        results["existing_entities"].append(existing_node.to_dict())
                    else:
                        # Entity marked as "existing" but not found in graph
                        # Treat as a new entity and let EntityResolver handle it
                        self.logger.debug(f"Entity '{entity.get('name', 'unknown')}' marked as existing but not found in graph, treating as new")
                        entity['status'] = 'new'  # Override the status
                        unresolved_entities.append(entity)
            
            if unresolved_entities:
                # Stage 2: Convert to EntityResolver candidates
                self.logger.debug(f"Stage 2: Converting {len(unresolved_entities)} entities to resolver candidates")
                candidates = []
                for i, entity in enumerate(unresolved_entities):
                    candidate = {
                        "candidate_id": f"alt_candidate_{i}_{entity.get('name', 'unknown')}",
                        "type": entity.get("type", "concept"),
                        "name": entity.get("name", ""),
                        "description": entity.get("description", ""),
                        "original_entity": entity  # Keep reference to original
                    }
                    candidates.append(candidate)
                
                # Stage 3: Resolve candidates using EntityResolver
                self.logger.debug(f"Stage 3: Resolving {len(candidates)} candidates with EntityResolver")
                resolutions = self.alt_entity_resolver.resolve_candidates(
                    candidates, 
                    process_individually=True  # Use individual processing for highest accuracy
                )
                
                # Stage 4: Process resolutions and update graph
                processed_entities = []
                for resolution, candidate in zip(resolutions, candidates):
                    original_entity = candidate["original_entity"]
                    
                    # Add resolution metadata to the entity
                    original_entity["resolver_candidate_id"] = resolution["candidate_id"]
                    original_entity["resolver_confidence"] = resolution["confidence"]
                    original_entity["resolver_matched"] = resolution["auto_matched"]
                    original_entity["resolver_justification"] = resolution["resolution_justification"]
                    
                    self.logger.debug(f"Resolution for '{candidate['name']}': auto_matched={resolution.get('auto_matched', False)}, "
                                     f"confidence={resolution.get('confidence', 0.0)}, threshold={self.alt_entity_resolver.confidence_threshold}, "
                                     f"resolved_to={resolution.get('resolved_node_id', 'unknown')}")
                    
                    if resolution["auto_matched"] and resolution["resolved_node_id"] != "<NEW>":
                        # High-confidence match to existing entity
                        self.logger.debug(f"Entity '{candidate['name']}' resolved to existing node "
                                        f"{resolution['resolved_node_id']} (confidence: {resolution['confidence']:.3f})")
                        
                        # Update existing node
                        existing_node = self.get_node(resolution["resolved_node_id"])
                        self.logger.debug(f"get_node({resolution['resolved_node_id']}) returned: {existing_node is not None}")
                        if existing_node:
                            existing_node.mention_count += 1
                            
                            # Update conversation history GUIDs
                            if conversation_guid:
                                if "conversation_history_guids" not in existing_node.attributes:
                                    existing_node.attributes["conversation_history_guids"] = []
                                if conversation_guid not in existing_node.attributes["conversation_history_guids"]:
                                    existing_node.attributes["conversation_history_guids"].append(conversation_guid)
                            
                            # Add to results
                            original_entity["resolved_to"] = resolution["resolved_node_id"]
                            original_entity["resolution_type"] = "matched"
                            processed_entities.append({
                                'node': existing_node,
                                'status': 'matched',
                                **original_entity
                            })
                            self.logger.debug(f"Added entity '{candidate['name']}' to processed_entities list")
                            results["existing_entities"].append(existing_node.to_dict())
                    else:
                        # Create new entity or low confidence match
                        self.logger.debug(f"Creating new entity for '{candidate['name']}' "
                                        f"(confidence: {resolution['confidence']:.3f})")
                        
                        # Create new node
                        new_node, is_new = self.add_or_update_node(
                            name=original_entity.get("name", ""),
                            node_type=original_entity.get("type", "concept"),
                            description=original_entity.get("description", ""),
                            confidence=original_entity.get("confidence", 1.0),
                            conversation_guid=conversation_guid
                        )
                        
                        # Add to results
                        original_entity["resolved_to"] = new_node.id
                        original_entity["resolution_type"] = "new" if is_new else "updated"
                        processed_entities.append({
                            'node': new_node,
                            'status': 'new' if is_new else 'updated',
                            **original_entity
                        })
                        if is_new:
                            results["new_entities"].append(new_node.to_dict())
                
                # Store resolved entities for relationship extraction
                results["resolved_entities"] = [item for item in processed_entities]
                self.logger.debug(f"processed_entities count: {len(processed_entities)}")
                for i, entity in enumerate(processed_entities):
                    node = entity.get('node')
                    node_name = node.name if node else 'unknown'
                    self.logger.debug(f"  processed_entities[{i}]: {node_name} (status: {entity.get('status', 'unknown')})")
            
            # Combine all processed entities for relationship extraction
            all_processed_entities = []
            
            # Add resolved entities from EntityResolver processing
            all_processed_entities.extend(results.get("resolved_entities", []))
            
            # Add any entities that were truly existing (found in _update_existing_entity)
            for entity_dict in results.get("existing_entities", []):
                # Convert back to the expected format
                existing_node = self.get_node(entity_dict.get("id"))
                if existing_node:
                    all_processed_entities.append({
                        "node": existing_node,
                        "status": "existing",
                        "name": entity_dict.get("name", ""),
                        "type": entity_dict.get("type", "")
                    })
            
            results["entities"] = [item['node'].to_dict() for item in all_processed_entities if item.get('node')]
            
            # Stage 5: Extract relationships if we have multiple entities
            self.logger.debug("Stage 5: Extracting relationships from resolved entities")
            self.logger.debug(f"all_processed_entities count: {len(all_processed_entities)}")
            for i, entity in enumerate(all_processed_entities):
                self.logger.debug(f"  [{i}] {entity}")
            
            if len(all_processed_entities) >= 2 and self.alt_relationship_extractor:
                # Create entity list with resolved node names for relationship extraction
                entity_list = []
                for processed_entity in all_processed_entities:
                    if processed_entity.get('node'):
                        # Use the resolved node's name and ID for relationship extraction
                        node = processed_entity['node']
                        entity_info = {
                            'name': node.name,  # Use the actual node name
                            'type': node.type,
                            'description': node.description,
                            'resolved_node_id': node.id,  # Add the actual node ID
                            'status': processed_entity.get('status', 'resolved')
                        }
                        entity_list.append(entity_info)
                
                self.logger.debug(f"Calling relationship extractor with {len(entity_list)} entities:")
                for entity in entity_list:
                    self.logger.debug(f"  - {entity['name']} ({entity['type']}) ID: {entity.get('resolved_node_id', 'N/A')}")
                
                # Log the conversation text being passed to relationship extractor
                self.logger.debug(f"Conversation text for relationship extraction: '{conversation_text}'")
                self.logger.debug(f"Digest text for relationship extraction: '{digest_text}'")
                
                extracted_relationships = self.alt_relationship_extractor.extract_relationships_from_conversation(
                    conversation_text, digest_text, entity_list)
                
                self.logger.debug(f"Relationship extractor returned {len(extracted_relationships)} relationships")
                for rel in extracted_relationships:
                    self.logger.debug(f"  - {rel.get('from_entity', '?')} --[{rel.get('relationship', '?')}]--> {rel.get('to_entity', '?')}")
                
                # Process and add relationships to graph
                # Create mapping from original entity names to resolved node IDs
                original_to_resolved = {}
                for processed_entity in all_processed_entities:
                    if processed_entity.get('node'):
                        resolved_node = processed_entity['node']
                        
                        # Try to get original entity name from multiple sources
                        original_name = None
                        if 'original_entity' in processed_entity:
                            original_name = processed_entity['original_entity'].get('name', '').lower()
                        elif 'name' in processed_entity:
                            original_name = processed_entity['name'].lower()
                        
                        # Also map the current node name to itself (for direct matches)
                        current_name = resolved_node.name.lower()
                        original_to_resolved[current_name] = resolved_node
                        
                        # Map original name to resolved node (if different)
                        if original_name and original_name != current_name:
                            original_to_resolved[original_name] = resolved_node
                            self.logger.debug(f"Mapping original '{original_name}' -> resolved '{resolved_node.name}' ({resolved_node.id})")
                
                for relationship in extracted_relationships:
                    try:
                        edge = self._add_relationship_to_graph_with_resolver(
                            relationship, all_processed_entities, original_to_resolved)
                        if edge:
                            results["relationships"].append(edge.to_dict())
                    except Exception as e:
                        self.logger.error(f"Error processing relationship: {e}")
                        continue
            
            # Generate enhanced stats
            results["stats"] = {
                "entities_extracted": len(raw_entities),
                "entities_resolved": len(results.get("resolved_entities", [])),
                "entities_new": len(results["new_entities"]),
                "entities_existing": len(results["existing_entities"]),
                "relationships_extracted": len(results["relationships"]),
                "conversation_length": len(conversation_text),
                "digest_length": len(digest_text),
                "resolver_enabled": True,
                "resolver_confidence_threshold": self.alt_entity_resolver.confidence_threshold
            }
            
            self.logger.info(f"Processed conversation with EntityResolver: {results['stats']}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in process_conversation_entry_with_resolver: {e}")
            # Fallback to basic processing
            self.logger.warning("Falling back to basic conversation processing")
            return self.process_conversation_entry(conversation_text, digest_text)
    
    def _add_relationship_to_graph_with_resolver(self, relationship: Dict[str, Any], 
                                               processed_entities: List[Dict[str, Any]],
                                               original_to_resolved: Dict[str, Any]) -> Optional[GraphEdge]:
        """Add a relationship to the graph using resolved entity mapping.
        
        This method handles the case where relationship extraction refers to original entity names
        but those entities have been resolved to existing nodes with different names/IDs.
        """
        try:
            from_entity_name = relationship.get('from_entity', '').lower()
            to_entity_name = relationship.get('to_entity', '').lower()
            
            # First try to find nodes using the original-to-resolved mapping
            from_node = original_to_resolved.get(from_entity_name)
            to_node = original_to_resolved.get(to_entity_name)
            
            # If not found in mapping, try direct name lookup (for entities that weren't resolved)
            if not from_node or not to_node:
                entity_name_to_node = {
                    item['node'].name.lower(): item['node'] 
                    for item in processed_entities if item.get('node')
                }
                
                if not from_node:
                    from_node = entity_name_to_node.get(from_entity_name)
                if not to_node:
                    to_node = entity_name_to_node.get(to_entity_name)
            
            # If still not found, try alternative lookups
            if not from_node or not to_node:
                # Try partial matching or different name variations
                for item in processed_entities:
                    if item.get('node'):
                        node = item['node']
                        node_name_lower = node.name.lower()
                        
                        # Check if the relationship entity name is contained in the node name
                        if not from_node and (from_entity_name in node_name_lower or node_name_lower in from_entity_name):
                            from_node = node
                            self.logger.debug(f"Found from_node via partial match: '{from_entity_name}' -> '{node.name}' ({node.id})")
                        
                        if not to_node and (to_entity_name in node_name_lower or node_name_lower in to_entity_name):
                            to_node = node
                            self.logger.debug(f"Found to_node via partial match: '{to_entity_name}' -> '{node.name}' ({node.id})")
            
            if not from_node or not to_node:
                self.logger.warning(f"Could not find nodes for relationship {relationship}")
                self.logger.debug(f"Available nodes: {[item['node'].name + ' (' + item['node'].id + ')' for item in processed_entities if item.get('node')]}")
                self.logger.debug(f"Original-to-resolved mapping: {[(k, v.name + ' (' + v.id + ')') for k, v in original_to_resolved.items()]}")
                return None
            
            # Create the relationship
            evidence = relationship.get('evidence', '')
            confidence = relationship.get('confidence', 0.5)
            relationship_type = relationship.get('relationship', 'related_to')
            
            edge = self.add_edge(
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                relationship=relationship_type,
                evidence=evidence,
                confidence=confidence
            )
            
            if edge:
                self.logger.debug(f"Created relationship: {from_node.name} ({from_node.id}) --[{relationship_type}]--> {to_node.name} ({to_node.id})")
            
            return edge
            
        except Exception as e:
            self.logger.error(f"Error adding relationship to graph: {e}")
            return None 