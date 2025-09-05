import React, { useEffect, useRef } from 'react'
import type { VerboseStatusMessage } from '../../types/api'

interface VerboseStatusDisplayProps {
  messages: VerboseStatusMessage[]
  isVisible: boolean
  onToggle: () => void
  maxHeight?: string
  className?: string
}

const VerboseStatusDisplay: React.FC<VerboseStatusDisplayProps> = ({
  messages,
  isVisible,
  onToggle,
  maxHeight = 'max-h-64',
  className = ''
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isVisible) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isVisible])

  const getStatusIcon = (messageType: string) => {
    switch (messageType) {
      case 'status':
        return '🔄'
      case 'success':
        return '✅'
      case 'warning':
        return '⚠️'
      case 'error':
        return '❌'
      default:
        return '📝'
    }
  }

  const getStatusColor = (messageType: string) => {
    switch (messageType) {
      case 'status':
        return 'text-blue-600'
      case 'success':
        return 'text-green-600'
      case 'warning':
        return 'text-amber-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const formatDuration = (duration?: number) => {
    if (duration === undefined || duration === null) return ''
    return ` (${duration.toFixed(2)}s)`
  }

  const formatMessage = (msg: VerboseStatusMessage) => {
    const indent = '  '.repeat(msg.level)
    const icon = getStatusIcon(msg.message_type)
    const duration = formatDuration(msg.duration)
    return `${icon} ${indent}${msg.message}${duration}`
  }

  if (!isVisible) {
    return (
      <div className={`bg-white/90 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200/50 ${className}`}>
        <div 
          className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50/50 transition-colors"
          onClick={onToggle}
        >
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700">Processing Status</span>
            {messages.length > 0 && (
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                {messages.length}
              </span>
            )}
          </div>
          <div className="text-gray-400 text-sm">
            Click to expand ▼
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white/90 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200/50 ${className}`}>
      <div 
        className="flex items-center justify-between p-3 border-b border-gray-200/50 cursor-pointer hover:bg-gray-50/50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-700">Processing Status</span>
          {messages.length > 0 && (
            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
              {messages.length}
            </span>
          )}
        </div>
        <div className="text-gray-400 text-sm">
          Click to collapse ▲
        </div>
      </div>
      
      <div className={`${maxHeight} overflow-y-auto`}>
        {messages.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            <div className="w-12 h-12 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
              <span className="text-xl">⏱️</span>
            </div>
            <div>No processing status messages yet</div>
            <div className="text-xs text-gray-400 mt-1">
              Status updates will appear here during operations
            </div>
          </div>
        ) : (
          <div className="p-3 space-y-1">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`font-mono text-xs leading-relaxed ${getStatusColor(msg.message_type)}`}
                style={{ whiteSpace: 'pre-wrap' }}
              >
                {formatMessage(msg)}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </div>
  )
}

export default VerboseStatusDisplay

