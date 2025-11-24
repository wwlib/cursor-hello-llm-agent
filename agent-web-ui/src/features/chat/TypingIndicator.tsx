import React, { useState, useEffect } from 'react'
import { useChatStore } from '../../stores/chatStore'

const TypingIndicator: React.FC = () => {
  const { isLongOperation, operationStartTime } = useChatStore()
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!operationStartTime) {
      setElapsed(0)
      return
    }

    // Calculate initial elapsed time
    const initialElapsed = Math.floor((Date.now() - operationStartTime) / 1000)
    setElapsed(initialElapsed)

    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - operationStartTime) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [operationStartTime])

  const getMessage = () => {
    if (isLongOperation) {
      return elapsed > 0 
        ? `Processing complex operation... (${elapsed}s)`
        : 'Processing complex operation...'
    }
    return elapsed > 0 ? `Agent is thinking... (${elapsed}s)` : 'Agent is thinking...'
  }

  const getHelpText = () => {
    if (isLongOperation) {
      return 'This may take a while for complex operations like initial memory creation or entity resolution'
    }
    return null
  }

  return (
    <div className="flex justify-start">
      <div className={`rounded-lg px-4 py-2 max-w-3xl ${isLongOperation ? 'bg-blue-50 border border-blue-200' : 'bg-gray-100'}`}>
        <div className="flex items-center space-x-1">
          <span className={`text-sm ${isLongOperation ? 'text-blue-700' : 'text-gray-500'}`}>
            {getMessage()}
          </span>
          <div className="flex space-x-1">
            <div className={`w-1 h-1 rounded-full animate-bounce ${isLongOperation ? 'bg-blue-400' : 'bg-gray-400'}`}></div>
            <div className={`w-1 h-1 rounded-full animate-bounce ${isLongOperation ? 'bg-blue-400' : 'bg-gray-400'}`} style={{ animationDelay: '0.1s' }}></div>
            <div className={`w-1 h-1 rounded-full animate-bounce ${isLongOperation ? 'bg-blue-400' : 'bg-gray-400'}`} style={{ animationDelay: '0.2s' }}></div>
          </div>
        </div>
        {getHelpText() && (
          <div className="text-xs text-blue-600 mt-1 leading-relaxed">
            {getHelpText()}
          </div>
        )}
      </div>
    </div>
  )
}

export default TypingIndicator 