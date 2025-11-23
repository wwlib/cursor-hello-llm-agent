#!/usr/bin/env python3
"""
Real LLM integration tests for RelationshipExtractor.

Tests the RelationshipExtractor with actual Ollama LLM calls to validate:
- Relationship extraction from conversation text with entity context
- Domain-specific relationship type detection
- LLM reasoning for relationship inference
- Confidence scoring and evidence generation
- Relationship validation

Requires running Ollama service with environment variables:
- OLLAMA_BASE_URL
- OLLAMA_MODEL
- OLLAMA_EMBED_MODEL
"""

import sys
import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from memory.graph_memory.relationship_extractor import RelationshipExtractor
from ai.llm_ollama import OllamaService
from utils.logging_config import LoggingConfig

# Import domain config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sample_data'))
from domain_configs import DND_CONFIG

# Test GUID for logging
TEST_GUID = "test_relationship_extractor_real_llm"

# Create a session-scoped UUID that can be shared between fixtures
@pytest.fixture(scope="session")
def test_run_uuid():
    """Generate a unique UUID for this test run."""
    import uuid
    return uuid.uuid4().hex[:8]


def setup_ollama_service(test_uuid=None):
    """Set up real Ollama LLM service using environment variables."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma3")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
    
    print(f"Setting up Ollama service:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print(f"  Embedding Model: {embed_model}")
    
    # Use LoggingConfig for consistent logging
    if test_uuid:
        guid = f"{TEST_GUID}_{test_uuid}"
    else:
        guid = TEST_GUID
    
    llm_logger = LoggingConfig.get_component_file_logger(
        guid,
        "ollama_relationship_extractor",
        log_to_console=False
    )
    
    print(f"  Logs directory: {LoggingConfig.get_log_base_dir(guid)}")
    
    # Configure LLM service with logger
    llm_config = {
        "base_url": base_url,
        "model": model,
        "logger": llm_logger
    }
    
    return OllamaService(llm_config)


@pytest.fixture
def temp_storage_path(test_run_uuid):
    """Create temporary storage directory for testing in tests/test_files/tmp."""
    # Use the specific directory mentioned in the README
    project_root = Path(__file__).parent.parent.parent  # Go up to project root
    temp_dir = project_root / "tests" / "test_files" / "tmp"
    
    # Create the directory if it doesn't exist
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a unique subdirectory for this test run using the shared UUID
    test_run_dir = temp_dir / f"relationship_extractor_test_{test_run_uuid}"
    test_run_dir.mkdir(exist_ok=True)
    
    yield str(test_run_dir)
    
    # Optional: Clean up after tests (or leave for analysis)
    # shutil.rmtree(test_run_dir, ignore_errors=True)


@pytest.fixture
def ollama_service(test_run_uuid):
    """Create real Ollama service for testing."""
    return setup_ollama_service(test_uuid=test_run_uuid)


@pytest.fixture
def relationship_extractor(ollama_service, test_run_uuid):
    """Create RelationshipExtractor with real LLM service and DND domain config."""
    # Use LoggingConfig for consistent logging
    if test_run_uuid:
        guid = f"{TEST_GUID}_{test_run_uuid}"
    else:
        guid = TEST_GUID
    
    extractor_logger = LoggingConfig.get_component_file_logger(
        guid,
        "relationship_extractor",
        log_to_console=False
    )
    
    return RelationshipExtractor(
        llm_service=ollama_service,
        domain_config=DND_CONFIG,
        logger=extractor_logger
    )


@pytest.fixture
def sample_entities():
    """Sample entities for relationship extraction testing."""
    return [
        {
            "id": "character_elena_001",
            "name": "Elena",
            "type": "character",
            "description": "Mayor of Haven who protects the valley's inhabitants from danger",
            "resolved_node_id": "character_elena_001",  # Required for relationship extraction
            "status": "resolved"
        },
        {
            "id": "location_haven_001", 
            "name": "Haven",
            "type": "location",
            "description": "Central settlement in the Lost Valley, well-protected and secure",
            "resolved_node_id": "location_haven_001",  # Required for relationship extraction
            "status": "resolved"
        },
        {
            "id": "location_lost_valley_001",
            "name": "The Lost Valley",
            "type": "location", 
            "description": "A hidden valley surrounded by impassable mountains",
            "resolved_node_id": "location_lost_valley_001",  # Required for relationship extraction
            "status": "resolved"
        },
        {
            "id": "character_theron_001",
            "name": "Theron",
            "type": "character",
            "description": "Master scholar who studies ancient ruins and magical artifacts",
            "resolved_node_id": "character_theron_001",  # Required for relationship extraction
            "status": "resolved"
        },
        {
            "id": "location_ancient_ruins_001",
            "name": "Ancient Ruins",
            "type": "location",
            "description": "Mysterious stone structures with strange magical energy",
            "resolved_node_id": "location_ancient_ruins_001",  # Required for relationship extraction
            "status": "resolved"
        }
    ]


@pytest.mark.integration
class TestRelationshipExtractorRealLLM:
    """Integration tests with real LLM service."""
    
    def test_basic_relationship_extraction(self, relationship_extractor, sample_entities, temp_storage_path, test_run_uuid):
        """Test basic relationship extraction from conversation with entity context."""
        print("\n=== Testing Basic Relationship Extraction ===")
        
        conversation_text = """
        Elena, the mayor of Haven, was discussing the recent discoveries in the Ancient Ruins 
        with Theron, the master scholar. She mentioned that Haven is located in the Lost Valley, 
        and that Theron has been studying the magical artifacts found in the ruins. 
        The ruins themselves are also located within the Lost Valley, creating an area of 
        concentrated magical activity that concerns the inhabitants of Haven.
        """
        
        digest_text = "Discussion about Haven's location, Theron's research, and magical discoveries in Ancient Ruins."
        
        print(f"Testing with {len(sample_entities)} entities...")
        print(f"Conversation: {conversation_text[:100]}...")
        
        # Get log directory from LoggingConfig
        if test_run_uuid:
            guid = f"{TEST_GUID}_{test_run_uuid}"
        else:
            guid = TEST_GUID
        log_dir = LoggingConfig.get_log_base_dir(guid)
        print(f"Log directory: {log_dir}")
        print()
        
        # Extract relationships
        relationships = relationship_extractor.extract_relationships_from_conversation(
            conversation_text=conversation_text,
            digest_text=digest_text,
            entities=sample_entities
        )
        
        print(f"Extracted {len(relationships)} relationships:")
        for i, rel in enumerate(relationships, 1):
            # Use entity IDs, not names (API returns IDs)
            from_id = rel.get('from_entity_id', 'unknown')
            to_id = rel.get('to_entity_id', 'unknown')
            # Find entity names for display
            from_entity = next((e['name'] for e in sample_entities if e.get('resolved_node_id') == from_id), from_id)
            to_entity = next((e['name'] for e in sample_entities if e.get('resolved_node_id') == to_id), to_id)
            
            print(f"  {i}. {from_entity} -[{rel['relationship']}]-> {to_entity}")
            print(f"     Confidence: {rel.get('confidence', 'N/A')}")
            print(f"     Evidence: {rel.get('evidence', 'N/A')}")
            print()
        
        # Basic validations
        assert len(relationships) > 0, "Should extract at least one relationship"
        
        for rel in relationships:
            # Check required fields (API uses entity IDs, not names)
            assert 'from_entity_id' in rel, "Relationship missing from_entity_id"
            assert 'to_entity_id' in rel, "Relationship missing to_entity_id"
            assert 'relationship' in rel, "Relationship missing relationship type"
            
            # Check confidence is reasonable
            confidence = rel.get('confidence', 1.0)
            assert 0.0 <= confidence <= 1.0, f"Invalid confidence: {confidence}"
            
            # Check relationship type is valid
            valid_types = relationship_extractor.get_relationship_types()
            assert rel['relationship'] in valid_types, f"Invalid relationship type: {rel['relationship']}"
        
        # Save results for analysis
        self._save_test_results(relationships, temp_storage_path, "basic_extraction_test")
        
        print(f"✅ Basic relationship extraction test passed!")
        print(f"Check detailed LLM logs at: {log_dir}")
    
    def test_domain_specific_relationships(self, relationship_extractor, temp_storage_path):
        """Test domain-specific D&D relationship extraction."""
        print("\n=== Testing Domain-Specific D&D Relationships ===")
        
        # D&D specific entities and scenario
        dnd_entities = [
            {
                "id": "character_wizard_001",
                "name": "Gandalf the Grey",
                "type": "character",
                "description": "Powerful wizard who leads the Fellowship and fights against evil",
                "resolved_node_id": "character_wizard_001",
                "status": "resolved"
            },
            {
                "id": "organization_fellowship_001",
                "name": "Fellowship of the Ring",
                "type": "organization",
                "description": "Group of heroes united to destroy the One Ring",
                "resolved_node_id": "organization_fellowship_001",
                "status": "resolved"
            },
            {
                "id": "object_staff_001",
                "name": "Wizard's Staff",
                "type": "object",
                "description": "Magical staff wielded by Gandalf for casting spells",
                "resolved_node_id": "object_staff_001",
                "status": "resolved"
            },
            {
                "id": "character_sauron_001",
                "name": "Sauron",
                "type": "character", 
                "description": "Dark Lord and primary antagonist seeking the One Ring",
                "resolved_node_id": "character_sauron_001",
                "status": "resolved"
            },
            {
                "id": "spell_fireball_001",
                "name": "Fireball",
                "type": "spell",
                "description": "Destructive fire magic spell used in combat",
                "resolved_node_id": "spell_fireball_001",
                "status": "resolved"
            }
        ]
        
        conversation_text = """
        Gandalf the Grey leads the Fellowship of the Ring in their quest. He wields his magical 
        Wizard's Staff to cast powerful spells like Fireball against their enemies. The Fellowship 
        is constantly opposed by Sauron, the Dark Lord, who seeks to destroy them. Gandalf uses 
        his Fireball spell when the Fellowship is attacked, channeling the magic through his staff.
        """
        
        digest_text = "Epic battle scene with Gandalf leading Fellowship against Sauron using magical combat."
        
        # Extract relationships
        relationships = relationship_extractor.extract_relationships_from_conversation(
            conversation_text=conversation_text,
            digest_text=digest_text,
            entities=dnd_entities
        )
        
        print(f"Extracted {len(relationships)} D&D relationships:")
        
        # Group relationships by type for analysis
        relationships_by_type = {}
        for rel in relationships:
            rel_type = rel['relationship']
            if rel_type not in relationships_by_type:
                relationships_by_type[rel_type] = []
            relationships_by_type[rel_type].append(rel)
        
        for rel_type, rels in relationships_by_type.items():
            print(f"\n  {rel_type.upper()} relationships:")
            for rel in rels:
                # Find entity names for display
                from_id = rel.get('from_entity_id', '')
                to_id = rel.get('to_entity_id', '')
                from_entity = next((e['name'] for e in dnd_entities if e.get('resolved_node_id') == from_id), from_id)
                to_entity = next((e['name'] for e in dnd_entities if e.get('resolved_node_id') == to_id), to_id)
                print(f"    • {from_entity} -> {to_entity}")
        
        # Check for expected D&D relationship types
        expected_types = ['leads', 'member_of', 'owns', 'uses', 'enemies_with']
        found_types = set(rel['relationship'] for rel in relationships)
        
        print(f"\nRelationship types found: {sorted(found_types)}")
        print(f"D&D domain types available: {sorted(relationship_extractor.get_relationship_types().keys())}")
        
        # Save results
        self._save_test_results(relationships, temp_storage_path, "dnd_domain_test")
        
        # Validations
        assert len(relationships) > 0, "Should extract relationships from D&D scenario"
        
        # Check that we're getting D&D-appropriate relationship types
        dnd_types = relationship_extractor.get_relationship_types()
        for rel in relationships:
            assert rel['relationship'] in dnd_types, f"Unknown relationship type: {rel['relationship']}"
        
        print(f"✅ Domain-specific D&D relationship extraction test passed!")
    
    def test_confidence_and_evidence_generation(self, relationship_extractor, sample_entities, temp_storage_path):
        """Test that LLM generates appropriate confidence scores and evidence."""
        print("\n=== Testing Confidence and Evidence Generation ===")
        
        # Use clear, unambiguous conversation for high confidence
        clear_conversation = """
        Elena is the mayor of Haven. Haven is located in the Lost Valley. 
        Theron studies the Ancient Ruins, which are also in the Lost Valley.
        """
        
        # Use ambiguous conversation for lower confidence
        ambiguous_conversation = """
        Someone mentioned that Elena might be associated with a place called Haven, 
        and there could be some connection to a valley. Theron was possibly researching 
        some old structures, but the details were unclear.
        """
        
        print("Testing with clear conversation:")
        clear_relationships = relationship_extractor.extract_relationships_from_conversation(
            conversation_text=clear_conversation,
            digest_text="Clear factual statements about locations and roles",
            entities=sample_entities
        )
        
        print("Testing with ambiguous conversation:")
        ambiguous_relationships = relationship_extractor.extract_relationships_from_conversation(
            conversation_text=ambiguous_conversation,
            digest_text="Uncertain and ambiguous references",
            entities=sample_entities
        )
        
        print(f"\nClear conversation results ({len(clear_relationships)} relationships):")
        clear_confidences = []
        for rel in clear_relationships:
            confidence = rel.get('confidence', 0.5)
            clear_confidences.append(confidence)
            # Find entity names for display
            from_id = rel.get('from_entity_id', '')
            to_id = rel.get('to_entity_id', '')
            from_entity = next((e['name'] for e in sample_entities if e.get('resolved_node_id') == from_id), from_id)
            to_entity = next((e['name'] for e in sample_entities if e.get('resolved_node_id') == to_id), to_id)
            
            print(f"  • {from_entity} -[{rel['relationship']}]-> {to_entity}")
            print(f"    Confidence: {confidence:.2f}")
            print(f"    Evidence: {rel.get('evidence', 'N/A')[:60]}...")
        
        print(f"\nAmbiguous conversation results ({len(ambiguous_relationships)} relationships):")
        ambiguous_confidences = []
        for rel in ambiguous_relationships:
            confidence = rel.get('confidence', 0.5)
            ambiguous_confidences.append(confidence)
            # Find entity names for display
            from_id = rel.get('from_entity_id', '')
            to_id = rel.get('to_entity_id', '')
            from_entity = next((e['name'] for e in sample_entities if e.get('resolved_node_id') == from_id), from_id)
            to_entity = next((e['name'] for e in sample_entities if e.get('resolved_node_id') == to_id), to_id)
            
            print(f"  • {from_entity} -[{rel['relationship']}]-> {to_entity}")
            print(f"    Confidence: {confidence:.2f}")
            print(f"    Evidence: {rel.get('evidence', 'N/A')[:60]}...")
        
        # Save results
        results = {
            "clear_conversation_results": clear_relationships,
            "ambiguous_conversation_results": ambiguous_relationships,
            "clear_avg_confidence": sum(clear_confidences) / len(clear_confidences) if clear_confidences else 0,
            "ambiguous_avg_confidence": sum(ambiguous_confidences) / len(ambiguous_confidences) if ambiguous_confidences else 0
        }
        self._save_test_results(results, temp_storage_path, "confidence_evidence_test")
        
        # Validate confidence behavior
        if clear_confidences and ambiguous_confidences:
            clear_avg = sum(clear_confidences) / len(clear_confidences)
            ambiguous_avg = sum(ambiguous_confidences) / len(ambiguous_confidences)
            
            print(f"\nConfidence Analysis:")
            print(f"  Clear conversation average confidence: {clear_avg:.2f}")
            print(f"  Ambiguous conversation average confidence: {ambiguous_avg:.2f}")
            
            # Clear conversation should generally have higher confidence
            # (though this is not guaranteed with LLM variability)
            if clear_avg > ambiguous_avg:
                print("  ✅ Clear conversation had higher confidence as expected")
            else:
                print("  ⚠️  Ambiguous conversation had higher/equal confidence - LLM variability")
        
        # Check that all relationships have evidence
        all_relationships = clear_relationships + ambiguous_relationships
        for rel in all_relationships:
            assert 'evidence' in rel and rel['evidence'], f"Missing evidence for relationship: {rel}"
            assert 'confidence' in rel and 0 <= rel['confidence'] <= 1, f"Invalid confidence: {rel.get('confidence')}"
        
        print(f"✅ Confidence and evidence generation test passed!")
    
    def _save_test_results(self, results: Any, temp_storage_path: str, test_name: str):
        """Save test results to JSON file for analysis."""
        results_file = os.path.join(temp_storage_path, f"{test_name}_results.json")
        
        # Ensure results are JSON serializable
        if isinstance(results, dict):
            serializable_results = results
        else:
            serializable_results = {"results": results}
        
        # Add metadata
        serializable_results["test_metadata"] = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "results_count": len(results) if isinstance(results, list) else 1
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 Test results saved to: {results_file}")


def run_real_llm_tests():
    """Run RelationshipExtractor tests with real LLM."""
    print("=" * 80)
    print("RELATIONSHIPEXTRACTOR REAL LLM INTEGRATION TESTS")
    print("=" * 80)
    
    # Check if Ollama is available
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma3")
    
    print(f"Testing with Ollama at: {base_url}")
    print(f"Using model: {model}")
    print()
    
    test_args = [
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-m", "integration"
    ]
    
    return pytest.main(test_args)


if __name__ == "__main__":
    exit_code = run_real_llm_tests()
    sys.exit(exit_code) 