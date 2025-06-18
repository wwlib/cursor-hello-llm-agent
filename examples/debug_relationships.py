#!/usr/bin/env python3
"""
Debug Relationship Extraction

This script tests relationship extraction in isolation to understand why it works
in the standalone example but fails in the memory manager integration.
"""

import os
import sys
import logging
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.llm_ollama import OllamaService
from memory.graph_memory.relationship_extractor import RelationshipExtractor
sys.path.insert(0, os.path.dirname(__file__))
from domain_configs import DND_CONFIG

def setup_logging():
    """Setup debug logging"""
    logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    logger.info("Starting Relationship Extraction Debug")
    
    # Initialize LLM service exactly like memory manager
    llm_config = {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "temperature": 0.7,
        "debug": True,  # Force debug mode
        "debug_file": "debug_relationships.log",
        "debug_scope": "relationship_debug",
        "console_output": True
    }
    
    llm_service = OllamaService(llm_config)
    logger.info(f"LLM service initialized with model: {llm_config['model']}")
    
    # Initialize RelationshipExtractor exactly like memory manager
    relationship_extractor = RelationshipExtractor(
        llm_service=llm_service,
        domain_config=DND_CONFIG,
        logger=logger
    )
    logger.info("RelationshipExtractor initialized")
    
    # Test Case 1: Standalone example format (known working)
    logger.info("\n" + "="*60)
    logger.info("TEST CASE 1: Standalone Example Format (Should Work)")
    logger.info("="*60)
    
    standalone_segments = [
        {
            "text": "Elena is a powerful Mayor who manages Haven, the central settlement",
            "importance": 4,
            "type": "information",
            "entities": [
                {"name": "Elena", "type": "character", "description": "A powerful Mayor"},
                {"name": "Haven", "type": "location", "description": "The central settlement"}
            ]
        },
        {
            "text": "Sara is the Captain of Riverwatch who defends the eastern settlement",
            "importance": 4,
            "type": "information",
            "entities": [
                {"name": "Sara", "type": "character", "description": "Captain of Riverwatch"},
                {"name": "Riverwatch", "type": "location", "description": "The eastern settlement"}
            ]
        },
        {
            "text": "Elena and Sara coordinate defense strategies between Haven and Riverwatch",
            "importance": 5,
            "type": "information",
            "entities": [
                {"name": "Elena", "type": "character", "description": "A powerful Mayor"},
                {"name": "Sara", "type": "character", "description": "Captain of Riverwatch"},
                {"name": "Haven", "type": "location", "description": "The central settlement"},
                {"name": "Riverwatch", "type": "location", "description": "The eastern settlement"}
            ]
        }
    ]
    
    # Add IDs to segments
    for i, segment in enumerate(standalone_segments):
        segment["id"] = f"standalone_seg_{i}"
    
    # Build entities_by_segment (exactly like memory manager)
    entities_by_segment = {}
    for segment in standalone_segments:
        segment_id = segment["id"]
        entities = segment.get("entities", [])
        entities_by_segment[segment_id] = entities
    
    logger.info(f"Standalone segments: {len(standalone_segments)}")
    logger.info(f"Entities by segment: {entities_by_segment}")
    
    try:
        logger.info("About to call extract_relationships_from_segments...")
        standalone_relationships = relationship_extractor.extract_relationships_from_segments(
            standalone_segments, entities_by_segment
        )
        logger.info(f"Standalone relationships found: {len(standalone_relationships)}")
        for rel in standalone_relationships:
            logger.info(f"  - {rel.get('from_entity')} {rel.get('relationship')} {rel.get('to_entity')}")
    except Exception as e:
        logger.error(f"Standalone extraction failed: {e}")
    
    # Stop here for now to focus on first test
    return
    
    # Test Case 2: Memory Manager format (currently failing)
    logger.info("\n" + "="*60)
    logger.info("TEST CASE 2: Memory Manager Format (Currently Failing)")
    logger.info("="*60)
    
    # Simulate exactly what memory manager creates
    memory_manager_segments = [
        {
            "id": "seg_0",
            "text": "Elena is a powerful Mayor who manages Haven, the central settlement",
            "entities": [
                {"name": "Elena", "type": "character", "description": "A powerful Mayor", "attributes": {}},
                {"name": "Haven", "type": "location", "description": "The central settlement", "attributes": {}}
            ],
            "importance": 4,
            "type": "information"
        },
        {
            "id": "seg_1", 
            "text": "Sara is the Captain of Riverwatch who defends the eastern settlement",
            "entities": [
                {"name": "Sara", "type": "character", "description": "Captain of Riverwatch", "attributes": {}},
                {"name": "Riverwatch", "type": "location", "description": "The eastern settlement", "attributes": {}}
            ],
            "importance": 4,
            "type": "information"
        }
    ]
    
    # Build entities_by_segment (exactly like memory manager)
    mm_entities_by_segment = {}
    for segment in memory_manager_segments:
        segment_id = segment["id"]
        entities = segment.get("entities", [])
        mm_entities_by_segment[segment_id] = entities
    
    logger.info(f"Memory manager segments: {len(memory_manager_segments)}")
    logger.info(f"MM Entities by segment: {mm_entities_by_segment}")
    
    try:
        mm_relationships = relationship_extractor.extract_relationships_from_segments(
            memory_manager_segments, mm_entities_by_segment
        )
        logger.info(f"Memory manager relationships found: {len(mm_relationships)}")
        for rel in mm_relationships:
            logger.info(f"  - {rel.get('from_entity')} {rel.get('relationship')} {rel.get('to_entity')}")
    except Exception as e:
        logger.error(f"Memory manager extraction failed: {e}")
    
    # Test Case 3: Single segment with multiple entities (memory manager typical case)
    logger.info("\n" + "="*60)
    logger.info("TEST CASE 3: Single Segment Multi-Entity (Memory Manager Typical)")
    logger.info("="*60)
    
    single_segment = [
        {
            "id": "seg_0",
            "text": "Elena the Mayor of Haven works closely with Sara the Captain of Riverwatch. They coordinate defense strategies.",
            "entities": [
                {"name": "Elena", "type": "character", "description": "Mayor of Haven", "attributes": {}},
                {"name": "Haven", "type": "location", "description": "Central settlement", "attributes": {}},
                {"name": "Sara", "type": "character", "description": "Captain of Riverwatch", "attributes": {}},
                {"name": "Riverwatch", "type": "location", "description": "Eastern settlement", "attributes": {}}
            ],
            "importance": 5,
            "type": "information"
        }
    ]
    
    single_entities_by_segment = {}
    for segment in single_segment:
        segment_id = segment["id"]
        entities = segment.get("entities", [])
        single_entities_by_segment[segment_id] = entities
    
    logger.info(f"Single segment: {len(single_segment)}")
    logger.info(f"Single entities by segment: {single_entities_by_segment}")
    
    try:
        single_relationships = relationship_extractor.extract_relationships_from_segments(
            single_segment, single_entities_by_segment
        )
        logger.info(f"Single segment relationships found: {len(single_relationships)}")
        for rel in single_relationships:
            logger.info(f"  - {rel.get('from_entity')} {rel.get('relationship')} {rel.get('to_entity')}")
    except Exception as e:
        logger.error(f"Single segment extraction failed: {e}")
    
    logger.info("\nDebug completed!")

if __name__ == "__main__":
    main()