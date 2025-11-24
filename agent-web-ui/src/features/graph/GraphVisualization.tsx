import React, { useCallback, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { GraphDataResponse } from '../../types/api'

interface GraphVisualizationProps {
  graphData: GraphDataResponse
  height?: number
}

interface GraphNode {
  id: string
  name: string
  type: string
  description?: string
  val?: number
  x?: number
  y?: number
  fx?: number
  fy?: number
}

interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  relationship?: string
  type?: string
  description?: string
  confidence?: number
  weight?: number
}

const GraphVisualization: React.FC<GraphVisualizationProps> = ({ 
  graphData, 
  height = 600 
}) => {
  const fgRef = useRef<{ zoomToFit: (duration?: number) => void; d3Force: (forceName?: string) => any }>()
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  // Color mapping for different entity types
  const getNodeColor = (node: GraphNode): string => {
    const colorMap: Record<string, string> = {
      character: '#ff6b6b',
      location: '#4ecdc4',
      object: '#45b7d1',
      event: '#f7b731',
      concept: '#5f27cd',
      organization: '#00d2d3',
      person: '#ff6b6b',
      place: '#4ecdc4',
      thing: '#45b7d1'
    }
    return colorMap[node.type?.toLowerCase()] || '#95a5a6'
  }

  // Transform API data to graph format
  const transformGraphData = useCallback(() => {
    if (!graphData.nodes || !graphData.edges) {
      return { nodes: [], links: [] }
    }

    // Transform nodes
    const nodes: GraphNode[] = graphData.nodes.map(node => ({
      id: node.id,
      name: node.name || node.id,
      type: node.type || 'unknown',
      description: node.description,
      val: 5 // Default size, can be adjusted based on metadata
    }))

    // Transform edges to links
    const links: GraphLink[] = graphData.edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      relationship: edge.type || edge.description,
      type: edge.type,
      description: edge.description,
      confidence: edge.metadata?.confidence || 1.0,
      weight: edge.metadata?.weight || 1.0
    }))

    return { nodes, links }
  }, [graphData])

  const graphDataTransformed = transformGraphData()

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node)
  }, [])

  const handleNodeDragEnd = useCallback((node: GraphNode) => {
    // Pin the node at its final position
    node.fx = node.x
    node.fy = node.y
  }, [])

  const resetView = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400)
    }
  }, [])

  const unpinAllNodes = useCallback(() => {
    if (fgRef.current) {
      const simulation = fgRef.current.d3Force()
      if (simulation) {
        const nodes = simulation.nodes() as GraphNode[]
        nodes.forEach(node => {
          delete node.fx
          delete node.fy
        })
        simulation.alpha(0.1).restart()
      }
    }
  }, [])

  if (!graphDataTransformed.nodes.length) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-center text-gray-500">
          <p className="text-lg mb-2">No graph data available</p>
          <p className="text-sm">Graph data will appear here when available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative w-full bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
      {/* Controls */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={resetView}
          className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm"
          title="Reset view to fit all nodes"
        >
          Reset View
        </button>
        <button
          onClick={unpinAllNodes}
          className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm"
          title="Unpin all nodes"
        >
          Unpin All
        </button>
      </div>

      {/* Graph Visualization */}
      <div style={{ height: `${height}px`, width: '100%' }}>
        <ForceGraph2D
          ref={fgRef}
          graphData={graphDataTransformed}
          nodeLabel={(node: GraphNode) => `${node.name} (${node.type})`}
          nodeVal={(node: GraphNode) => node.val || 5}
          nodeColor={getNodeColor}
          linkLabel={(link: GraphLink) => 
            `${link.relationship || link.type || 'related'}${link.confidence ? ` (${(link.confidence * 100).toFixed(0)}%)` : ''}`
          }
          linkWidth={(link: GraphLink) => Math.sqrt(link.weight || 1) * 2}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          onNodeClick={handleNodeClick}
          onNodeDragEnd={handleNodeDragEnd}
          d3Force={{
            charge: { strength: -300 },
            link: { 
              distance: 50,
              strength: 0.5
            },
            center: { strength: 0.1 },
            collision: {
              radius: (node: GraphNode) => Math.sqrt(node.val || 5) * 2.5,
              strength: 0.9
            }
          }}
          width={typeof window !== 'undefined' ? window.innerWidth - 100 : 800}
          height={height}
          nodeCanvasObject={(node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
            // Draw the node circle
            const label = node.name || node.id
            const fontSize = 12 / globalScale
            const radius = Math.sqrt(node.val || 5) * 2
            
            // Draw node circle
            ctx.beginPath()
            ctx.arc(node.x!, node.y!, radius, 0, 2 * Math.PI, false)
            ctx.fillStyle = getNodeColor(node)
            ctx.fill()
            
            // Draw node border
            ctx.strokeStyle = '#333'
            ctx.lineWidth = 1 / globalScale
            ctx.stroke()
            
            // Draw always-visible label
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillStyle = '#333'
            ctx.font = `${fontSize}px Arial`
            
            // Position label below the node
            const labelY = node.y! + radius + fontSize
            ctx.fillText(label, node.x!, labelY)
          }}
        />
      </div>

      {/* Node Details Modal */}
      {selectedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-xl font-bold text-gray-900">{selectedNode.name}</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-semibold text-gray-700">Type:</span>{' '}
                <span className="text-gray-600">{selectedNode.type}</span>
              </div>
              {selectedNode.description && (
                <div>
                  <span className="font-semibold text-gray-700">Description:</span>
                  <p className="text-gray-600 mt-1">{selectedNode.description}</p>
                </div>
              )}
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white bg-opacity-95 border border-gray-300 rounded-lg p-3 shadow-lg z-10">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Entity Types</h4>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ff6b6b] border border-gray-300"></div>
            <span className="text-gray-600">Character/Person</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#4ecdc4] border border-gray-300"></div>
            <span className="text-gray-600">Location/Place</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#45b7d1] border border-gray-300"></div>
            <span className="text-gray-600">Object/Thing</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#f7b731] border border-gray-300"></div>
            <span className="text-gray-600">Event</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#5f27cd] border border-gray-300"></div>
            <span className="text-gray-600">Concept</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#00d2d3] border border-gray-300"></div>
            <span className="text-gray-600">Organization</span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2 italic">Click nodes for details</p>
      </div>
    </div>
  )
}

export default GraphVisualization

