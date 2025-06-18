# Graph Viewer Usage Guide

## Quick Start

1. **Install dependencies**:
   ```bash
   cd graph-viewer
   npm install
   ```

2. **Start the application**:
   ```bash
   npm start
   ```
   The app will open at http://localhost:3000

3. **Load sample data**:
   Click "Load Sample D&D Data" to see the pre-loaded graph

## Loading Your Own Graph Data

### Method 1: Copy Script (Recommended)
Use the provided script to copy data from your agent's memory:

```bash
cd graph-viewer
./scripts/copy-graph-data.sh dnd5g6
npm start
```

Then click "Load Sample D&D Data" in the app.

### Method 2: File Upload
1. Navigate to your agent's graph data directory:
   ```
   agent_memories/standard/{your_agent_guid}/agent_memory_graph_data/
   ```
2. Download/copy the `graph_nodes.json` and `graph_edges.json` files
3. In the graph viewer, use the file upload controls to select these files
4. Click "Load Graph"

## Graph Visualization Features

### Node Interactions
- **Click**: View detailed information about an entity
- **Right-click**: Focus the camera on that node
- **Hover**: See a tooltip with basic information

### Navigation
- **Mouse wheel**: Zoom in/out
- **Click and drag**: Pan around the graph
- **Reset View button**: Fit all nodes in the viewport

### Visual Elements
- **Node size**: Proportional to mention count (how often the entity appears)
- **Node color**: Indicates entity type (character, location, object, etc.)
- **Link arrows**: Show the direction of relationships
- **Link color**: Indicates relationship type
- **Link thickness**: Proportional to relationship weight

## Understanding the Data

### Entity Types (Colors)
- 🔴 **Character** (Red): People, NPCs, player characters
- 🟢 **Location** (Teal): Places, areas, regions  
- 🔵 **Object** (Blue): Items, artifacts, tools
- 🟡 **Event** (Yellow): Actions, occurrences, happenings
- 🟣 **Concept** (Purple): Ideas, abstractions, magic systems
- 🟦 **Organization** (Cyan): Groups, factions, institutions

### Relationship Types
- **located_in**: Physical containment (character in location)
- **owns**: Ownership relationships (character owns object)
- **member_of**: Group membership (character member of organization)
- **allies_with** / **enemies_with**: Social relationships
- **uses**: Functional relationships (character uses object)
- **created_by**: Creation relationships (object created by character)
- **leads_to**: Sequential connections (event leads to event)
- **participates_in**: Event participation (character participates in event)
- **related_to**: General associations

## Troubleshooting

### Graph Won't Load
- Check that your JSON files are valid
- Ensure nodes file is an object with entity IDs as keys
- Ensure edges file is an array of relationship objects
- Check browser console for error messages

### Performance Issues
- Large graphs (>500 nodes) may be slow to render
- Try reducing the cooldown ticks or adjusting force parameters
- Consider filtering your data to focus on specific entity types

### File Upload Not Working
- Ensure you're selecting JSON files
- Check file permissions
- Try downloading files locally first, then uploading

## Data Export

The graph viewer is read-only. To modify graph data, you need to:
1. Work with the LLM Agent Framework
2. Use the agent's conversation system to add new entities/relationships
3. Refresh the graph viewer with updated data

## Example Workflow

1. Run an agent conversation session:
   ```bash
   python examples/agent_usage_example.py --config dnd --guid my-campaign
   ```

2. After some conversations, copy the graph data:
   ```bash
   cd graph-viewer
   ./scripts/copy-graph-data.sh my-campaign
   ```

3. View the updated graph:
   ```bash
   npm start
   # Click "Load Sample D&D Data"
   ```

This creates a feedback loop where you can see how conversations build knowledge graphs over time.