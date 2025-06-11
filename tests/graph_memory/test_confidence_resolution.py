#!/usr/bin/env python3
"""
Confidence-based resolution decision tests for EntityResolver.

Tests the confidence threshold functionality and auto-matching behavior
to ensure the EntityResolver makes appropriate resolution decisions
based on confidence scores.
"""

import sys
import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from memory.graph_memory.entity_resolver import EntityResolver


class ConfidenceMockLLMService:
    """Mock LLM service that returns specific confidence levels for testing."""
    
    def __init__(self, confidence_scenarios: Dict[str, float]):
        """
        Initialize with confidence scenarios.
        
        Args:
            confidence_scenarios: Dict mapping entity names to confidence scores
        """
        self.confidence_scenarios = confidence_scenarios
        self.call_count = 0
    
    def generate(self, prompt: str) -> str:
        """Generate responses with controlled confidence levels."""
        self.call_count += 1
        
        # Determine which scenario this is based on prompt content
        for entity_name, confidence in self.confidence_scenarios.items():
            if entity_name.lower() in prompt.lower():
                return f'''[
    ["candidate_{entity_name.lower().replace(' ', '_')}", "existing_node_{entity_name.lower().replace(' ', '_')}", "Test match for {entity_name}", {confidence}]
]'''
        
        # Default response for unknown entities
        return '''[
    ["candidate_unknown", "<NEW>", "No match found", 0.0]
]'''


@pytest.fixture
def temp_storage_path():
    """Create temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestConfidenceBasedResolution:
    """Test confidence-based resolution decisions."""
    
    def test_high_confidence_auto_match(self, temp_storage_path):
        """Test that high confidence scores result in auto-matching."""
        # Create scenarios with high confidence
        confidence_scenarios = {
            "High Confidence Entity": 0.95,
            "Another High Entity": 0.88
        }
        
        mock_llm = ConfidenceMockLLMService(confidence_scenarios)
        resolver = EntityResolver(
            llm_service=mock_llm,
            storage_path=temp_storage_path,
            confidence_threshold=0.8
        )
        
        candidates = [
            {
                "candidate_id": "high_001",
                "type": "character",
                "name": "High Confidence Entity",
                "description": "An entity that should match with high confidence"
            },
            {
                "candidate_id": "high_002", 
                "type": "location",
                "name": "Another High Entity",
                "description": "Another entity with high confidence match"
            }
        ]
        
        resolutions = resolver.resolve_candidates(candidates)
        
        assert len(resolutions) == 2
        
        for resolution in resolutions:
            assert resolution["confidence"] >= 0.8
            assert resolution["auto_matched"] == True
            assert resolution["resolved_node_id"] != "<NEW>"
            print(f"High confidence test: {resolution['candidate_id']} -> "
                  f"{resolution['resolved_node_id']} (confidence: {resolution['confidence']})")
    
    def test_low_confidence_no_auto_match(self, temp_storage_path):
        """Test that low confidence scores do not result in auto-matching."""
        confidence_scenarios = {
            "Low Confidence Entity": 0.6,
            "Very Low Entity": 0.3
        }
        
        mock_llm = ConfidenceMockLLMService(confidence_scenarios)
        resolver = EntityResolver(
            llm_service=mock_llm,
            storage_path=temp_storage_path,
            confidence_threshold=0.8
        )
        
        candidates = [
            {
                "candidate_id": "low_001",
                "type": "character", 
                "name": "Low Confidence Entity",
                "description": "An entity with uncertain matching"
            },
            {
                "candidate_id": "low_002",
                "type": "object",
                "name": "Very Low Entity", 
                "description": "An entity with very low confidence"
            }
        ]
        
        resolutions = resolver.resolve_candidates(candidates)
        
        assert len(resolutions) == 2
        
        for resolution in resolutions:
            assert resolution["confidence"] < 0.8
            assert resolution["auto_matched"] == False
            # Should still suggest the match but not auto-apply it
            assert resolution["resolved_node_id"] != "<NEW>"
            print(f"Low confidence test: {resolution['candidate_id']} -> "
                  f"{resolution['resolved_node_id']} (confidence: {resolution['confidence']}, "
                  f"auto_matched: {resolution['auto_matched']})")
    
    def test_threshold_boundary_conditions(self, temp_storage_path):
        """Test entities right at the confidence threshold boundary."""
        confidence_scenarios = {
            "Exactly Threshold": 0.8,      # Exactly at threshold
            "Just Above": 0.801,           # Just above threshold
            "Just Below": 0.799            # Just below threshold
        }
        
        mock_llm = ConfidenceMockLLMService(confidence_scenarios)
        resolver = EntityResolver(
            llm_service=mock_llm,
            storage_path=temp_storage_path,
            confidence_threshold=0.8
        )
        
        candidates = [
            {
                "candidate_id": "boundary_001",
                "type": "character",
                "name": "Exactly Threshold", 
                "description": "Entity exactly at threshold"
            },
            {
                "candidate_id": "boundary_002",
                "type": "character",
                "name": "Just Above",
                "description": "Entity just above threshold"
            },
            {
                "candidate_id": "boundary_003",
                "type": "character", 
                "name": "Just Below",
                "description": "Entity just below threshold"
            }
        ]
        
        resolutions = resolver.resolve_candidates(candidates)
        
        # Find specific resolutions
        exactly_threshold = next(r for r in resolutions if "exactly_threshold" in r["candidate_id"])
        just_above = next(r for r in resolutions if "just_above" in r["candidate_id"])
        just_below = next(r for r in resolutions if "just_below" in r["candidate_id"])
        
        # Test boundary conditions
        assert exactly_threshold["confidence"] == 0.8
        assert exactly_threshold["auto_matched"] == True  # >= threshold
        
        assert just_above["confidence"] > 0.8
        assert just_above["auto_matched"] == True
        
        assert just_below["confidence"] < 0.8
        assert just_below["auto_matched"] == False
        
        print("Boundary condition results:")
        for resolution in resolutions:
            print(f"  {resolution['candidate_id']}: confidence={resolution['confidence']}, "
                  f"auto_matched={resolution['auto_matched']}")
    
    def test_custom_threshold_override(self, temp_storage_path):
        """Test overriding the default confidence threshold."""
        confidence_scenarios = {
            "Medium Confidence": 0.75
        }
        
        mock_llm = ConfidenceMockLLMService(confidence_scenarios)
        resolver = EntityResolver(
            llm_service=mock_llm,
            storage_path=temp_storage_path,
            confidence_threshold=0.8  # Default threshold
        )
        
        candidate = {
            "candidate_id": "threshold_test",
            "type": "character",
            "name": "Medium Confidence",
            "description": "Entity with medium confidence"
        }
        
        # Test with default threshold (0.8) - should not auto-match
        resolution_default = resolver.resolve_candidates([candidate])[0]
        assert resolution_default["confidence"] == 0.75
        assert resolution_default["auto_matched"] == False
        
        # Test with lower threshold (0.7) - should auto-match
        resolution_low = resolver.resolve_candidates([candidate], confidence_threshold=0.7)[0]
        assert resolution_low["confidence"] == 0.75
        assert resolution_low["auto_matched"] == True
        
        # Test with higher threshold (0.9) - should not auto-match
        resolution_high = resolver.resolve_candidates([candidate], confidence_threshold=0.9)[0]
        assert resolution_high["confidence"] == 0.75
        assert resolution_high["auto_matched"] == False
        
        print("Threshold override results:")
        print(f"  Default (0.8): auto_matched={resolution_default['auto_matched']}")
        print(f"  Low (0.7): auto_matched={resolution_low['auto_matched']}")
        print(f"  High (0.9): auto_matched={resolution_high['auto_matched']}")
    
    def test_mixed_confidence_batch(self, temp_storage_path):
        """Test batch processing with mixed confidence levels."""
        confidence_scenarios = {
            "High Entity": 0.92,
            "Medium Entity": 0.75,
            "Low Entity": 0.45,
            "Zero Entity": 0.0
        }
        
        mock_llm = ConfidenceMockLLMService(confidence_scenarios)
        resolver = EntityResolver(
            llm_service=mock_llm,
            storage_path=temp_storage_path,
            confidence_threshold=0.8
        )
        
        candidates = [
            {
                "candidate_id": f"mixed_{name.lower().replace(' ', '_')}",
                "type": "character",
                "name": name,
                "description": f"Test entity: {name}"
            }
            for name in confidence_scenarios.keys()
        ]
        
        # Test both batch and individual processing
        batch_resolutions = resolver.resolve_candidates(candidates, process_individually=False)
        individual_resolutions = resolver.resolve_candidates(candidates, process_individually=True)
        
        # Both should have same number of results
        assert len(batch_resolutions) == len(individual_resolutions) == len(candidates)
        
        # Check that auto_matched flags are set correctly for both modes
        for resolutions, mode in [(batch_resolutions, "batch"), (individual_resolutions, "individual")]:
            auto_matched_count = sum(1 for r in resolutions if r["auto_matched"])
            high_confidence_count = sum(1 for r in resolutions if r["confidence"] >= 0.8)
            
            assert auto_matched_count == high_confidence_count
            print(f"{mode.capitalize()} processing: {auto_matched_count}/{len(resolutions)} auto-matched")
    
    def test_no_match_scenarios(self, temp_storage_path):
        """Test scenarios where no match should be found."""
        confidence_scenarios = {
            "No Match Entity": 0.0  # Explicitly no match
        }
        
        mock_llm = ConfidenceMockLLMService(confidence_scenarios)
        resolver = EntityResolver(
            llm_service=mock_llm,
            storage_path=temp_storage_path,
            confidence_threshold=0.8
        )
        
        candidate = {
            "candidate_id": "no_match_test",
            "type": "character",
            "name": "No Match Entity",
            "description": "An entity that should not match anything"
        }
        
        resolution = resolver.resolve_candidates([candidate])[0]
        
        assert resolution["confidence"] == 0.0
        assert resolution["auto_matched"] == False
        assert resolution["resolved_node_id"] == "existing_node_no_match_entity"  # Mock still returns something
        
        # Test with actual "<NEW>" response
        class NoMatchLLM:
            def generate(self, prompt):
                return '''[
    ["candidate_no_match", "<NEW>", "No similar entity found", 0.0]
]'''
        
        resolver_no_match = EntityResolver(
            llm_service=NoMatchLLM(),
            storage_path=temp_storage_path,
            confidence_threshold=0.8
        )
        
        resolution_new = resolver_no_match.resolve_candidates([candidate])[0]
        
        assert resolution_new["resolved_node_id"] == "<NEW>"
        assert resolution_new["confidence"] == 0.0
        assert resolution_new["auto_matched"] == False
        
        print("No match test results:")
        print(f"  Mock match: {resolution['resolved_node_id']} (confidence: {resolution['confidence']})")
        print(f"  Actual new: {resolution_new['resolved_node_id']} (confidence: {resolution_new['confidence']})")


def run_confidence_tests():
    """Run all confidence-based resolution tests."""
    print("=" * 80)
    print("CONFIDENCE-BASED RESOLUTION TESTS")
    print("=" * 80)
    
    test_args = [
        __file__,
        "-v",
        "-s", 
        "--tb=short"
    ]
    
    return pytest.main(test_args)


if __name__ == "__main__":
    exit_code = run_confidence_tests()
    sys.exit(exit_code)