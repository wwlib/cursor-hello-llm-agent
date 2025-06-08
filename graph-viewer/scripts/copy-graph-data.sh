#!/bin/bash

# Script to copy graph data from agent memories to the viewer's public directory
# Usage: ./copy-graph-data.sh [agent_guid]
# If no agent_guid is provided, it will list available agents

AGENT_MEMORIES_DIR="../agent_memories/standard"
PUBLIC_DATA_DIR="./public/sample-data"

if [ $# -eq 0 ]; then
    echo "Available agent memory directories:"
    ls -1 "$AGENT_MEMORIES_DIR"
    echo ""
    echo "Usage: $0 <agent_guid>"
    echo "Example: $0 dnd5g6"
    exit 1
fi

AGENT_GUID=$1
SOURCE_DIR="$AGENT_MEMORIES_DIR/$AGENT_GUID/agent_memory_graph_data"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Directory $SOURCE_DIR does not exist"
    echo "Available agent directories:"
    ls -1 "$AGENT_MEMORIES_DIR"
    exit 1
fi

# Create public data directory if it doesn't exist
mkdir -p "$PUBLIC_DATA_DIR"

# Copy the graph files
if [ -f "$SOURCE_DIR/graph_nodes.json" ] && [ -f "$SOURCE_DIR/graph_edges.json" ]; then
    cp "$SOURCE_DIR/graph_nodes.json" "$PUBLIC_DATA_DIR/"
    cp "$SOURCE_DIR/graph_edges.json" "$PUBLIC_DATA_DIR/"
    cp "$SOURCE_DIR/graph_metadata.json" "$PUBLIC_DATA_DIR/" 2>/dev/null || true
    echo "Successfully copied graph data from $AGENT_GUID to $PUBLIC_DATA_DIR"
    echo "Graph files copied:"
    ls -la "$PUBLIC_DATA_DIR"
else
    echo "Error: graph_nodes.json and/or graph_edges.json not found in $SOURCE_DIR"
fi