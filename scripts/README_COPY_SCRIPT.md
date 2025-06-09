# Graph Memory Copy Script

## Overview

The `copy_graph_to_viewer.sh` script copies graph memory files from agent conversations to the graph-viewer for visualization.

**Location**: This script is located in the `/scripts/` directory at the project root for easy access across the entire project.

## Usage

```bash
scripts/copy_graph_to_viewer.sh --guid <conversation_guid>
```

## Arguments

- `--guid <guid>` - **Required**. The conversation GUID to copy graph data from
- `--help` - Show usage information

## Example

```bash
# Copy graph data from conversation dnd5g8
scripts/copy_graph_to_viewer.sh --guid dnd5g8

# Show help
scripts/copy_graph_to_viewer.sh --help
```

## File Paths

**Source**: `agent_memories/standard/<guid>/agent_memory_graph_data/`
- `graph_nodes.json` - Entity nodes in the knowledge graph
- `graph_edges.json` - Relationships between entities  
- `graph_metadata.json` - Graph metadata and statistics

**Destination**: `graph-viewer/public/sample-data/`
- Files are copied with the same names for graph-viewer consumption

## Features

- ✅ **Cross-platform compatible** - Works on both macOS and Linux
- ✅ **Robust error handling** - Clear error messages and validation
- ✅ **Rich feedback** - File sizes, stats, and visual indicators
- ✅ **Automatic directory creation** - Creates destination if needed
- ✅ **Graph statistics** - Shows node count, edge count, and last updated

## Sample Output

```
🔍 Copying graph memory files for conversation: dnd5g8
📂 Source: /path/to/agent_memories/standard/dnd5g8/agent_memory_graph_data
📂 Destination: /path/to/graph-viewer/public/sample-data

✅ Copied graph_nodes.json (4.3KB)
✅ Copied graph_edges.json (4.0KB) 
✅ Copied graph_metadata.json (155B)

🎉 Successfully copied 3 files (8.4KB total)
📊 Graph data is now available in graph-viewer
🌐 Open graph-viewer/public/d3-graph.html to visualize the knowledge graph

📈 Quick stats:
   📍 Nodes: 13
   🔗 Edges: 9
   🕒 Last updated: 2025-06-08T19:11:30.170863
```

## Error Handling

The script provides helpful error messages:

- Missing `--guid` argument
- Invalid conversation GUID
- Missing source directory
- Missing graph files

## Integration

This script complements the existing test framework:
- `run_comprehensive_test.sh` - Tests alternative extractors and auto-copies results
- `copy_graph_to_viewer.sh` - Copies specific conversation graph data
- Graph-viewer - Visualizes the copied graph data

## Prerequisites

- `jq` - For parsing JSON files and showing statistics
- `bc` - For file size calculations on macOS (usually pre-installed) 