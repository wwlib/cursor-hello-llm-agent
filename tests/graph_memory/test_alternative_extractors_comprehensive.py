#!/usr/bin/env python3
"""
Comprehensive test script for alternative entity and relationship extractors.

This script tests the alternative LLM-centric extraction approach using:
- sample_data/graph_data/* for existing graph simulation
- sample_data/agent_memory_conversations.json for test conversations
- sample_data/domain_configs.py for D&D domain configuration

Following the ALT_ENTITY_AND_RELATIONSHIP_EXTRACTION_APPROACH.md plan.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from memory.graph_memory.alt_graph_manager import AltGraphManager
from memory.graph_memory.alt_entity_extractor import AltEntityExtractor
from memory.graph_memory.alt_relationship_extractor import AltRelationshipExtractor
from memory.embeddings_manager import EmbeddingsManager
from ai.llm_ollama import OllamaService

# Import domain config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sample_data'))
from domain_configs import DND_CONFIG


def setup_ollama_services():
    """Set up real Ollama LLM and embeddings services using environment variables."""
    
    # Get environment variables
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma3")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
    
    print(f"Setting up Ollama services:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print(f"  Embedding Model: {embed_model}")
    
    # Configure LLM service
    llm_config = {
        "base_url": base_url,
        "model": model,
        "temperature": 0.7,
        "debug": True,
        "debug_file": "logs/test_ollama.log",
        "debug_scope": "test_extraction",
        "console_output": True
    }
    
    # Initialize services
    llm_service = OllamaService(llm_config)
    
    return llm_service, embed_model


class ComprehensiveTestRunner:
    """Main test runner for comprehensive alternative extractor testing."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.sample_data_dir = self.test_dir / "sample_data"
        self.graph_data_dir = self.sample_data_dir / "graph_data" 
        self.tmp_dir = Path(__file__).parent.parent / "test_files" / "tmp"
        self.graph_viewer_dir = Path(__file__).parent.parent.parent / "graph-viewer" / "public" / "sample-data"
        
        # Ensure tmp directory exists
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize real LLM services
        self.llm_service, self.embed_model = setup_ollama_services()
        
        # Initialize embeddings manager
        embeddings_file = str(self.tmp_dir / "test_embeddings.jsonl")
        self.embeddings_manager = EmbeddingsManager(embeddings_file, self.llm_service)
        
        self.results = {
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        
    def setup_test_environment(self):
        """Set up the test environment with sample data."""
        print("=== SETTING UP TEST ENVIRONMENT ===")
        
        # Copy existing graph data to tmp directory for testing
        for file in ["graph_nodes.json", "graph_edges.json", "graph_metadata.json"]:
            src = self.graph_data_dir / file
            dst = self.tmp_dir / file
            if src.exists():
                shutil.copy2(src, dst)
                print(f"Copied {file} to tmp directory")
        
        # Load conversation data
        conv_file = self.sample_data_dir / "agent_memory_conversations.json"
        with open(conv_file, 'r') as f:
            self.conversation_data = json.load(f)
            
        print(f"Loaded {len(self.conversation_data['entries'])} conversation entries")
        
        # Initialize AltGraphManager with real LLM services
        self.alt_graph_manager = AltGraphManager(
            storage_path=str(self.tmp_dir),
            llm_service=self.llm_service,
            embeddings_manager=self.embeddings_manager,
            domain_config=DND_CONFIG
        )
        
        print("Alternative Graph Manager initialized")
        
    def load_baseline_stats(self) -> Dict[str, Any]:
        """Load statistics from the existing baseline graph."""
        baseline_stats = {}
        
        # Load existing nodes
        nodes_file = self.graph_data_dir / "graph_nodes.json"
        if nodes_file.exists():
            with open(nodes_file, 'r') as f:
                nodes = json.load(f)
                baseline_stats["node_count"] = len(nodes)
                baseline_stats["node_types"] = {}
                for node in nodes.values():
                    node_type = node.get("type", "unknown")
                    baseline_stats["node_types"][node_type] = baseline_stats["node_types"].get(node_type, 0) + 1
        
        # Load existing edges  
        edges_file = self.graph_data_dir / "graph_edges.json"
        if edges_file.exists():
            with open(edges_file, 'r') as f:
                edges = json.load(f)
                baseline_stats["edge_count"] = len(edges)
                baseline_stats["relationship_types"] = {}
                for edge in edges:
                    rel_type = edge.get("relationship", "unknown")
                    baseline_stats["relationship_types"][rel_type] = baseline_stats["relationship_types"].get(rel_type, 0) + 1
                    
        return baseline_stats
        
    def test_entity_extraction(self) -> Dict[str, Any]:
        """Test alternative entity extraction with conversation data."""
        print("\n=== TESTING ALTERNATIVE ENTITY EXTRACTION ===")
        
        test_result = {
            "test_name": "entity_extraction",
            "start_time": datetime.now().isoformat(),
            "entries_processed": 0,
            "entities_extracted": 0,
            "new_entities": 0,
            "existing_entities_updated": 0,
            "errors": []
        }
        
        try:
            # Process each conversation entry
            for entry in self.conversation_data["entries"]:
                # Skip user queries as per filtering pipeline
                if entry.get("role") == "user":
                    continue
                    
                digest = entry.get("digest", {})
                rated_segments = digest.get("rated_segments", [])
                
                # Filter segments according to baseline approach
                qualifying_segments = []
                for segment in rated_segments:
                    if (segment.get("importance", 0) >= 3 and 
                        segment.get("memory_worthy", False) and
                        segment.get("type") in ["information", "action"]):
                        qualifying_segments.append(segment)
                
                if not qualifying_segments:
                    continue
                    
                print(f"\nProcessing entry {entry['guid'][:8]}... with {len(qualifying_segments)} qualifying segments")
                
                # Use alternative extraction approach
                conversation_text = entry.get("content", "")
                digest_text = " ".join([seg["text"] for seg in qualifying_segments])
                
                # Process the conversation entry using the alternative approach
                results = self.alt_graph_manager.process_conversation_entry(
                    conversation_text=conversation_text,
                    digest_text=digest_text
                )
                
                test_result["entries_processed"] += 1
                test_result["entities_extracted"] += len(results.get("entities", []))
                test_result["new_entities"] += len(results.get("new_entities", []))
                test_result["existing_entities_updated"] += len(results.get("existing_entities", []))
                
                # Log results
                for entity in results.get("new_entities", []):
                    print(f"  + NEW: {entity.get('type', 'unknown')} '{entity.get('name', 'unknown')}'")
                for entity in results.get("existing_entities", []):
                    print(f"  ~ UPDATED: {entity.get('type', 'unknown')} '{entity.get('name', 'unknown')}'")
                        
        except Exception as e:
            test_result["errors"].append(str(e))
            print(f"ERROR in entity extraction: {e}")
            
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
        
    def test_relationship_extraction(self) -> Dict[str, Any]:
        """Test alternative relationship extraction."""
        print("\n=== TESTING ALTERNATIVE RELATIONSHIP EXTRACTION ===")
        
        test_result = {
            "test_name": "relationship_extraction", 
            "start_time": datetime.now().isoformat(),
            "entries_processed": 0,
            "relationships_extracted": 0,
            "new_relationships": 0,
            "errors": []
        }
        
        try:
            # Process each conversation entry for relationships
            for entry in self.conversation_data["entries"]:
                if entry.get("role") == "user":
                    continue
                    
                digest = entry.get("digest", {})
                rated_segments = digest.get("rated_segments", [])
                
                qualifying_segments = []
                for segment in rated_segments:
                    if (segment.get("importance", 0) >= 3 and 
                        segment.get("memory_worthy", False) and
                        segment.get("type") in ["information", "action"]):
                        qualifying_segments.append(segment)
                
                if not qualifying_segments:
                    continue
                    
                print(f"\nExtracting relationships from entry {entry['guid'][:8]}...")
                
                conversation_text = entry.get("content", "")
                digest_text = " ".join([seg["text"] for seg in qualifying_segments])
                
                # Process the conversation entry (this handles both entities and relationships)
                results = self.alt_graph_manager.process_conversation_entry(
                    conversation_text=conversation_text,
                    digest_text=digest_text
                )
                
                test_result["entries_processed"] += 1
                test_result["relationships_extracted"] += len(results.get("relationships", []))
                
                # Log relationship results
                for rel in results.get("relationships", []):
                    test_result["new_relationships"] += 1
                    from_name = rel.get("from_node_name", "unknown")
                    to_name = rel.get("to_node_name", "unknown")
                    rel_type = rel.get("relationship", "unknown")
                    print(f"  + NEW RELATIONSHIP: {from_name} -> {rel_type} -> {to_name}")
                        
        except Exception as e:
            test_result["errors"].append(str(e))
            print(f"ERROR in relationship extraction: {e}")
            
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
        
    def analyze_results(self, baseline_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results and compare with baseline."""
        print("\n=== ANALYZING RESULTS ===")
        
        # Load final graph state
        final_nodes_file = self.tmp_dir / "graph_nodes.json"
        final_edges_file = self.tmp_dir / "graph_edges.json"
        
        final_stats = {"node_count": 0, "edge_count": 0, "node_types": {}, "relationship_types": {}}
        
        if final_nodes_file.exists():
            with open(final_nodes_file, 'r') as f:
                nodes = json.load(f)
                final_stats["node_count"] = len(nodes)
                for node in nodes.values():
                    node_type = node.get("type", "unknown")
                    final_stats["node_types"][node_type] = final_stats["node_types"].get(node_type, 0) + 1
                    
        if final_edges_file.exists():
            with open(final_edges_file, 'r') as f:
                edges = json.load(f)
                final_stats["edge_count"] = len(edges)
                for edge in edges:
                    rel_type = edge.get("relationship", "unknown")
                    final_stats["relationship_types"][rel_type] = final_stats["relationship_types"].get(rel_type, 0) + 1
        
        analysis = {
            "baseline_stats": baseline_stats,
            "final_stats": final_stats,
            "changes": {
                "nodes_added": final_stats["node_count"] - baseline_stats.get("node_count", 0),
                "edges_added": final_stats["edge_count"] - baseline_stats.get("edge_count", 0)
            },
            "llm_calls": "tracked_via_debug_logs"
        }
        
        print(f"Baseline nodes: {baseline_stats.get('node_count', 0)}")
        print(f"Final nodes: {final_stats['node_count']}")
        print(f"Nodes added: {analysis['changes']['nodes_added']}")
        print(f"Baseline edges: {baseline_stats.get('edge_count', 0)}")
        print(f"Final edges: {final_stats['edge_count']}")
        print(f"Edges added: {analysis['changes']['edges_added']}")
        print(f"LLM calls: {analysis['llm_calls']}")
        
        return analysis
        
    def copy_results_to_graph_viewer(self):
        """Copy results to graph-viewer for visualization."""
        print("\n=== COPYING RESULTS TO GRAPH VIEWER ===")
        
        # Ensure graph-viewer directory exists
        if not self.graph_viewer_dir.exists():
            print(f"Creating graph-viewer directory: {self.graph_viewer_dir}")
            self.graph_viewer_dir.mkdir(parents=True, exist_ok=True)
            
        try:
            files_copied = 0
            for file in ["graph_nodes.json", "graph_edges.json", "graph_metadata.json"]:
                src = self.tmp_dir / file
                dst = self.graph_viewer_dir / file
                if src.exists():
                    shutil.copy2(src, dst)
                    file_size = src.stat().st_size
                    print(f"✅ Copied {file} ({file_size:,} bytes) to graph-viewer")
                    files_copied += 1
                else:
                    print(f"⚠️  Source file not found: {src}")
            
            if files_copied > 0:
                print(f"🎉 Successfully copied {files_copied} files to graph-viewer!")
                print(f"📊 View results at: {self.graph_viewer_dir}")
                print("🌐 Open graph-viewer/public/d3-graph.html to visualize the knowledge graph")
            else:
                print("❌ No files were copied")
                    
        except Exception as e:
            print(f"❌ Error copying to graph-viewer: {e}")
            
    def save_test_report(self):
        """Save comprehensive test report."""
        report_file = self.tmp_dir / "alternative_extractors_test_report.json"
        
        self.results["end_time"] = datetime.now().isoformat()
        self.results["summary"]["total_tests"] = len(self.results["tests"])
        self.results["summary"]["total_errors"] = sum(len(test.get("errors", [])) for test in self.results["tests"])
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\nTest report saved to: {report_file}")
        
    def run_all_tests(self):
        """Run the complete test suite."""
        print("COMPREHENSIVE ALTERNATIVE EXTRACTORS TEST")
        print("=" * 50)
        
        try:
            # Setup
            self.setup_test_environment()
            baseline_stats = self.load_baseline_stats()
            
            # Run entity extraction tests
            entity_test_result = self.test_entity_extraction()
            self.results["tests"].append(entity_test_result)
            
            # Run relationship extraction tests  
            relationship_test_result = self.test_relationship_extraction()
            self.results["tests"].append(relationship_test_result)
            
            # Analyze results
            analysis = self.analyze_results(baseline_stats)
            self.results["analysis"] = analysis
            
            # Copy results for visualization
            self.copy_results_to_graph_viewer()
            
            # Save final report
            self.save_test_report()
            
            print("\n" + "=" * 50)
            print("COMPREHENSIVE TEST COMPLETED SUCCESSFULLY")
            print("=" * 50)
            
        except Exception as e:
            print(f"\nFATAL ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    runner = ComprehensiveTestRunner()
    runner.run_all_tests() 