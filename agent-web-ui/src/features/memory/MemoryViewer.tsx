import React, { useState, useEffect } from 'react'
import { useSessionStore } from '../../stores/sessionStore'
import apiClient from '../../services/api'
import type { MemoryDataResponse } from '../../types/api'

const MemoryViewer: React.FC = () => {
  const { currentSession } = useSessionStore()
  const [memoryData, setMemoryData] = useState<MemoryDataResponse | null>(null)
  const [memoryStats, setMemoryStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const fetchMemoryData = async () => {
    if (!currentSession) {
      setError('No session selected')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const [data, stats] = await Promise.all([
        apiClient.getMemoryData(currentSession.session_id),
        apiClient.getMemoryStats(currentSession.session_id).catch(() => null)
      ])
      setMemoryData(data)
      setMemoryStats(stats)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch memory data')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchMemoryData()
  }, [currentSession, refreshKey])

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1)
  }

  if (!currentSession) {
    return (
      <div className="p-6 text-center">
        <div className="text-gray-500">
          Please select a session to view memory data
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Memory Data</h1>
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

      {isLoading && !memoryData && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-gray-600">Loading memory data...</span>
        </div>
      )}

      {memoryData && (
        <div className="space-y-6">
          {/* Memory Statistics */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h2 className="text-lg font-semibold mb-2">Memory Statistics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Total Entries:</span>
                <div className="font-medium">{memoryData.total || 0}</div>
              </div>
              <div>
                <span className="text-gray-600">Data Items:</span>
                <div className="font-medium">{memoryData.data?.length || 0}</div>
              </div>
              <div>
                <span className="text-gray-600">Conversations:</span>
                <div className="font-medium">
                  {memoryStats?.conversations_count || 0}
                </div>
              </div>
              <div>
                <span className="text-gray-600">Memory Type:</span>
                <div className="font-medium">{memoryStats?.memory_type || 'N/A'}</div>
              </div>
            </div>
            {memoryStats?.has_graph_memory && (
              <div className="mt-2 text-sm text-blue-600">
                ✓ Graph Memory Enabled
              </div>
            )}
          </div>

          {/* Raw JSON Data */}
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
              <h2 className="text-lg font-semibold">Raw Memory JSON</h2>
            </div>
            <div className="p-4">
              <pre className="bg-gray-900 text-gray-100 p-4 rounded-md overflow-auto max-h-96 text-sm">
                {JSON.stringify(memoryData, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MemoryViewer 