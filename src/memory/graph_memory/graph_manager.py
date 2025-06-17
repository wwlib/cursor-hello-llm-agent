"""
Graph Manager

LLM-centric graph management with advanced entity and relationship extraction.
Focuses on full conversation analysis rather than segment-based processing,
and relies on LLM reasoning for entity and relationship identification.
"""

import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

from .graph_entities import GraphNode, GraphEdge
from .graph_storage import GraphStorage
from .graph_queries import GraphQueries
from .entity_extractor import EntityExtractor
from .relationship_extractor import RelationshipExtractor
from .entity_resolver import EntityResolver


class GraphManager:
    """Graph manager using LLM-centric extractors for entity and relationship extraction."""
    
    def __init__(self, storage_path: str, embeddings_manager=None, 
                 similarity_threshold: float = 0.8, logger=None,
                 llm_service=None, embeddings_llm_service=None, domain_config=None,
                 logs_dir=None, memory_guid=None):
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
            logs_dir: Directory for graph-specific log files (optional).
            memory_guid: Memory GUID for creating dedicated log directories (optional).
        """
        # Initialize core graph functionality
        self.storage = GraphStorage(storage_path)
        self.embeddings_manager = embeddings_manager
        self.similarity_threshold = similarity_threshold
        self.logger = logger or logging.getLogger(__name__)
        self.domain_config = domain_config or {}
        
        # Initialize graph data structures
        self.nodes = {}  # Dict[str, GraphNode]
        self.edges = []  # List[GraphEdge]
        
        # Load existing graph data
        self._load_graph()
        
        # Create dedicated LLM services with graph-specific logging if logs_dir is provided
        self.graph_llm_service = llm_service  # Default to passed service
        self.resolver_llm_service = llm_service  # Default to passed service
        self.relationship_llm_service = llm_service  # Default to passed service
        self.relationship_extractor_logger = logger  # Default to passed logger
        
        if llm_service and logs_dir and memory_guid:
            self._setup_graph_specific_logging(llm_service, logs_dir, memory_guid)
        
        # Initialize entity and relationship extractors using dedicated LLM services
        if llm_service and domain_config:
            self.entity_extractor = EntityExtractor(
                self.graph_llm_service, domain_config, graph_manager=self, logger=logger)
            self.relationship_extractor = RelationshipExtractor(
                self.graph_llm_service, domain_config, self.relationship_extractor_logger, 
                relationship_llm_service=self.relationship_llm_service)
            
            # Initialize EntityResolver for essential duplicate detection
            if not embeddings_manager:
                raise ValueError("EntityResolver requires embeddings_manager - it is mandatory for graph memory")
            
            graph_config = domain_config.get("graph_memory_config", {})
            confidence_threshold = graph_config.get("similarity_threshold", 0.8)
            self.entity_resolver = EntityResolver(
                llm_service=self.resolver_llm_service,
                embeddings_manager=embeddings_manager,
                storage_path=storage_path,
                confidence_threshold=confidence_threshold,
                logger=logger
            )
            self.logger.info("EntityResolver initialized - essential component for preventing duplicate entities")
        else:
            raise ValueError("GraphManager requires llm_service and domain_config - these are mandatory for graph memory operations")
        
        self.logger.info("Initialized GraphManager with LLM-centric extractors")
    
    def _setup_graph_specific_logging(self, base_llm_service, logs_dir: str, memory_guid: str):
        """
        Setup dedicated LLM services with graph-specific logging.
        
        Args:
            base_llm_service: Base LLM service to clone configuration from.
            logs_dir: Directory for log files.
            memory_guid: Memory GUID for creating subdirectories.
        """
        import os
        from src.ai.llm_ollama import OllamaService
        
        # Create GUID-specific logs directory if it doesn't exist  
        # logs_dir should be project root, so we create logs/[guid] subdirectory
        guid_logs_dir = os.path.join(logs_dir, "logs", memory_guid)
        os.makedirs(guid_logs_dir, exist_ok=True)
        
        # Create graph-specific log files
        llm_graph_manager_debug_file = os.path.join(guid_logs_dir, "ollama_graph_manager.log")
        llm_entity_resolver_debug_file = os.path.join(guid_logs_dir, "ollama_entity_resolver.log")
        relationship_extractor_debug_file = os.path.join(guid_logs_dir, "relationship_extractor.log")
        llm_relationship_extractor_debug_file = os.path.join(guid_logs_dir, "ollama_relationship_extractor.log")
        
        self.logger.debug(f"Graph manager debug log: {llm_graph_manager_debug_file}")
        self.logger.debug(f"Entity resolver debug log: {llm_entity_resolver_debug_file}")
        self.logger.debug(f"Relationship extractor debug log: {relationship_extractor_debug_file}")
        self.logger.debug(f"Ollama relationship extractor debug log: {llm_relationship_extractor_debug_file}")
        
        # Create dedicated logger for RelationshipExtractor
        self.relationship_extractor_logger = self._create_component_logger(
            "relationship_extractor", memory_guid, relationship_extractor_debug_file)
        
        # Get base configuration from the original service
        base_config = {}
        if hasattr(base_llm_service, 'config'):
            base_config = base_llm_service.config.copy()
        elif hasattr(base_llm_service, 'base_url'):
            # Extract common configuration
            base_config = {
                "base_url": getattr(base_llm_service, 'base_url', 'http://localhost:11434'),
                "model": getattr(base_llm_service, 'model', 'gemma3'),
                "temperature": getattr(base_llm_service, 'temperature', 0.7),
                "stream": getattr(base_llm_service, 'stream', False)
            }
        
        # Create dedicated LLM service for general graph operations
        graph_config = base_config.copy()
        graph_config.update({
            "debug": True,
            "debug_file": llm_graph_manager_debug_file,
            "debug_scope": "graph_manager",
            "console_output": False,
            "temperature": 0  # Use deterministic temperature for graph operations
        })
        
        # Create dedicated LLM service for entity resolution
        resolver_config = base_config.copy()
        resolver_config.update({
            "debug": True,
            "debug_file": llm_entity_resolver_debug_file,
            "debug_scope": "entity_resolver",
            "console_output": False,
            "temperature": 0  # Use deterministic temperature for resolution
        })
        
        # Create dedicated LLM service for relationship extraction
        relationship_llm_config = base_config.copy()
        relationship_llm_config.update({
            "debug": True,
            "debug_file": llm_relationship_extractor_debug_file,
            "debug_scope": "relationship_extractor",
            "console_output": False,
            "temperature": 0.1  # Use slightly higher temperature for relationship creativity
        })
        
        try:
            # Create the dedicated LLM services
            if isinstance(base_llm_service, OllamaService):
                self.graph_llm_service = OllamaService(graph_config)
                self.resolver_llm_service = OllamaService(resolver_config)
                self.relationship_llm_service = OllamaService(relationship_llm_config)
                self.logger.info("Created dedicated graph, resolver, and relationship LLM services with separate logging")
            else:
                # For other LLM service types, fall back to the original service
                self.logger.warning(f"Graph-specific logging not implemented for {type(base_llm_service).__name__}, using original service")
                self.graph_llm_service = base_llm_service
                self.resolver_llm_service = base_llm_service
                self.relationship_llm_service = base_llm_service
        except Exception as e:
            self.logger.error(f"Failed to create dedicated LLM services: {e}")
            self.logger.warning("Falling back to original LLM service")
            self.graph_llm_service = base_llm_service
            self.resolver_llm_service = base_llm_service
            self.relationship_llm_service = base_llm_service
    
    def _create_component_logger(self, component_name: str, memory_guid: str, log_file_path: str) -> logging.Logger:
        """
        Create a dedicated logger for a graph component.
        
        Args:
            component_name: Name of the component (e.g., 'relationship_extractor')
            memory_guid: Memory GUID for unique logger naming
            log_file_path: Path to the log file
            
        Returns:
            Configured logger instance
        """
        # Create logger name based on component and memory GUID
        logger_name = f"graph_memory.{component_name}.{memory_guid}"
        component_logger = logging.getLogger(logger_name)
        
        # Avoid duplicate handlers if logger already exists
        if component_logger.handlers:
            return component_logger
            
        # Set logger level
        component_logger.setLevel(logging.DEBUG)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        component_logger.addHandler(file_handler)
        
        # Prevent propagation to avoid duplicate logs in parent loggers
        component_logger.propagate = False
        
        self.logger.debug(f"Created dedicated logger for {component_name}: {logger_name} -> {log_file_path}")
        
        return component_logger
    
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
        if not self.entity_extractor or not self.relationship_extractor:
            self.logger.error("Entity extractors not available - missing LLM service or domain config")
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
            extracted_entities = self.entity_extractor.extract_entities_from_conversation(
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
                extracted_relationships = self.relationship_extractor.extract_relationships_from_conversation(
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
            "manager_type": "llm_centric",
            "has_entity_extractor": self.entity_extractor is not None,
            "has_relationship_extractor": self.relationship_extractor is not None,
        }
        
        if self.entity_extractor:
            stats["entity_extractor"] = self.entity_extractor.get_stats()
        
        if self.relationship_extractor:
            stats["relationship_extractor"] = self.relationship_extractor.get_stats()
        
        # Add LLM service information
        stats["llm_services"] = self.get_llm_services_info()
        
        return stats
    
    def get_llm_services_info(self) -> Dict[str, Any]:
        """Get information about all LLM services used by this GraphManager."""
        services_info = {}
        
        # Graph LLM service
        if hasattr(self, 'graph_llm_service') and self.graph_llm_service:
            services_info['graph_llm'] = {
                'service_type': type(self.graph_llm_service).__name__,
                'model': getattr(self.graph_llm_service, 'model', 'unknown'),
                'debug_scope': getattr(self.graph_llm_service, 'debug_scope', None),
                'debug_file': getattr(self.graph_llm_service, 'debug_file', None)
            }
        
        # Resolver LLM service
        if hasattr(self, 'resolver_llm_service') and self.resolver_llm_service:
            services_info['resolver_llm'] = {
                'service_type': type(self.resolver_llm_service).__name__,
                'model': getattr(self.resolver_llm_service, 'model', 'unknown'),
                'debug_scope': getattr(self.resolver_llm_service, 'debug_scope', None),
                'debug_file': getattr(self.resolver_llm_service, 'debug_file', None)
            }
        
        # Relationship LLM service
        if hasattr(self, 'relationship_llm_service') and self.relationship_llm_service:
            services_info['relationship_llm'] = {
                'service_type': type(self.relationship_llm_service).__name__,
                'model': getattr(self.relationship_llm_service, 'model', 'unknown'),
                'debug_scope': getattr(self.relationship_llm_service, 'debug_scope', None),
                'debug_file': getattr(self.relationship_llm_service, 'debug_file', None)
            }
        
        # Relationship ExtractorLogger information
        if hasattr(self, 'relationship_extractor_logger') and self.relationship_extractor_logger:
            services_info['relationship_extractor_logger'] = {
                'logger_name': self.relationship_extractor_logger.name,
                'logger_level': logging.getLevelName(self.relationship_extractor_logger.level),
                'has_handlers': len(self.relationship_extractor_logger.handlers) > 0,
                'log_files': [
                    handler.baseFilename for handler in self.relationship_extractor_logger.handlers 
                    if hasattr(handler, 'baseFilename')
                ]
            }
        
        # Check if services are distinct
        services_info['using_dedicated_services'] = self._are_services_distinct()
        
        return services_info
    
    def _are_services_distinct(self) -> Dict[str, bool]:
        """Check which services are using dedicated instances vs shared instances."""
        distinct_services = {}
        
        # Check if services are the same object (shared) or different (dedicated)
        base_service = getattr(self, 'graph_llm_service', None)
        resolver_service = getattr(self, 'resolver_llm_service', None)
        relationship_service = getattr(self, 'relationship_llm_service', None)
        
        distinct_services['resolver_dedicated'] = (
            resolver_service is not None and 
            base_service is not None and 
            resolver_service is not base_service
        )
        
        distinct_services['relationship_dedicated'] = (
            relationship_service is not None and 
            base_service is not None and 
            relationship_service is not base_service
        )
        
        return distinct_services
    
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
        if not self.entity_extractor:
            self.logger.error("Entity extractor not available")
            return {"entities": [], "relationships": [], "error": "Entity extractor not available"}
        
        # Use basic processing if EntityResolver is not available
        if not self.entity_resolver:
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
            self.logger.debug("Stage 1: Extracting entities from conversation with EntityExtractor")
            raw_entities = self.entity_extractor.extract_entities_from_conversation(
                conversation_text, digest_text)
            
            if not raw_entities:
                self.logger.info("No entities extracted from conversation")
                return results
            
            # All entities from EntityExtractor are now candidates for EntityResolver
            # EntityExtractor no longer does any matching - only extraction
            if raw_entities:
                # Stage 2: Convert to EntityResolver candidates
                self.logger.debug(f"Stage 2: Converting {len(raw_entities)} entities to resolver candidates")
                candidates = []
                for i, entity in enumerate(raw_entities):
                    candidate = {
                        "candidate_id": f"candidate_{i}_{entity.get('name', 'unknown')}",
                        "type": entity.get("type", "concept"),
                        "name": entity.get("name", ""),
                        "description": entity.get("description", ""),
                        "original_entity": entity  # Keep reference to original
                    }
                    candidates.append(candidate)
                
                # Stage 3: Resolve candidates using EntityResolver
                self.logger.debug(f"Stage 3: Resolving {len(candidates)} candidates with EntityResolver")
                resolutions = self.entity_resolver.resolve_candidates(
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
                                     f"confidence={resolution.get('confidence', 0.0)}, threshold={self.entity_resolver.confidence_threshold}, "
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
            
            if len(all_processed_entities) >= 2 and self.relationship_extractor:
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
                
                extracted_relationships = self.relationship_extractor.extract_relationships_from_conversation(
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
                "resolver_confidence_threshold": self.entity_resolver.confidence_threshold
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
    
    def _load_graph(self):
        """Load existing graph data from storage."""
        try:
            # Load nodes
            nodes_data = self.storage.load_nodes()
            for node_id, node_data in nodes_data.items():
                self.nodes[node_id] = GraphNode.from_dict(node_data)
            
            # Load edges
            edges_data = self.storage.load_edges()
            for edge_data in edges_data:
                self.edges.append(GraphEdge.from_dict(edge_data))
                
            self.logger.debug(f"Loaded {len(self.nodes)} nodes and {len(self.edges)} edges from storage")
            
        except Exception as e:
            self.logger.warning(f"Failed to load existing graph data: {e}")
            self.nodes = {}
            self.edges = []
    
    def _save_graph(self):
        """Save current graph state to storage."""
        try:
            # Save nodes
            nodes_data = {node_id: node.to_dict() for node_id, node in self.nodes.items()}
            self.storage.save_nodes(nodes_data)
            
            # Save edges
            edges_data = [edge.to_dict() for edge in self.edges]
            self.storage.save_edges(edges_data)
            
            # Update metadata
            metadata = {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "last_updated": datetime.now().isoformat()
            }
            self.storage.save_metadata(metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to save graph data: {e}")
    
    def add_or_update_node(self, name: str, node_type: str, description: str, 
                          confidence: float = 1.0, conversation_guid: str = None, 
                          **attributes) -> Tuple[GraphNode, bool]:
        """Add a new node or update an existing one."""
        try:
            # Check for existing node with same name and type
            existing_node = None
            for node in self.nodes.values():
                if node.name.lower() == name.lower() and node.type == node_type:
                    existing_node = node
                    break
            
            if existing_node:
                # Update existing node
                existing_node.description = description
                existing_node.mention_count += 1
                existing_node.updated_at = datetime.now().isoformat()
                
                # Update conversation history if provided
                if conversation_guid:
                    if "conversation_history_guids" not in existing_node.attributes:
                        existing_node.attributes["conversation_history_guids"] = []
                    if conversation_guid not in existing_node.attributes["conversation_history_guids"]:
                        existing_node.attributes["conversation_history_guids"].append(conversation_guid)
                
                # Update attributes
                existing_node.attributes.update(attributes)
                
                # Update embedding if description changed
                if self.embeddings_manager:
                    try:
                        embedding_text = f"{existing_node.name} {existing_node.description}"
                        
                        # Update in embeddings manager
                        entity_metadata = {
                            "entity_id": existing_node.id,
                            "entity_name": existing_node.name,
                            "entity_type": existing_node.type,
                            "source": "graph_entity"
                        }
                        self.embeddings_manager.add_embedding(
                            text_or_item=embedding_text,
                            metadata=entity_metadata
                        )
                        self.logger.debug(f"Updated embedding for existing entity: {existing_node.name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to update embedding for entity {existing_node.name}: {e}")
                
                self._save_graph()
                return existing_node, False
            else:
                # Create new node
                node_id = f"{node_type}_{name.lower().replace(' ', '_')}_{str(uuid.uuid4())[:8]}"
                
                new_attributes = attributes.copy()
                if conversation_guid:
                    new_attributes["conversation_history_guids"] = [conversation_guid]
                
                new_node = GraphNode(
                    node_id=node_id,
                    name=name,
                    node_type=node_type,
                    description=description,
                    attributes=new_attributes
                )
                
                # Generate embedding for the entity for RAG searches
                if self.embeddings_manager:
                    try:
                        # Use name + description for embedding
                        embedding_text = f"{name} {description}"
                        
                        # Also add to embeddings manager with proper metadata for RAG
                        entity_metadata = {
                            "entity_id": node_id,
                            "entity_name": name,
                            "entity_type": node_type,
                            "source": "graph_entity"
                        }
                        self.embeddings_manager.add_embedding(
                            text_or_item=embedding_text,
                            metadata=entity_metadata
                        )
                        self.logger.debug(f"Generated embedding for new entity: {name} ({node_type})")
                    except Exception as e:
                        self.logger.warning(f"Failed to generate embedding for entity {name}: {e}")
                
                self.nodes[node_id] = new_node
                self._save_graph()
                return new_node, True
                
        except Exception as e:
            self.logger.error(f"Error adding/updating node: {e}")
            # Return a minimal node as fallback
            fallback_id = f"{node_type}_{str(uuid.uuid4())[:8]}"
            fallback_node = GraphNode(fallback_id, name, node_type, description)
            return fallback_node, True
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by its ID."""
        return self.nodes.get(node_id)
    
    def add_edge(self, from_node_id: str, to_node_id: str, relationship: str, 
                evidence: str = "", confidence: float = 1.0) -> Optional[GraphEdge]:
        """Add an edge between two nodes."""
        try:
            # Check if edge already exists
            existing_edge = self._find_edge(from_node_id, to_node_id, relationship)
            if existing_edge:
                # Update existing edge
                existing_edge.confidence = max(existing_edge.confidence, confidence)
                existing_edge.evidence = evidence
                existing_edge.updated_at = datetime.now().isoformat()
                self._save_graph()
                return existing_edge
            
            # Create new edge
            edge_id = f"edge_{str(uuid.uuid4())[:8]}"
            new_edge = GraphEdge(
                edge_id=edge_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                relationship=relationship,
                evidence=evidence,
                confidence=confidence
            )
            
            self.edges.append(new_edge)
            self._save_graph()
            return new_edge
            
        except Exception as e:
            self.logger.error(f"Error adding edge: {e}")
            return None
    
    def _find_edge(self, from_node_id: str, to_node_id: str, relationship: str) -> Optional[GraphEdge]:
        """Find an existing edge between two nodes with a specific relationship."""
        for edge in self.edges:
            if (edge.from_node_id == from_node_id and 
                edge.to_node_id == to_node_id and 
                edge.relationship == relationship):
                return edge
        return None
    
    def query_for_context(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Query the graph for relevant context."""
        if not self.embeddings_manager:
            # Simple text matching fallback
            results = []
            query_lower = query.lower()
            for node in self.nodes.values():
                if (query_lower in node.name.lower() or 
                    query_lower in node.description.lower()):
                    results.append({
                        'name': node.name,
                        'type': node.type,
                        'description': node.description,
                        'relevance_score': 1.0
                    })
                    if len(results) >= max_results:
                        break
            return results
        
        try:
            # Use embeddings for semantic search
            query_embedding = self.embeddings_manager.generate_embedding(query)
            similarities = []
            
            for node in self.nodes.values():
                if node.embedding:
                    similarity = self._cosine_similarity(query_embedding, node.embedding)
                    similarities.append((similarity, node))
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[0], reverse=True)
            results = []
            for similarity, node in similarities[:max_results]:
                results.append({
                    'name': node.name,
                    'type': node.type,
                    'description': node.description,
                    'relevance_score': similarity
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in graph query: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            import numpy as np
            
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            
        except Exception:
            # Fallback to simple calculation
            dot_product = sum(x * y for x, y in zip(vec1, vec2))
            magnitude1 = sum(x * x for x in vec1) ** 0.5
            magnitude2 = sum(x * x for x in vec2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2) 