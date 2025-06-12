"""
Entity Resolver

Dedicated entity resolution using structured prompts and RAG-based matching.

This module implements the recommended entity resolution approach from the 
README-entity-resolution-plan.md, providing both batch and individual 
candidate processing with confidence-based decision making.

Example::

    from src.memory.graph_memory.entity_resolver import EntityResolver
    
    # Initialize resolver
    resolver = EntityResolver(
        llm_service=llm_service,
        embeddings_manager=embeddings_manager,
        storage_path="graph_data"
    )
    
    # Resolve candidates against existing nodes
    candidates = [
        {"candidate_id": "candidate_1", "type": "character", "description": "..."},
        {"candidate_id": "candidate_2", "type": "location", "description": "..."}
    ]
    
    resolutions = resolver.resolve_candidates(candidates, process_individually=True)

Attributes:
    llm_service: LLM service for resolution prompts.
    embeddings_manager: For RAG-based candidate selection.
    storage: Graph storage for existing node data.
    confidence_threshold (float): Minimum confidence for auto-matching (default: 0.8).
"""

import json
import os
from typing import Dict, List, Any, Optional
import logging

from .graph_storage import GraphStorage


class EntityResolver:
    """Dedicated entity resolution using structured prompts and RAG matching.
    
    EntityResolver implements the recommended two-pass entity resolution process:
    
    1. RAG-based candidate selection for each entity
    2. LLM-driven matching with confidence scoring
    3. One-at-a-time or batch processing options
    4. Confidence-based decision making
    
    The resolver uses the structured entity_resolution.prompt template for
    consistent output format with confidence scores.
    
    Attributes:
        llm_service: LLM service for generating resolution prompts.
        embeddings_manager: For semantic similarity search of existing entities.
        storage: Graph storage for loading existing node data.
        confidence_threshold: Minimum confidence for automatic matching.
        logger: Logger instance for debugging and monitoring.
    
    Example::
    
        # Initialize resolver with services
        resolver = EntityResolver(
            llm_service=gemma_service,
            embeddings_manager=embeddings_manager,
            storage_path="memory_files/graph_data"
        )
        
        # Process candidates individually for higher accuracy
        candidates = [
            {"candidate_id": "c1", "type": "character", "description": "A fire wizard"},
            {"candidate_id": "c2", "type": "location", "description": "Ancient ruins"}
        ]
        
        resolutions = resolver.resolve_candidates(
            candidates, 
            process_individually=True,
            confidence_threshold=0.85
        )
        
        # Process resolutions
        for resolution in resolutions:
            if resolution["resolved_node_id"] == "<NEW>":
                print(f"Creating new entity: {resolution['candidate_id']}")
            else:
                print(f"Matched to existing: {resolution['resolved_node_id']} "
                      f"(confidence: {resolution['confidence']})")
    
    Note:
        Requires configured LLM service and graph storage.
        Embeddings manager is optional but recommended for RAG functionality.
    """
    
    def __init__(self, llm_service, embeddings_manager=None, storage_path: str = None,
                 confidence_threshold: float = 0.8, logger=None):
        """Initialize entity resolver with services and configuration.
        
        Args:
            llm_service: LLM service instance for resolution prompts.
                Must support text generation with structured prompts.
            embeddings_manager: Optional embeddings manager for RAG-based
                candidate selection. If None, resolution relies only on LLM.
            storage_path: Path to graph storage directory.
                If None, uses default path based on current directory.
            confidence_threshold: Minimum confidence score (0.0-1.0) for
                automatic entity matching. Default 0.8.
            logger: Logger instance for debugging and monitoring.
                If None, creates a default logger.
                   
        Example::
        
            # Full configuration
            resolver = EntityResolver(
                llm_service=llm_service,
                embeddings_manager=embeddings_manager,
                storage_path="/path/to/graph_data",
                confidence_threshold=0.85,
                logger=custom_logger
            )
            
            # Minimal configuration (no RAG)
            resolver = EntityResolver(llm_service=llm_service)
        """
        self.llm_service = llm_service
        self.embeddings_manager = embeddings_manager
        self.confidence_threshold = confidence_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize graph storage
        if storage_path:
            self.storage = GraphStorage(storage_path)
        else:
            # Default path
            default_path = os.path.join(os.getcwd(), "graph_data")
            self.storage = GraphStorage(default_path)
        
        # Load resolution prompt template
        self.resolution_template = self._load_resolution_template()
    
    def _load_resolution_template(self) -> str:
        """Load the entity resolution prompt template.
        
        Returns:
            Prompt template string with placeholders for existing node data
            and candidate nodes.
            
        Note:
            Template must be in templates/entity_resolution.prompt relative
            to this module's location.
        """
        try:
            template_path = os.path.join(os.path.dirname(__file__), 
                                       'templates', 'entity_resolution.prompt')
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error loading resolution template: {e}")
            # Fallback minimal template
            return """You are a Node ID Resolver. Analyze existing nodes and candidates.
Output format: [candidate_id, existing_node_id, resolution_justification, confidence]

**Existing Node Data:**
{{existing_node_data}}

**Candidate Nodes:**
{{candidate_nodes}}

**Resolved Nodes:**"""
    
    def resolve_candidates(self, candidates: List[Dict[str, Any]], 
                          process_individually: bool = False,
                          confidence_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Resolve candidate entities against existing nodes.
        
        Main entry point for entity resolution. Processes candidates using either
        batch or individual resolution modes with confidence-based decision making.
        
        Args:
            candidates: List of candidate entity dictionaries.
                Each candidate should contain:
                - candidate_id (str): Unique identifier for the candidate
                - type (str): Entity type (character, location, etc.)
                - description (str): Entity description for matching
                - name (str, optional): Entity name if available
                
            process_individually: If True, process candidates one at a time
                for higher accuracy. If False, process in batch mode.
                Default False for compatibility.
                
            confidence_threshold: Override default confidence threshold.
                If None, uses instance default.
                     
        Returns:
            List of resolution dictionaries, each containing:
            - candidate_id (str): Original candidate identifier
            - resolved_node_id (str): Existing node ID or "<NEW>"
            - resolution_justification (str): Explanation of matching decision
            - confidence (float): Confidence score (0.0-1.0)
            - auto_matched (bool): Whether resolution exceeded confidence threshold
            
        Example::
        
            candidates = [
                {
                    "candidate_id": "candidate_001",
                    "type": "character",
                    "name": "Fire Wizard",
                    "description": "A powerful wizard specializing in fire magic"
                }
            ]
            
            resolutions = resolver.resolve_candidates(candidates, process_individually=True)
            
            for resolution in resolutions:
                if resolution["auto_matched"]:
                    print(f"High confidence match: {resolution['resolved_node_id']}")
                elif resolution["resolved_node_id"] != "<NEW>":
                    print(f"Low confidence match: {resolution['resolved_node_id']}")
                else:
                    print(f"No match found, creating new entity")
            
        Note:
            Individual processing mode provides higher accuracy but takes longer.
            Batch mode is faster but may have lower accuracy for complex cases.
        """
        if not candidates:
            return []
        
        # Use override threshold if provided
        threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        
        if process_individually:
            return self._resolve_individually(candidates, threshold)
        else:
            return self._resolve_batch(candidates, threshold)
    
    def _resolve_individually(self, candidates: List[Dict[str, Any]], 
                            confidence_threshold: float) -> List[Dict[str, Any]]:
        """Process candidates one at a time for higher accuracy.
        
        Implements the recommended one-at-a-time processing approach from
        the entity resolution plan. Each candidate is processed with its
        own RAG context and LLM resolution call.
        
        Args:
            candidates: List of candidate dictionaries to resolve.
            confidence_threshold: Minimum confidence for auto-matching.
            
        Returns:
            List of resolution results with confidence scores.
            
        Note:
            This method provides the highest accuracy by allowing the LLM
            to focus on one candidate at a time with targeted RAG context.
        """
        resolutions = []
        resolved_context = []  # Track resolved entities for subsequent candidates
        
        for candidate in candidates:
            try:
                # Get RAG candidates for this specific entity
                rag_candidates = self._get_rag_candidates_for_entity(candidate)
                
                # Combine with previously resolved entities in this session
                existing_context = rag_candidates + resolved_context
                
                # Resolve single candidate
                resolution = self._resolve_single_candidate(candidate, existing_context, confidence_threshold)
                resolutions.append(resolution)
                
                # Add to resolved context if it was matched to existing entity
                if resolution["resolved_node_id"] != "<NEW>":
                    resolved_context.append({
                        "existing_node_id": resolution["resolved_node_id"],
                        "type": candidate.get("type", ""),
                        "description": candidate.get("description", "")
                    })
                
                self.logger.debug(f"Resolved candidate {candidate.get('candidate_id')}: "
                                f"{resolution['resolved_node_id']} (confidence: {resolution['confidence']})")
                
            except Exception as e:
                self.logger.error(f"Error resolving candidate {candidate.get('candidate_id')}: {e}")
                # Fallback: mark as new entity
                resolutions.append({
                    "candidate_id": candidate.get("candidate_id", "unknown"),
                    "resolved_node_id": "<NEW>",
                    "resolution_justification": f"Error during resolution: {e}",
                    "confidence": 0.0,
                    "auto_matched": False
                })
        
        return resolutions
    
    def _resolve_batch(self, candidates: List[Dict[str, Any]], 
                      confidence_threshold: float) -> List[Dict[str, Any]]:
        """Process all candidates in a single batch resolution.
        
        Batch processing mode that resolves multiple candidates simultaneously.
        Faster than individual processing but may have lower accuracy for
        complex resolution scenarios.
        
        Args:
            candidates: List of candidate dictionaries to resolve.
            confidence_threshold: Minimum confidence for auto-matching.
            
        Returns:
            List of resolution results with confidence scores.
            
        Note:
            Batch mode is more efficient but the LLM must consider multiple
            candidates simultaneously, which may reduce accuracy.
        """
        try:
            # Get combined RAG context for all candidates
            all_rag_candidates = []
            for candidate in candidates:
                rag_candidates = self._get_rag_candidates_for_entity(candidate)
                all_rag_candidates.extend(rag_candidates)
            
            # Remove duplicates while preserving order
            seen_ids = set()
            unique_existing = []
            for entity in all_rag_candidates:
                entity_id = entity.get("existing_node_id", "")
                if entity_id and entity_id not in seen_ids:
                    seen_ids.add(entity_id)
                    unique_existing.append(entity)
            
            # Resolve all candidates together
            return self._resolve_candidates_batch(candidates, unique_existing, confidence_threshold)
            
        except Exception as e:
            self.logger.error(f"Error in batch resolution: {e}")
            # Fallback: mark all as new entities
            return [{
                "candidate_id": candidate.get("candidate_id", "unknown"),
                "resolved_node_id": "<NEW>",
                "resolution_justification": f"Error during batch resolution: {e}",
                "confidence": 0.0,
                "auto_matched": False
            } for candidate in candidates]
    
    def _get_rag_candidates_for_entity(self, candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use RAG to find existing entities similar to the candidate.
        
        Performs semantic similarity search to find existing entities that
        might match the candidate entity. Filters by entity type for relevance.
        
        Args:
            candidate: Candidate entity with type and description.
            
        Returns:
            List of similar existing entities with node IDs and descriptions.
            
        Note:
            Returns empty list if embeddings_manager is not available.
            RAG search is filtered by entity type for relevance.
        """
        if not self.embeddings_manager:
            self.logger.debug("No embeddings manager available for RAG")
            return []
        
        try:
            # Create search query from candidate
            search_query = candidate.get("description", "")
            if candidate.get("name"):
                search_query = f"{candidate['name']} {search_query}"
            
            if not search_query.strip():
                return []
            
            # Perform semantic search
            similar_results = self.embeddings_manager.search(
                query=search_query,
                k=5  # max_results parameter name is 'k' in search method
            )
            
            # Filter by entity type and convert to resolution format
            candidate_type = candidate.get("type", "")
            rag_candidates = []
            
            for result in similar_results:
                # Check if result has entity type metadata
                metadata = result.get("metadata", {})
                if metadata.get("entity_type") == candidate_type:
                    entity_name = metadata.get("entity_name", "")
                    entity_description = result.get("text", "")
                    # Get the actual node ID from metadata
                    actual_node_id = metadata.get("entity_id", "")
                    
                    if entity_name and entity_description and actual_node_id:
                        rag_candidates.append({
                            "existing_node_id": actual_node_id,  # Use actual node ID from graph storage
                            "type": candidate_type,
                            "description": entity_description
                        })
            
            self.logger.debug(f"RAG found {len(rag_candidates)} candidates for {candidate.get('candidate_id')}")
            return rag_candidates[:3]  # Limit to top 3 for prompt efficiency
            
        except Exception as e:
            self.logger.error(f"Error in RAG candidate selection: {e}")
            return []
    
    def _resolve_single_candidate(self, candidate: Dict[str, Any], 
                                 existing_context: List[Dict[str, Any]],
                                 confidence_threshold: float) -> Dict[str, Any]:
        """Resolve a single candidate using LLM with structured prompt.
        
        Uses the entity_resolution.prompt template to resolve one candidate
        against a list of existing entities with confidence scoring.
        
        Args:
            candidate: Single candidate entity to resolve.
            existing_context: List of existing entities for comparison.
            confidence_threshold: Minimum confidence for auto-matching.
            
        Returns:
            Resolution dictionary with confidence score and auto-match flag.
        """
        # Format existing node data
        existing_node_data = ""
        for entity in existing_context:
            existing_node_data += f"  existing_node_id: \"{entity.get('existing_node_id', '')}\"\n"
            existing_node_data += f"  type: \"{entity.get('type', '')}\"\n"
            existing_node_data += f"  description: \"{entity.get('description', '')}\"\n\n"
        
        # Format candidate data
        candidate_data = json.dumps([{
            "candidate_id": candidate.get("candidate_id", ""),
            "type": candidate.get("type", ""),
            "description": candidate.get("description", "")
        }], indent=2)
        
        # Build prompt from template
        prompt = self.resolution_template.replace("{{existing_node_data}}", existing_node_data)
        prompt = prompt.replace("{{candidate_nodes}}", candidate_data)
        
        # Get LLM resolution
        try:
            response = self.llm_service.generate(prompt)
            resolutions = self._parse_resolution_response(response)
            
            if resolutions and len(resolutions) > 0:
                resolution = resolutions[0]
                # Add auto-match flag based on confidence
                resolution["auto_matched"] = resolution.get("confidence", 0.0) >= confidence_threshold
                return resolution
            else:
                # Fallback if parsing failed
                return {
                    "candidate_id": candidate.get("candidate_id", ""),
                    "resolved_node_id": "<NEW>",
                    "resolution_justification": "Failed to parse LLM response",
                    "confidence": 0.0,
                    "auto_matched": False
                }
                
        except Exception as e:
            self.logger.error(f"Error in LLM resolution: {e}")
            return {
                "candidate_id": candidate.get("candidate_id", ""),
                "resolved_node_id": "<NEW>",
                "resolution_justification": f"LLM error: {e}",
                "confidence": 0.0,
                "auto_matched": False
            }
    
    def _resolve_candidates_batch(self, candidates: List[Dict[str, Any]], 
                                 existing_context: List[Dict[str, Any]],
                                 confidence_threshold: float) -> List[Dict[str, Any]]:
        """Resolve multiple candidates in batch using structured prompt.
        
        Similar to single candidate resolution but processes multiple candidates
        in one LLM call for efficiency.
        
        Args:
            candidates: List of candidate entities to resolve.
            existing_context: List of existing entities for comparison.
            confidence_threshold: Minimum confidence for auto-matching.
            
        Returns:
            List of resolution results with confidence scores.
        """
        # Format existing node data
        existing_node_data = ""
        for entity in existing_context:
            existing_node_data += f"  existing_node_id: \"{entity.get('existing_node_id', '')}\"\n"
            existing_node_data += f"  type: \"{entity.get('type', '')}\"\n"
            existing_node_data += f"  description: \"{entity.get('description', '')}\"\n\n"
        
        # Format candidate data
        candidate_data = json.dumps([{
            "candidate_id": candidate.get("candidate_id", ""),
            "type": candidate.get("type", ""),
            "description": candidate.get("description", "")
        } for candidate in candidates], indent=2)
        
        # Build prompt from template
        prompt = self.resolution_template.replace("{{existing_node_data}}", existing_node_data)
        prompt = prompt.replace("{{candidate_nodes}}", candidate_data)
        
        # Get LLM resolution
        try:
            response = self.llm_service.generate(prompt)
            resolutions = self._parse_resolution_response(response)
            
            # Add auto-match flags and ensure all candidates are covered
            for resolution in resolutions:
                resolution["auto_matched"] = resolution.get("confidence", 0.0) >= confidence_threshold
            
            # Handle missing candidates (fallback)
            resolved_ids = {r.get("candidate_id") for r in resolutions}
            for candidate in candidates:
                candidate_id = candidate.get("candidate_id", "")
                if candidate_id not in resolved_ids:
                    resolutions.append({
                        "candidate_id": candidate_id,
                        "resolved_node_id": "<NEW>",
                        "resolution_justification": "Not resolved by LLM",
                        "confidence": 0.0,
                        "auto_matched": False
                    })
            
            return resolutions
            
        except Exception as e:
            self.logger.error(f"Error in batch LLM resolution: {e}")
            # Fallback: mark all as new
            return [{
                "candidate_id": candidate.get("candidate_id", ""),
                "resolved_node_id": "<NEW>",
                "resolution_justification": f"Batch resolution error: {e}",
                "confidence": 0.0,
                "auto_matched": False
            } for candidate in candidates]
    
    def _parse_resolution_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM resolution response to extract resolution data.
        
        Handles multiple LLM response formats:
        1. Array of tuples: [["candidate_id", "node_id", "justification", confidence], ...]
        2. Array of objects: [{"candidate_id": "...", "existing_node_id": "...", ...}, ...]
        3. Responses wrapped in code blocks with ```json
        
        Args:
            response: Raw LLM response text containing resolution data.
            
        Returns:
            List of resolution dictionaries with standardized fields.
        
        Note:
            Prioritizes robustness over strict format enforcement to handle
            varying LLM response styles. Logs warnings for unexpected formats.
        """
        try:
            # Look for JSON in code blocks first (common LLM behavior)
            import re
            code_block_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL | re.IGNORECASE)
            if code_block_match:
                json_str = code_block_match.group(1)
            else:
                # Fallback to any JSON array in the response
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if not json_match:
                    self.logger.warning("No JSON array found in resolution response")
                    return []
                json_str = json_match.group(0)
            
            parsed_data = json.loads(json_str)
            
            resolutions = []
            for item in parsed_data:
                if isinstance(item, list) and len(item) >= 3:
                    # Handle tuple format: [candidate_id, existing_node_id, justification, confidence]
                    candidate_id = str(item[0]) if len(item) > 0 else ""
                    resolved_node_id = str(item[1]) if len(item) > 1 else "<NEW>"
                    justification = str(item[2]) if len(item) > 2 else ""
                    confidence = float(item[3]) if len(item) > 3 else 0.0
                    
                    resolutions.append({
                        "candidate_id": candidate_id,
                        "resolved_node_id": resolved_node_id,
                        "resolution_justification": justification,
                        "confidence": confidence
                    })
                    
                elif isinstance(item, dict):
                    # Handle object format: {"candidate_id": "...", "existing_node_id": "...", ...}
                    candidate_id = str(item.get("candidate_id", ""))
                    resolved_node_id = str(item.get("existing_node_id", "<NEW>"))
                    justification = str(item.get("resolution_justification", ""))
                    confidence = float(item.get("confidence", 0.0))
                    
                    resolutions.append({
                        "candidate_id": candidate_id,
                        "resolved_node_id": resolved_node_id,
                        "resolution_justification": justification,
                        "confidence": confidence
                    })
                else:
                    self.logger.warning(f"Unexpected resolution item format: {type(item)} - {item}")
            
            self.logger.debug(f"Successfully parsed {len(resolutions)} resolutions from LLM response")
            return resolutions
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse resolution JSON: {e}")
            self.logger.debug(f"Problematic response: {response[:500]}...")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing resolution response: {e}")
            return []