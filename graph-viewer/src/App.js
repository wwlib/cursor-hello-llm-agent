import React, { useState, useCallback, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import './App.css';

const App = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const fgRef = useRef();

  // Color mapping for different entity types
  const getNodeColor = (node) => {
    const colorMap = {
      character: '#ff6b6b',
      location: '#4ecdc4',
      object: '#45b7d1',
      event: '#f7b731',
      concept: '#5f27cd',
      organization: '#00d2d3'
    };
    return colorMap[node.type] || '#95a5a6';
  };

  // Color mapping for different relationship types
  const getLinkColor = (link) => {
    const colorMap = {
      located_in: '#3498db',
      owns: '#e74c3c',
      member_of: '#9b59b6',
      allies_with: '#2ecc71',
      enemies_with: '#e67e22',
      uses: '#f39c12',
      created_by: '#1abc9c',
      leads_to: '#34495e',
      participates_in: '#8e44ad',
      related_to: '#95a5a6',
      mentions: '#d35400'
    };
    return colorMap[link.relationship] || '#bdc3c7';
  };

  const loadGraphData = useCallback(async (nodesFile, edgesFile) => {
    setLoading(true);
    setError(null);
    
    try {
      // Load nodes
      const nodesResponse = await fetch(nodesFile);
      if (!nodesResponse.ok) throw new Error('Failed to load nodes file');
      const nodesData = await nodesResponse.json();
      
      // Load edges
      const edgesResponse = await fetch(edgesFile);
      if (!edgesResponse.ok) throw new Error('Failed to load edges file');
      const edgesData = await edgesResponse.json();
      
      // Transform nodes data (from object to array)
      const nodes = Object.values(nodesData).map(node => ({
        id: node.id,
        name: node.name,
        type: node.type,
        description: node.description,
        aliases: node.aliases,
        mention_count: node.mention_count,
        created_at: node.created_at,
        updated_at: node.updated_at,
        val: Math.max(node.mention_count * 2, 3) // Node size based on mention count
      }));
      
      // Transform edges data
      const links = edgesData.map(edge => ({
        source: edge.from_node_id,
        target: edge.to_node_id,
        relationship: edge.relationship,
        confidence: edge.confidence,
        evidence: edge.evidence,
        weight: edge.weight
      }));
      
      setGraphData({ nodes, links });
    } catch (err) {
      setError(err.message);
      console.error('Error loading graph data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFileUpload = (event, fileType) => {
    const file = event.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      if (fileType === 'nodes') {
        setNodesFile(url);
      } else {
        setEdgesFile(url);
      }
    }
  };

  const [nodesFile, setNodesFile] = useState(null);
  const [edgesFile, setEdgesFile] = useState(null);

  // Load sample data from the agent memories
  const loadSampleData = () => {
    // Load from the public sample-data directory
    loadGraphData('/sample-data/graph_nodes.json',
                   '/sample-data/graph_edges.json');
  };

  const handleNodeClick = useCallback(node => {
    setSelectedNode(node);
  }, []);

  const handleNodeRightClick = useCallback(node => {
    // Focus camera on node
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 1000);
      fgRef.current.zoom(8, 2000);
    }
  }, []);

  const resetView = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Memory Graph Viewer</h1>
        <div className="controls">
          <div className="file-controls">
            <div className="file-input-group">
              <label htmlFor="nodes-file">Nodes File:</label>
              <input
                id="nodes-file"
                type="file"
                accept=".json"
                onChange={(e) => handleFileUpload(e, 'nodes')}
              />
            </div>
            <div className="file-input-group">
              <label htmlFor="edges-file">Edges File:</label>
              <input
                id="edges-file"
                type="file"
                accept=".json"
                onChange={(e) => handleFileUpload(e, 'edges')}
              />
            </div>
            <button 
              onClick={() => nodesFile && edgesFile && loadGraphData(nodesFile, edgesFile)}
              disabled={!nodesFile || !edgesFile || loading}
            >
              Load Graph
            </button>
          </div>
          <div className="sample-controls">
            <button onClick={loadSampleData} disabled={loading}>
              Load Sample D&D Data
            </button>
            <button onClick={resetView} disabled={graphData.nodes.length === 0}>
              Reset View
            </button>
          </div>
        </div>
        
        {loading && <div className="loading">Loading graph data...</div>}
        {error && <div className="error">Error: {error}</div>}
        
        <div className="stats">
          Nodes: {graphData.nodes.length} | Links: {graphData.links.length}
        </div>
      </header>

      <main className="graph-container">
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          nodeLabel={node => `${node.name} (${node.type})`}
          nodeColor={getNodeColor}
          nodeVal={node => node.val}
          linkLabel={link => `${link.relationship} (confidence: ${link.confidence})`}
          linkColor={getLinkColor}
          linkWidth={link => Math.sqrt(link.weight) * 2}
          linkDirectionalArrowLength={6}
          linkDirectionalArrowRelPos={1}
          onNodeClick={handleNodeClick}
          onNodeRightClick={handleNodeRightClick}
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          width={window.innerWidth}
          height={window.innerHeight - 200}
        />
      </main>

      {selectedNode && (
        <div className="node-details">
          <h3>{selectedNode.name}</h3>
          <p><strong>Type:</strong> {selectedNode.type}</p>
          <p><strong>Description:</strong> {selectedNode.description}</p>
          {selectedNode.aliases && selectedNode.aliases.length > 0 && (
            <p><strong>Aliases:</strong> {selectedNode.aliases.join(', ')}</p>
          )}
          <p><strong>Mentions:</strong> {selectedNode.mention_count}</p>
          <p><strong>Created:</strong> {new Date(selectedNode.created_at).toLocaleString()}</p>
          <button onClick={() => setSelectedNode(null)}>Close</button>
        </div>
      )}

      <div className="legend">
        <h4>Entity Types</h4>
        <div className="legend-items">
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#ff6b6b'}}></div>
            <span>Character</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#4ecdc4'}}></div>
            <span>Location</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#45b7d1'}}></div>
            <span>Object</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#f7b731'}}></div>
            <span>Event</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#5f27cd'}}></div>
            <span>Concept</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#00d2d3'}}></div>
            <span>Organization</span>
          </div>
        </div>
        <p><em>Click nodes for details, right-click to focus</em></p>
      </div>
    </div>
  );
};

export default App;