import React, { useState, useCallback, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import './App.css';

const App = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [is3D, setIs3D] = useState(true);
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


  const handleNodeDragEnd = useCallback((node) => {
    // Pin the node at its final position (react-force-graph approach)
    node.fx = node.x;
    node.fy = node.y;
    node.fz = node.z;
  }, []);


  const resetView = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400);
    }
  };

  const unpinAllNodes = () => {
    if (fgRef.current) {
      const simulation = fgRef.current.d3Force();
      if (simulation) {
        const nodes = simulation.nodes();
        nodes.forEach(node => {
          delete node.fx;
          delete node.fy;
          delete node.fz;
        });
        simulation.alpha(0.1).restart(); // Gentle restart to reposition
      }
    }
  };

  // Render the appropriate graph component based on 2D/3D toggle
  const renderGraph = () => {
    const commonProps = {
      ref: fgRef,
      graphData: graphData,
      nodeLabel: "name",
      nodeVal: node => node.val,
      linkLabel: link => `${link.relationship} (confidence: ${link.confidence})`,
      linkWidth: link => Math.sqrt(link.weight || 1) * 2,
      linkDirectionalArrowLength: 4,
      linkDirectionalArrowRelPos: 1,
      onNodeClick: handleNodeClick,
      onNodeDragEnd: handleNodeDragEnd,
      d3Force: {
        charge: { strength: -10 },
        link: { 
          distance: 25,
          strength: 5
        },
        center: { strength: 5.0 },
        collision: {
          radius: node => Math.sqrt(node.val || 5) * 2.5,
          strength: 0.9
        }
      },
      width: window.innerWidth,
      height: window.innerHeight - 200
    };

    if (is3D) {
      return (
        <ForceGraph3D
          {...commonProps}
          nodeAutoColorBy="type"
          nodeThreeObject={node => {
            // Create a group to hold both sphere and text
            const group = new THREE.Group();
            
            // Create sphere for the node
            const nodeGeometry = new THREE.SphereGeometry(Math.sqrt(node.val || 5) * 2);
            const nodeMaterial = new THREE.MeshLambertMaterial({ 
              color: getNodeColor(node)
            });
            const sphere = new THREE.Mesh(nodeGeometry, nodeMaterial);
            group.add(sphere);
            
            // Create text sprite for always-visible label
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            const fontSize = 16;
            context.font = `${fontSize}px Arial`;
            context.fillStyle = '#333333';
            context.textAlign = 'center';
            
            const text = node.name || 'unnamed';
            const textWidth = context.measureText(text).width;
            canvas.width = textWidth + 10;
            canvas.height = fontSize + 4;
            
            context.font = `${fontSize}px Arial`;
            context.fillStyle = '#333333';
            context.textAlign = 'center';
            context.fillText(text, canvas.width / 2, fontSize);
            
            const texture = new THREE.CanvasTexture(canvas);
            const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
            const sprite = new THREE.Sprite(spriteMaterial);
            sprite.scale.set(canvas.width * 0.5, canvas.height * 0.5, 1);
            sprite.position.set(0, Math.sqrt(node.val || 5) * 3, 0);
            group.add(sprite);
            
            return group;
          }}
          showNavInfo={false}
        />
      );
    } else {
      return (
        <ForceGraph2D
          {...commonProps}
          nodeColor={getNodeColor}
          nodeCanvasObject={(node, ctx, globalScale) => {
            // Draw the node circle
            const label = node.name;
            const fontSize = 12/globalScale;
            const radius = Math.sqrt(node.val || 5) * 2;
            
            // Draw node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = getNodeColor(node);
            ctx.fill();
            
            // Draw node border
            ctx.strokeStyle = '#333';
            ctx.lineWidth = 1/globalScale;
            ctx.stroke();
            
            // Draw always-visible label
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#333';
            ctx.font = `${fontSize}px Arial`;
            
            // Position label below the node
            const labelY = node.y + radius + fontSize;
            ctx.fillText(label, node.x, labelY);
          }}
        />
      );
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
            <button onClick={unpinAllNodes} disabled={graphData.nodes.length === 0}>
              Unpin All Nodes
            </button>
            <button onClick={() => setIs3D(!is3D)}>
              Switch to {is3D ? '2D' : '3D'} View
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
        {renderGraph()}
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