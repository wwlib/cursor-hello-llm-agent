"""
Graph Storage

Handles persistence of graph data with JSON serialization.
"""

import json
import os
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime


class GraphStorage:
    """Handles graph data persistence with JSON files."""
    
    def __init__(self, storage_path: str):
        """
        Initialize graph storage.
        
        Args:
            storage_path: Directory path for storing graph files
        """
        self.storage_path = storage_path
        self.nodes_file = os.path.join(storage_path, "graph_nodes.json")
        self.edges_file = os.path.join(storage_path, "graph_edges.json")
        self.metadata_file = os.path.join(storage_path, "graph_metadata.json")
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        # Initialize files if they don't exist
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize storage files if they don't exist."""
        if not os.path.exists(self.nodes_file):
            self._save_json(self.nodes_file, {})
        
        if not os.path.exists(self.edges_file):
            self._save_json(self.edges_file, [])
        
        if not os.path.exists(self.metadata_file):
            metadata = {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
                "node_count": 0,
                "edge_count": 0
            }
            self._save_json(self.metadata_file, metadata)
    
    def _load_json(self, file_path: str) -> Any:
        """Load JSON data from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {} if 'nodes' in file_path else []
    
    def _save_json(self, file_path: str, data: Any) -> None:
        """Save data to JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Load all nodes from storage."""
        return self._load_json(self.nodes_file)
    
    def save_nodes(self, nodes: Dict[str, Dict[str, Any]]) -> None:
        """Save nodes to storage."""
        self._save_json(self.nodes_file, nodes)
        self._update_metadata(node_count=len(nodes))
    
    def load_edges(self) -> List[Dict[str, Any]]:
        """Load all edges from storage."""
        return self._load_json(self.edges_file)
    
    def save_edges(self, edges: List[Dict[str, Any]]) -> None:
        """Save edges to storage."""
        self._save_json(self.edges_file, edges)
        self._update_metadata(edge_count=len(edges))
    
    def load_metadata(self) -> Dict[str, Any]:
        """Load graph metadata."""
        return self._load_json(self.metadata_file)
    
    def _update_metadata(self, **kwargs) -> None:
        """Update metadata with provided fields."""
        metadata = self.load_metadata()
        metadata["last_updated"] = datetime.now().isoformat()
        metadata.update(kwargs)
        self._save_json(self.metadata_file, metadata)
    
    def create_backup(self, backup_suffix: str = None) -> str:
        """
        Create a backup of the current graph state.
        
        Args:
            backup_suffix: Optional suffix for backup files
            
        Returns:
            Backup directory path
        """
        if backup_suffix is None:
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_dir = os.path.join(self.storage_path, f"backup_{backup_suffix}")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy current files to backup
        import shutil
        for file_path in [self.nodes_file, self.edges_file, self.metadata_file]:
            if os.path.exists(file_path):
                backup_file = os.path.join(backup_dir, os.path.basename(file_path))
                shutil.copy2(file_path, backup_file)
        
        return backup_dir
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        metadata = self.load_metadata()
        nodes = self.load_nodes()
        edges = self.load_edges()
        
        stats = {
            "metadata": metadata,
            "actual_node_count": len(nodes),
            "actual_edge_count": len(edges),
            "storage_path": self.storage_path,
            "files_exist": {
                "nodes": os.path.exists(self.nodes_file),
                "edges": os.path.exists(self.edges_file),
                "metadata": os.path.exists(self.metadata_file)
            }
        }
        
        if os.path.exists(self.nodes_file):
            stats["nodes_file_size"] = os.path.getsize(self.nodes_file)
        if os.path.exists(self.edges_file):
            stats["edges_file_size"] = os.path.getsize(self.edges_file)
        
        return stats