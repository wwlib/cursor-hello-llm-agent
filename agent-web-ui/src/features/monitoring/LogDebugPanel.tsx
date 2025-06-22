import React from 'react'
import { useLogStore } from '../../stores/logStore'
import { useSessionStore } from '../../stores/sessionStore'
import wsService from '../../services/websocket'

const LogDebugPanel: React.FC = () => {
  const { currentSession } = useSessionStore()
  const {
    availableLogSources,
    subscribedLogSources,
    isSubscribed,
    logs,
    subscribeToLogs,
    initializeLogStreaming
  } = useLogStore()

  const handleTestConnection = () => {
    console.log('🔍 DEBUG: Testing WebSocket connection...')
    console.log('🔍 DEBUG: WebSocket state:', {
      isConnected: wsService.isConnected,
      connectionState: wsService.connectionState,
      subscribedLogSources: wsService.getSubscribedLogSources()
    })
    
    // Test getting log sources
    wsService.getLogSources()
  }

  const handleForceSubscribe = () => {
    console.log('🔍 DEBUG: Force subscribing to available sources...')
    if (availableLogSources.length > 0) {
      subscribeToLogs(availableLogSources)
    } else {
      console.log('🔍 DEBUG: No available sources to subscribe to')
    }
  }

  const handleReinitialize = () => {
    console.log('🔍 DEBUG: Reinitializing log streaming...')
    initializeLogStreaming()
  }

  if (!currentSession) {
    return null
  }

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
      <h3 className="text-sm font-semibold text-yellow-800 mb-2">🔍 Log Streaming Debug</h3>
      
      <div className="space-y-2 text-xs">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <strong>WebSocket:</strong> {wsService.isConnected ? '✅ Connected' : '❌ Disconnected'}
          </div>
          <div>
            <strong>Log Streaming:</strong> {isSubscribed ? '✅ Active' : '❌ Inactive'}
          </div>
        </div>
        
        <div>
          <strong>Available Sources:</strong> [{availableLogSources.join(', ') || 'None'}]
        </div>
        
        <div>
          <strong>Subscribed Sources:</strong> [{subscribedLogSources.join(', ') || 'None'}]
        </div>
        
        <div>
          <strong>Log Count:</strong> {logs.length} entries
        </div>
        
        <div className="flex space-x-2 mt-3">
          <button
            onClick={handleTestConnection}
            className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs hover:bg-blue-200"
          >
            Test Connection
          </button>
          <button
            onClick={handleForceSubscribe}
            className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs hover:bg-green-200"
          >
            Force Subscribe
          </button>
          <button
            onClick={handleReinitialize}
            className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs hover:bg-purple-200"
          >
            Reinitialize
          </button>
        </div>
      </div>
    </div>
  )
}

export default LogDebugPanel 