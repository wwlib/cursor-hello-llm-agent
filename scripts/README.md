# Scripts Directory

This directory contains utility scripts for the LLM Agent Framework project.

## Available Scripts

### `copy_graph_to_viewer.sh`

Copies graph memory files from agent conversations to the graph-viewer for visualization.

**Usage:**
```bash
scripts/copy_graph_to_viewer.sh --guid <conversation_guid>
```

**Purpose:**
- Extract graph data from specific agent memory conversations
- Copy to graph-viewer for interactive visualization
- Useful for analyzing knowledge graphs from real conversations

**See also:** [`README_COPY_SCRIPT.md`](README_COPY_SCRIPT.md) for detailed documentation.

## Usage from Project Root

All scripts are designed to be run from the project root directory:

```bash
# Run from project root
scripts/copy_graph_to_viewer.sh --guid dnd5g8
```

## Adding New Scripts

When adding new utility scripts to this directory:

1. Make them executable: `chmod +x script_name.sh`
2. Design them to work from the project root
3. Use robust path resolution: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`
4. Include comprehensive help text and error handling
5. Add documentation to this README 