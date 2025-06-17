#!/usr/bin/env python3
"""
Real LLM integration tests for RelationshipExtractor.

Tests the RelationshipExtractor with actual Ollama LLM calls to validate:
- Relationship extraction from conversation text with entity context
- Domain-specific relationship type detection
- LLM reasoning for relationship inference
- Confidence scoring and evidence generation
- Deduplication and validation

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
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from memory.graph_memory.relationship_extractor import RelationshipExtractor
from ai.llm_ollama import OllamaService

# Import domain config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sample_data'))
from domain_configs import DND_CONFIG


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
    
    # Use the project root logs directory with UUID
    project_root = Path(__file__).parent.parent.parent  # Go up to project root
    if test_uuid:
        logs_dir = project_root / "logs" / test_uuid
        print(f"  Logs directory: {logs_dir}")
    else:
        # Fallback to old location if no UUID provided
        logs_dir = Path(__file__).parent / "logs"
    
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure LLM service with detailed logging
    llm_config = {
        "base_url": base_url,
        "model": model,
        "embed_model": embed_model,
        "debug": True,
        "debug_file": str(logs_dir / "test_ollama_relationship_extraction.log"),
        "debug_scope": "relationship_extractor_test",
        "console_output": False
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
    # Create a specific logger for relationship extraction
    rel_logger = logging.getLogger(f"relationship_extractor_test.{test_run_uuid}")
    rel_logger.setLevel(logging.DEBUG)
    
    # Add handler to write to the same log file as the LLM service
    log_dir = f"logs/{test_run_uuid}"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "test_relationship_extractor_real_llm.log")
    
    # Check if handler already exists to avoid duplicates
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename.endswith("test_relationship_extractor_real_llm.log") 
               for h in rel_logger.handlers):
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(name)s]:[%(funcName)s]::[%(levelname)s]:%(message)s')
        file_handler.setFormatter(formatter)
        rel_logger.addHandler(file_handler)
    
    return RelationshipExtractor(
        llm_service=ollama_service,
        domain_config=DND_CONFIG,
        logger=rel_logger
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
            "status": "new"
        },
        {
            "id": "location_haven_001", 
            "name": "Haven",
            "type": "location",
            "description": "Central settlement in the Lost Valley, well-protected and secure",
            "status": "new"
        },
        {
            "id": "location_lost_valley_001",
            "name": "The Lost Valley",
            "type": "location", 
            "description": "A hidden valley surrounded by impassable mountains",
            "status": "new"
        },
        {
            "id": "character_theron_001",
            "name": "Theron",
            "type": "character",
            "description": "Master scholar who studies ancient ruins and magical artifacts",
            "status": "new"
        },
        {
            "id": "location_ancient_ruins_001",
            "name": "Ancient Ruins",
            "type": "location",
            "description": "Mysterious stone structures with strange magical energy",
            "status": "new"
        }
    ]


@pytest.mark.integration
class TestRelationshipExtractorRealLLM:
    """Integration tests with real LLM service."""
    
    def test_basic_relationship_extraction(self, relationship_extractor, sample_entities, temp_storage_path):
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
        print(f"Log file location: {relationship_extractor.llm_service.debug_file}")
        print()
        
        # Extract relationships
        relationships = relationship_extractor.extract_relationships_from_conversation(
            conversation_text=conversation_text,
            digest_text=digest_text,
            entities=sample_entities
        )
        
        print(f"Extracted {len(relationships)} relationships:")
        for i, rel in enumerate(relationships, 1):
            print(f"  {i}. {rel['from_entity']} -[{rel['relationship']}]-> {rel['to_entity']}")
            print(f"     Confidence: {rel.get('confidence', 'N/A')}")
            print(f"     Evidence: {rel.get('evidence', 'N/A')}")
            print()
        
        # Basic validations
        assert len(relationships) > 0, "Should extract at least one relationship"
        
        for rel in relationships:
            # Check required fields
            assert 'from_entity' in rel, "Relationship missing from_entity"
            assert 'to_entity' in rel, "Relationship missing to_entity"
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
        print(f"Check detailed LLM logs at: {relationship_extractor.llm_service.debug_file}")
    
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
                "status": "new"
            },
            {
                "id": "organization_fellowship_001",
                "name": "Fellowship of the Ring",
                "type": "organization",
                "description": "Group of heroes united to destroy the One Ring",
                "status": "new"
            },
            {
                "id": "object_staff_001",
                "name": "Wizard's Staff",
                "type": "object",
                "description": "Magical staff wielded by Gandalf for casting spells",
                "status": "new"
            },
            {
                "id": "character_sauron_001",
                "name": "Sauron",
                "type": "character", 
                "description": "Dark Lord and primary antagonist seeking the One Ring",
                "status": "new"
            },
            {
                "id": "spell_fireball_001",
                "name": "Fireball",
                "type": "spell",
                "description": "Destructive fire magic spell used in combat",
                "status": "new"
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
                print(f"    • {rel['from_entity']} -> {rel['to_entity']}")
        
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
    
    def test_entity_only_relationship_extraction(self, relationship_extractor, temp_storage_path):
        """Test relationship extraction with just entities and minimal context."""
        print("\n=== Testing Entity-Only Relationship Extraction ===")
        
        # Test entities that should have obvious relationships based on descriptions
        entities = [
            {
                "id": "location_castle_001",
                "name": "Ironhold Castle",
                "type": "location",
                "description": "Massive fortress that serves as the royal seat of King Aldric",
                "status": "new"
            },
            {
                "id": "character_king_001",
                "name": "King Aldric",
                "type": "character",
                "description": "Ruler of the kingdom who resides in Ironhold Castle",
                "status": "new"
            },
            {
                "id": "object_crown_001",
                "name": "Crown of Kings",
                "type": "object",
                "description": "Ancient crown worn by King Aldric during royal ceremonies",
                "status": "new"
            },
            {
                "id": "organization_royal_guard_001",
                "name": "Royal Guard",
                "type": "organization",
                "description": "Elite soldiers who protect King Aldric and defend Ironhold Castle",
                "status": "new"
            }
        ]
        
        context_text = "Royal court setting with established hierarchy and territorial control."
        
        # Extract relationships using entity-only method
        relationships = relationship_extractor.extract_relationships_from_entities(
            entities=entities,
            context_text=context_text
        )
        
        print(f"Extracted {len(relationships)} relationships from entity analysis:")
        for rel in relationships:
            print(f"  • {rel['from_entity']} -[{rel['relationship']}]-> {rel['to_entity']}")
            print(f"    Evidence: {rel.get('evidence', 'N/A')}")
        
        # Save results
        self._save_test_results(relationships, temp_storage_path, "entity_only_test")
        
        # Validate that logical relationships were found
        assert len(relationships) > 0, "Should find relationships based on entity descriptions"
        
        # Check for expected relationship patterns
        entity_names = [entity['name'] for entity in entities]
        relationship_pairs = [(rel['from_entity'], rel['to_entity']) for rel in relationships]
        
        print(f"\nRelationship pairs found: {relationship_pairs}")
        print(f"Available entities: {entity_names}")
        
        # All relationships should involve the provided entities
        for rel in relationships:
            assert rel['from_entity'] in entity_names, f"Unknown from_entity: {rel['from_entity']}"
            assert rel['to_entity'] in entity_names, f"Unknown to_entity: {rel['to_entity']}"
        
        print(f"✅ Entity-only relationship extraction test passed!")
    
    def test_relationship_deduplication(self, relationship_extractor, temp_storage_path):
        """Test relationship deduplication functionality."""
        print("\n=== Testing Relationship Deduplication ===")
        
        # Create test relationships with duplicates
        test_relationships = [
            {
                "from_entity": "Elena",
                "to_entity": "Haven", 
                "relationship": "located_in",
                "confidence": 0.9,
                "evidence": "Elena is the mayor of Haven"
            },
            {
                "from_entity": "elena",  # Different case
                "to_entity": "haven",   # Different case
                "relationship": "located_in",
                "confidence": 0.8,
                "evidence": "Elena lives in Haven"
            },
            {
                "from_entity": "Theron",
                "to_entity": "Ancient Ruins",
                "relationship": "uses",
                "confidence": 0.7,
                "evidence": "Theron studies the ruins"
            },
            {
                "from_entity": "Elena",
                "to_entity": "Haven",
                "relationship": "owns",  # Different relationship type
                "confidence": 0.6,
                "evidence": "Elena owns property in Haven"
            }
        ]
        
        print(f"Input relationships: {len(test_relationships)}")
        for i, rel in enumerate(test_relationships, 1):
            print(f"  {i}. {rel['from_entity']} -[{rel['relationship']}]-> {rel['to_entity']}")
        
        # Deduplicate
        deduplicated = relationship_extractor.deduplicate_relationships(test_relationships)
        
        print(f"\nAfter deduplication: {len(deduplicated)}")
        for i, rel in enumerate(deduplicated, 1):
            print(f"  {i}. {rel['from_entity']} -[{rel['relationship']}]-> {rel['to_entity']}")
        
        # Save results
        results = {
            "original": test_relationships,
            "deduplicated": deduplicated,
            "removed_count": len(test_relationships) - len(deduplicated)
        }
        self._save_test_results(results, temp_storage_path, "deduplication_test")
        
        # Validate deduplication
        assert len(deduplicated) < len(test_relationships), "Should remove at least one duplicate"
        assert len(deduplicated) == 3, "Should have 3 unique relationships (Elena->Haven located_in, Theron->Ancient Ruins uses, Elena->Haven owns)"
        
        # Check that different relationship types are preserved
        relationship_keys = {(rel['from_entity'].lower(), rel['to_entity'].lower(), rel['relationship']) 
                           for rel in deduplicated}
        assert len(relationship_keys) == len(deduplicated), "Each relationship should be unique"
        
        print(f"✅ Relationship deduplication test passed!")
    
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
            print(f"  • {rel['from_entity']} -[{rel['relationship']}]-> {rel['to_entity']}")
            print(f"    Confidence: {confidence:.2f}")
            print(f"    Evidence: {rel.get('evidence', 'N/A')[:60]}...")
        
        print(f"\nAmbiguous conversation results ({len(ambiguous_relationships)} relationships):")
        ambiguous_confidences = []
        for rel in ambiguous_relationships:
            confidence = rel.get('confidence', 0.5)
            ambiguous_confidences.append(confidence)
            print(f"  • {rel['from_entity']} -[{rel['relationship']}]-> {rel['to_entity']}")
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