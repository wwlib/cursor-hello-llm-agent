"""
Test Graph Memory Module

Unit tests for the knowledge graph memory system.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, MagicMock

import sys
from pathlib import Path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.memory.graph_memory import GraphManager, EntityExtractor, RelationshipExtractor, GraphQueries
from src.memory.graph_memory.graph_storage import GraphStorage


class TestGraphStorage(unittest.TestCase):
    """Test graph storage functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = GraphStorage(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test storage initialization."""
        self.assertTrue(os.path.exists(self.storage.nodes_file))
        self.assertTrue(os.path.exists(self.storage.edges_file))
        self.assertTrue(os.path.exists(self.storage.metadata_file))
        
        # Test initial data
        nodes = self.storage.load_nodes()
        edges = self.storage.load_edges()
        metadata = self.storage.load_metadata()
        
        self.assertEqual(nodes, {})
        self.assertEqual(edges, [])
        self.assertIn('created_at', metadata)
        self.assertIn('version', metadata)
    
    def test_save_load_nodes(self):
        """Test saving and loading nodes."""
        test_nodes = {
            'node1': {'id': 'node1', 'type': 'character', 'name': 'Test'}
        }
        
        self.storage.save_nodes(test_nodes)
        loaded_nodes = self.storage.load_nodes()
        
        self.assertEqual(loaded_nodes, test_nodes)
    
    def test_save_load_edges(self):
        """Test saving and loading edges."""
        test_edges = [
            {'id': 'edge1', 'from_node_id': 'node1', 'to_node_id': 'node2', 'relationship': 'knows'}
        ]
        
        self.storage.save_edges(test_edges)
        loaded_edges = self.storage.load_edges()
        
        self.assertEqual(loaded_edges, test_edges)


class TestGraphManager(unittest.TestCase):
    """Test graph manager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock embeddings manager
        self.mock_embeddings = Mock()
        self.mock_embeddings.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        self.graph_manager = GraphManager(
            storage_path=self.temp_dir,
            embeddings_manager=self.mock_embeddings,
            similarity_threshold=0.8
        )
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_add_new_node(self):
        """Test adding a new node."""
        node, is_new = self.graph_manager.add_or_update_node(
            name="Test Character",
            node_type="character",
            description="A test character for unit testing"
        )
        
        self.assertTrue(is_new)
        self.assertEqual(node.name, "Test Character")
        self.assertEqual(node.type, "character")
        self.assertIn("character_", node.id)
        self.assertEqual(len(self.graph_manager.nodes), 1)
    
    def test_update_existing_node(self):
        """Test updating an existing node via similarity matching."""
        # Add first node
        node1, is_new1 = self.graph_manager.add_or_update_node(
            name="Test Character",
            node_type="character", 
            description="A test character"
        )
        
        # Mock high similarity for second addition
        self.graph_manager._cosine_similarity = Mock(return_value=0.9)
        
        # Add similar node - should update existing
        node2, is_new2 = self.graph_manager.add_or_update_node(
            name="Test Char",  # Different name
            node_type="character",
            description="A test character with similar description"
        )
        
        self.assertFalse(is_new2)  # Should be update, not new
        self.assertEqual(node1.id, node2.id)  # Same node
        self.assertEqual(node2.mention_count, 2)  # Incremented
        self.assertIn("Test Char", node2.aliases)  # Name added as alias
        self.assertEqual(len(self.graph_manager.nodes), 1)  # Still only one node
    
    def test_add_edge(self):
        """Test adding edges between nodes."""
        # Add two nodes
        node1, _ = self.graph_manager.add_or_update_node("Character A", "character", "First character")
        node2, _ = self.graph_manager.add_or_update_node("Location B", "location", "Test location")
        
        # Add edge
        edge = self.graph_manager.add_edge(
            from_node_id=node1.id,
            to_node_id=node2.id,
            relationship="located_in",
            weight=1.0
        )
        
        self.assertEqual(edge.from_node_id, node1.id)
        self.assertEqual(edge.to_node_id, node2.id)
        self.assertEqual(edge.relationship, "located_in")
        self.assertEqual(len(self.graph_manager.edges), 1)
    
    def test_find_connected_nodes(self):
        """Test finding connected nodes."""
        # Add nodes and edge
        node1, _ = self.graph_manager.add_or_update_node("Character A", "character", "First character")
        node2, _ = self.graph_manager.add_or_update_node("Location B", "location", "Test location")
        
        self.graph_manager.add_edge(node1.id, node2.id, "located_in")
        
        # Test connection
        connected = self.graph_manager.get_connected_nodes(node1.id)
        self.assertEqual(len(connected), 1)
        self.assertEqual(connected[0][0].id, node2.id)
        self.assertEqual(connected[0][1].relationship, "located_in")
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]
        
        # Orthogonal vectors
        sim1 = GraphManager._cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(sim1, 0.0, places=5)
        
        # Identical vectors
        sim2 = GraphManager._cosine_similarity(vec1, vec3)
        self.assertAlmostEqual(sim2, 1.0, places=5)


class TestEntityExtractor(unittest.TestCase):
    """Test entity extraction functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock LLM service
        self.mock_llm = Mock()
        self.mock_llm.generate.return_value = '''
        [
            {"type": "character", "name": "Eldara", "description": "A fire wizard who runs a magic shop"},
            {"type": "location", "name": "Riverwatch", "description": "A town with a magic shop"}
        ]
        '''
        
        # Domain config for D&D
        self.domain_config = {"domain_name": "dnd_campaign"}
        
        self.entity_extractor = EntityExtractor(
            llm_service=self.mock_llm,
            domain_config=self.domain_config
        )
    
    def test_extract_entities(self):
        """Test entity extraction from text."""
        text = "Eldara the fire wizard runs a magic shop in Riverwatch."
        
        entities = self.entity_extractor.extract_entities(text)
        
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0]['name'], 'Eldara')
        self.assertEqual(entities[0]['type'], 'character')
        self.assertEqual(entities[1]['name'], 'Riverwatch')
        self.assertEqual(entities[1]['type'], 'location')
    
    def test_entity_validation(self):
        """Test entity validation."""
        # Valid entity
        valid_entity = {
            "type": "character",
            "name": "Test",
            "description": "A test character"
        }
        self.assertTrue(self.entity_extractor._validate_entity(valid_entity))
        
        # Invalid entities
        invalid_entities = [
            {"type": "character", "name": ""},  # Empty name
            {"type": "invalid_type", "name": "Test", "description": "Test"},  # Invalid type
            {"name": "Test", "description": "Test"},  # Missing type
            {"type": "character", "name": "Test", "description": ""},  # Empty description
        ]
        
        for invalid_entity in invalid_entities:
            self.assertFalse(self.entity_extractor._validate_entity(invalid_entity))


class TestRelationshipExtractor(unittest.TestCase):
    """Test relationship extraction functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock LLM service
        self.mock_llm = Mock()
        self.mock_llm.generate.return_value = '''
        [
            {
                "from_entity": "Eldara",
                "to_entity": "Riverwatch",
                "relationship": "located_in",
                "confidence": 0.9,
                "evidence": "Eldara runs a shop in Riverwatch"
            }
        ]
        '''
        
        self.domain_config = {"domain_name": "dnd_campaign"}
        
        self.relationship_extractor = RelationshipExtractor(
            llm_service=self.mock_llm,
            domain_config=self.domain_config
        )
    
    def test_extract_relationships(self):
        """Test relationship extraction."""
        text = "Eldara runs a magic shop in Riverwatch."
        entities = [
            {"name": "Eldara", "type": "character", "description": "A fire wizard"},
            {"name": "Riverwatch", "type": "location", "description": "A town"}
        ]
        
        relationships = self.relationship_extractor.extract_relationships(text, entities)
        
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0]['from_entity'], 'Eldara')
        self.assertEqual(relationships[0]['to_entity'], 'Riverwatch')
        self.assertEqual(relationships[0]['relationship'], 'located_in')


class TestGraphQueries(unittest.TestCase):
    """Test graph query functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create graph manager with test data
        self.graph_manager = GraphManager(
            storage_path=self.temp_dir,
            embeddings_manager=None,  # No embeddings for unit tests
            similarity_threshold=0.8
        )
        
        # Add test data
        self.char_node, _ = self.graph_manager.add_or_update_node(
            "Eldara", "character", "A fire wizard"
        )
        self.loc_node, _ = self.graph_manager.add_or_update_node(
            "Riverwatch", "location", "A town"
        )
        self.graph_manager.add_edge(
            self.char_node.id, self.loc_node.id, "located_in"
        )
        
        self.graph_queries = GraphQueries(self.graph_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_find_entity_context(self):
        """Test finding entity context."""
        context = self.graph_queries.find_entity_context("Eldara")
        
        self.assertTrue(context['found'])
        self.assertEqual(context['entity']['name'], 'Eldara')
        self.assertEqual(context['direct_connections'], 1)
        self.assertIn('located_in', context['relationships'])
    
    def test_find_entities_by_type(self):
        """Test finding entities by type."""
        characters = self.graph_queries.find_entities_by_type("character")
        locations = self.graph_queries.find_entities_by_type("location")
        
        self.assertEqual(len(characters), 1)
        self.assertEqual(characters[0]['name'], 'Eldara')
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0]['name'], 'Riverwatch')
    
    def test_find_path_between_entities(self):
        """Test finding path between entities."""
        path = self.graph_queries.find_path_between_entities("Eldara", "Riverwatch")
        
        self.assertIsNotNone(path)
        self.assertTrue(path['path_found'])
        self.assertEqual(path['path_length'], 1)
        self.assertEqual(path['path'][0]['relationship'], 'located_in')


if __name__ == '__main__':
    unittest.main()