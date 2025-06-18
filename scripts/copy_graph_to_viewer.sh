#!/bin/bash

# Script to copy graph memory files from agent_memories to graph-viewer
# Usage: ./copy_graph_to_viewer.sh --guid <conversation_guid>

set -e  # Exit on any error

# Default values
GUID=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Function to show usage
show_usage() {
    echo "Usage: $0 --guid <conversation_guid>"
    echo ""
    echo "Copy graph memory files from agent_memories to graph-viewer for visualization"
    echo ""
    echo "Arguments:"
    echo "  --guid <guid>    Required. The conversation GUID to copy graph data from"
    echo ""
    echo "Example:"
    echo "  $0 --guid abc123def-456-789-ghi"
    echo ""
    echo "Source: agent_memories/standard/<guid>/agent_memory_graph_data/*"
    echo "Destination: graph-viewer/public/sample-data/"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --guid)
            GUID="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "❌ Unknown argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$GUID" ]]; then
    echo "❌ Error: --guid argument is required"
    show_usage
    exit 1
fi

# Define paths
SOURCE_DIR="$WORKSPACE_ROOT/agent_memories/standard/$GUID/agent_memory_graph_data"
DEST_DIR="$WORKSPACE_ROOT/graph-viewer/public/sample-data"

echo "🔍 Copying graph memory files for conversation: $GUID"
echo "📂 Source: $SOURCE_DIR"
echo "📂 Destination: $DEST_DIR"
echo ""

# Check if source directory exists
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "❌ Error: Source directory not found: $SOURCE_DIR"
    echo ""
    echo "💡 Make sure:"
    echo "   1. The conversation GUID is correct"
    echo "   2. The agent memory has been created for this conversation"
    echo "   3. Graph data has been generated"
    exit 1
fi

# Create destination directory if it doesn't exist
if [[ ! -d "$DEST_DIR" ]]; then
    echo "📁 Creating destination directory: $DEST_DIR"
    mkdir -p "$DEST_DIR"
fi

# Copy graph files
FILES_COPIED=0
TOTAL_SIZE=0

for file in "graph_nodes.json" "graph_edges.json" "graph_metadata.json"; do
    SOURCE_FILE="$SOURCE_DIR/$file"
    DEST_FILE="$DEST_DIR/$file"
    
    if [[ -f "$SOURCE_FILE" ]]; then
        cp "$SOURCE_FILE" "$DEST_FILE"
        FILE_SIZE=$(stat -f%z "$SOURCE_FILE" 2>/dev/null || stat -c%s "$SOURCE_FILE" 2>/dev/null || echo "0")
        TOTAL_SIZE=$((TOTAL_SIZE + FILE_SIZE))
        FILES_COPIED=$((FILES_COPIED + 1))
        # Format file size in human readable format
        if command -v numfmt >/dev/null 2>&1; then
            FORMATTED_SIZE="$(numfmt --to=iec-i --suffix=B $FILE_SIZE)"
        else
            # Fallback for macOS
            if [[ $FILE_SIZE -gt 1048576 ]]; then
                FORMATTED_SIZE="$(echo "scale=1; $FILE_SIZE/1048576" | bc)MB"
            elif [[ $FILE_SIZE -gt 1024 ]]; then
                FORMATTED_SIZE="$(echo "scale=1; $FILE_SIZE/1024" | bc)KB"
            else
                FORMATTED_SIZE="${FILE_SIZE}B"
            fi
        fi
        echo "✅ Copied $file ($FORMATTED_SIZE)"
    else
        echo "⚠️  File not found: $file"
    fi
done

echo ""

if [[ $FILES_COPIED -gt 0 ]]; then
    # Format total size in human readable format
    if command -v numfmt >/dev/null 2>&1; then
        FORMATTED_TOTAL="$(numfmt --to=iec-i --suffix=B $TOTAL_SIZE)"
    else
        # Fallback for macOS
        if [[ $TOTAL_SIZE -gt 1048576 ]]; then
            FORMATTED_TOTAL="$(echo "scale=1; $TOTAL_SIZE/1048576" | bc)MB"
        elif [[ $TOTAL_SIZE -gt 1024 ]]; then
            FORMATTED_TOTAL="$(echo "scale=1; $TOTAL_SIZE/1024" | bc)KB"
        else
            FORMATTED_TOTAL="${TOTAL_SIZE}B"
        fi
    fi
    echo "🎉 Successfully copied $FILES_COPIED files ($FORMATTED_TOTAL total)"
    echo "📊 Graph data is now available in graph-viewer"
    echo "🌐 Open graph-viewer/public/d3-graph.html to visualize the knowledge graph"
    echo ""
    echo "📈 Quick stats:"
    
    # Show quick stats from the files
    if [[ -f "$DEST_DIR/graph_nodes.json" ]]; then
        NODE_COUNT=$(jq 'length' "$DEST_DIR/graph_nodes.json" 2>/dev/null || echo "unknown")
        echo "   📍 Nodes: $NODE_COUNT"
    fi
    
    if [[ -f "$DEST_DIR/graph_edges.json" ]]; then
        EDGE_COUNT=$(jq 'length' "$DEST_DIR/graph_edges.json" 2>/dev/null || echo "unknown")
        echo "   🔗 Edges: $EDGE_COUNT"
    fi
    
    if [[ -f "$DEST_DIR/graph_metadata.json" ]]; then
        LAST_UPDATED=$(jq -r '.last_updated // "unknown"' "$DEST_DIR/graph_metadata.json" 2>/dev/null || echo "unknown")
        echo "   🕒 Last updated: $LAST_UPDATED"
    fi
else
    echo "❌ No files were copied"
    echo "💡 Check that the conversation has generated graph memory data"
    exit 1
fi 