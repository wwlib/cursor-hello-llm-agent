import React, { useState, useEffect } from 'react'
import { useSessionStore } from '../../stores/sessionStore'
import apiClient from '../../services/api'
import type { GraphDataResponse } from '../../types/api'

const GraphViewer: React.FC = () => {
  const { currentSession } = useSessionStore()
  const [graphData, setGraphData] = useState<GraphDataResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const fetchGraphData = async () => {
    if (!currentSession) {
      setError('No session selected')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const data = await apiClient.getGraphData(currentSession.session_id)
      setGraphData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch graph data')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchGraphData()
  }, [currentSession, refreshKey])

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1)
  }

  if (!currentSession) {
    return (
      <div className="p-6 text-center">
        <div className="text-gray-500">
          Please select a session to view graph data
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Graph Data</h1>
          <p className="text-sm text-gray-600 mt-1">
            Session: {currentSession.session_id}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="text-red-700">
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {isLoading && !graphData && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-gray-600">Loading graph data...</span>
        </div>
      )}

      {graphData && (
        <div className="space-y-6">
          {/* Graph Statistics */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h2 className="text-lg font-semibold mb-2">Graph Statistics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Total Nodes:</span>
                <div className="font-medium">{graphData.nodes?.length || 0}</div>
              </div>
              <div>
                <span className="text-gray-600">Total Edges:</span>
                <div className="font-medium">{graphData.edges?.length || 0}</div>
              </div>
              <div>
                <span className="text-gray-600">Last Updated:</span>
                <div className="font-medium">
                  {graphData.metadata?.last_updated 
                    ? new Date(graphData.metadata.last_updated).toLocaleString()
                    : 'N/A'
                  }
                </div>
              </div>
              <div>
                <span className="text-gray-600">Graph Version:</span>
                <div className="font-medium">{graphData.metadata?.version || 'N/A'}</div>
              </div>
            </div>
          </div>

          {/* Nodes Summary */}
          {graphData.nodes && graphData.nodes.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
                <h2 className="text-lg font-semibold">Nodes Summary</h2>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {graphData.nodes.slice(0, 6).map((node, index) => (
                    <div key={node.id || index} className="bg-gray-50 p-3 rounded-md">
                      <div className="font-medium text-sm">{node.name || node.id}</div>
                      <div className="text-xs text-gray-600">{node.type}</div>
                      {node.description && (
                        <div className="text-xs text-gray-500 mt-1 line-clamp-2">
                          {node.description}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                {graphData.nodes.length > 6 && (
                  <div className="text-center mt-4 text-sm text-gray-500">
                    ... and {graphData.nodes.length - 6} more nodes
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Edges Summary */}
          {graphData.edges && graphData.edges.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
                <h2 className="text-lg font-semibold">Relationships Summary</h2>
              </div>
              <div className="p-4">
                <div className="space-y-2">
                  {graphData.edges.slice(0, 8).map((edge, index) => (
                    <div key={edge.id || index} className="bg-gray-50 p-3 rounded-md text-sm">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{edge.source}</span>
                        <span className="text-gray-500">→</span>
                        <span className="font-medium">{edge.target}</span>
                      </div>
                      <div className="text-xs text-gray-600 mt-1">{edge.type}</div>
                      {edge.description && (
                        <div className="text-xs text-gray-500 mt-1">{edge.description}</div>
                      )}
                    </div>
                  ))}
                </div>
                {graphData.edges.length > 8 && (
                  <div className="text-center mt-4 text-sm text-gray-500">
                    ... and {graphData.edges.length - 8} more relationships
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Raw JSON Data */}
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
              <h2 className="text-lg font-semibold">Raw Graph JSON</h2>
            </div>
            <div className="p-4">
              <pre className="bg-gray-900 text-gray-100 p-4 rounded-md overflow-auto max-h-96 text-sm">
                {JSON.stringify(graphData, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default GraphViewer 