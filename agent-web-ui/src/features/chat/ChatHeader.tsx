import React from 'react'
import { 
  WifiIcon, 
  SignalSlashIcon, 
  TrashIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline'
import type { SessionInfo } from '../../types/api'

interface ChatHeaderProps {
  session: SessionInfo
  isConnected: boolean
  onClearHistory: () => void
}

const ChatHeader: React.FC<ChatHeaderProps> = ({ 
  session, 
  isConnected, 
  onClearHistory 
}) => {
  const handleClearHistory = () => {
    if (confirm('Are you sure you want to clear the chat history? This cannot be undone.')) {
      onClearHistory()
    }
  }

  return (
    <div className="border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <WifiIcon className="h-5 w-5 text-green-500" />
            ) : (
              <SignalSlashIcon className="h-5 w-5 text-red-500" />
            )}
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Agent Chat
              </h2>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>
                  Session: {session.session_id.slice(0, 8)}...
                </span>
                <span>
                  Domain: {session.config.domain || 'Default'}
                </span>
                <span className={`flex items-center space-x-1 ${
                  isConnected ? 'text-green-600' : 'text-red-600'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${
                    isConnected ? 'bg-green-400' : 'bg-red-400'
                  }`}></div>
                  <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleClearHistory}
            className="p-2 text-gray-400 hover:text-red-600 rounded-md hover:bg-gray-50"
            title="Clear chat history"
          >
            <TrashIcon className="h-5 w-5" />
          </button>
          
          <div className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-50">
            <InformationCircleIcon className="h-5 w-5" />
          </div>
        </div>
      </div>
      
      {session.config.enable_graph && (
        <div className="mt-2 text-xs text-blue-600 bg-blue-50 rounded-md px-2 py-1 inline-block">
          Graph Memory Enabled
        </div>
      )}
    </div>
  )
}

export default ChatHeader 