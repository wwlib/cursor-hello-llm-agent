# Python Documentation Best Practices & Tools

## 1. Sphinx (Most Popular - JSDoc Equivalent)

Sphinx is the de facto standard for Python documentation, used by Python itself and most major libraries.

### Setup

```bash
pip install sphinx sphinx-autobuild sphinx-rtd-theme
```

### Configuration (`docs/conf.py`)

```python
# Configuration file for the Sphinx documentation builder
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

project = 'LLM Agent Framework'
copyright = '2024, Your Name'
author = 'Your Name'

extensions = [
    'sphinx.ext.autodoc',       # Auto-generate docs from docstrings
    'sphinx.ext.viewcode',      # Add source code links
    'sphinx.ext.napoleon',     # Support Google/NumPy style docstrings
    'sphinx.ext.intersphinx',  # Link to other documentation
    'sphinx.ext.githubpages',  # GitHub Pages support
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Auto-generate API documentation
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
```

### Usage

```bash
# Generate documentation
sphinx-apidoc -o docs src/
sphinx-build -b html docs docs/_build/html

# Live reload during development
sphinx-autobuild docs docs/_build/html
```

## 2. MkDocs + mkdocstrings (Modern Alternative)

A more modern, markdown-based approach similar to GitBook.

### Setup

```bash
pip install mkdocs mkdocstrings[python] mkdocs-material
```

### Configuration (`mkdocs.yml`)

```yaml
site_name: LLM Agent Framework
site_description: Comprehensive documentation for the LLM Agent Framework
site_url: https://yourname.github.io/llm-agent-framework

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate
    - search.suggest
    - search.highlight
    - content.tabs.link
    - content.code.annotation
    - content.code.copy
  language: en
  palette:
    - scheme: default
      toggle:
        icon: material/toggle-switch-off-outline 
        name: Switch to dark mode
      primary: teal
      accent: purple 
    - scheme: slate 
      toggle:
        icon: material/toggle-switch
        name: Switch to light mode    
      primary: teal
      accent: lime

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
            docstring_options:
              ignore_init_summary: true
            merge_init_into_class: true
            show_submodules: true

nav:
  - Home: index.md
  - API Reference:
    - Graph Memory: api/graph_memory.md
    - Memory Manager: api/memory_manager.md
  - Examples: examples.md
```

### API Documentation (`docs/api/graph_memory.md`)

```markdown
# Graph Memory System

::: src.memory.graph_memory.graph_manager.GraphManager
    options:
      show_root_heading: true
      show_source: true
      
::: src.memory.graph_memory.graph_manager.GraphNode

::: src.memory.graph_memory.graph_manager.GraphEdge
```

## 3. pdoc (Automatic API Documentation)

Minimal setup, automatic generation - closest to JSDoc simplicity.

### Setup & Usage

```bash
pip install pdoc3

# Generate HTML documentation
pdoc --html --output-dir docs src/memory/graph_memory/

# Serve with live reload
pdoc --http localhost:8080 src/memory/graph_memory/
```

## 4. Pydantic for API Documentation

If using Pydantic models, automatic OpenAPI/JSON Schema generation:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class GraphNodeModel(BaseModel):
    """Graph node representation for API serialization.
    
    This model defines the structure for graph nodes when serialized
    to JSON for API responses or storage.
    """
    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Entity type (character, location, etc.)")
    name: str = Field(..., description="Primary entity name")
    description: str = Field(..., description="Detailed entity description")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    mention_count: int = Field(default=1, description="Number of mentions")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "character_001",
                "type": "character", 
                "name": "Eldara",
                "description": "A fire wizard who runs a magic shop",
                "aliases": ["the wizard", "fire mage"],
                "mention_count": 3
            }
        }
```

## 5. Google Style Docstring Reference

### Class Documentation

```python
class GraphManager:
    """Main graph management system with RAG-based entity resolution.
    
    Longer description of the class purpose, architecture, and key features.
    Can include multiple paragraphs and detailed explanations.
    
    Attributes:
        storage: GraphStorage instance for persistence.
        nodes: Dictionary of loaded graph nodes.
        similarity_threshold: Threshold for entity matching.
        
    Example:
        Basic usage example:
        
        ```python
        manager = GraphManager("./graph_data")
        node, is_new = manager.add_or_update_node(
            name="Eldara",
            node_type="character",
            description="A fire wizard"
        )
        ```
        
    Note:
        Requires embeddings_manager for similarity matching.
        
    Warning:
        Storage path must be writable.
    """
```

### Method Documentation

```python
def add_or_update_node(self, name: str, node_type: str, description: str,
                      **attributes) -> Tuple[GraphNode, bool]:
    """Add a new node or update existing one using semantic similarity.
    
    This method implements the core duplicate prevention logic by searching
    for similar existing entities and either updating them or creating new ones.
    
    Args:
        name: Entity name/identifier. Must be non-empty string.
        node_type: Type of entity. Must match domain configuration.
        description: Detailed description for semantic embedding.
                    Used as primary text for similarity matching.
        **attributes: Additional custom attributes stored with entity.
        
    Returns:
        A tuple containing:
        - GraphNode: The created or updated node instance
        - bool: True if new node created, False if existing updated
        
    Raises:
        ValueError: If name is empty or node_type is invalid.
        StorageError: If unable to save to storage.
        
    Example:
        ```python
        # Add new character entity
        node, is_new = manager.add_or_update_node(
            name="Eldara",
            node_type="character", 
            description="A fire wizard who runs a magic shop",
            profession="wizard",
            magic_type="fire"
        )
        
        if is_new:
            print(f"Created: {node.name}")
        else:
            print(f"Updated: {node.name} (mentions: {node.mention_count})")
        ```
        
    Note:
        Semantic similarity requires embeddings_manager configuration.
        Without it, only exact name matching prevents duplicates.
    """
```

### Function Documentation

```python
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors.
    
    Computes the cosine of the angle between two non-zero vectors,
    which measures their directional similarity regardless of magnitude.
    
    Args:
        vec1: First vector as list of floats.
        vec2: Second vector as list of floats. Must be same length as vec1.
        
    Returns:
        Cosine similarity score between -1.0 and 1.0, where:
        - 1.0: Vectors point in same direction (identical)
        - 0.0: Vectors are orthogonal (unrelated)
        - -1.0: Vectors point in opposite directions
        
    Raises:
        ValueError: If vectors have different lengths or are empty.
        ZeroDivisionError: If either vector has zero magnitude.
        
    Example:
        ```python
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0] 
        similarity = cosine_similarity(v1, v2)  # Returns 0.0
        ```
    """
```

## 6. Project Documentation Structure

```
docs/
├── conf.py                 # Sphinx configuration
├── index.rst              # Main documentation page
├── api/                    # Auto-generated API docs
│   ├── graph_memory.rst
│   ├── memory_manager.rst
│   └── embeddings.rst
├── guides/                 # User guides
│   ├── quickstart.md
│   ├── configuration.md
│   └── examples.md
├── _static/               # Static assets (CSS, images)
└── _templates/            # Custom templates

# Alternative MkDocs structure
docs/
├── mkdocs.yml
├── index.md
├── api/
│   ├── graph_memory.md
│   └── memory_manager.md
├── guides/
│   ├── getting-started.md
│   └── examples.md
└── assets/
```

## 7. Automation with GitHub Actions

```yaml
# .github/workflows/docs.yml
name: Documentation

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
        
    - name: Install dependencies
      run: |
        pip install sphinx sphinx-rtd-theme
        pip install -r requirements.txt
        
    - name: Build documentation
      run: |
        sphinx-apidoc -o docs src/
        sphinx-build -b html docs docs/_build/html
        
    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      if: github.ref == 'refs/heads/main'
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: docs/_build/html
```

## 8. Documentation Comments vs Docstrings

```python
# Wrong: Regular comments don't generate documentation
class GraphNode:
    # This represents a graph node
    # It has various attributes
    
    def __init__(self, node_id):
        # Initialize the node
        pass

# Correct: Docstrings are accessible to documentation tools
class GraphNode:
    """Represents a node in the knowledge graph.
    
    GraphNode stores entity information and supports similarity matching.
    """
    
    def __init__(self, node_id: str):
        """Initialize a new graph node.
        
        Args:
            node_id: Unique identifier for the node.
        """
        pass
```

## 9. Type Hints for Better Documentation

```python
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

@dataclass
class GraphStats:
    """Statistics about the graph state.
    
    Attributes:
        node_count: Total number of nodes.
        edge_count: Total number of edges.
        node_types: Count of each node type.
    """
    node_count: int
    edge_count: int
    node_types: Dict[str, int]

def query_graph(
    query: str, 
    max_results: int = 5,
    include_embeddings: bool = False
) -> List[Dict[str, Union[str, float, List[str]]]]:
    """Query the graph with type hints for clear API."""
    pass
```

## Summary

**Recommendation for your project:**

1. **Use Sphinx + Google Style docstrings** (as shown in the graph_manager.py example)
2. **Add type hints** for clearer API documentation  
3. **Set up GitHub Actions** for automatic documentation deployment
4. **Consider MkDocs** if you prefer Markdown over reStructuredText

This gives you JSDoc-equivalent functionality with automatic API documentation generation, cross-references, search, and professional presentation. 