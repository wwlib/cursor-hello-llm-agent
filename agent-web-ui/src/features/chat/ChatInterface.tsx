import React, { useEffect, useRef } from 'react'
import { useSessionStore } from '../../stores/sessionStore'
import { useChatStore } from '../../stores/chatStore'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import TypingIndicator from './TypingIndicator'
import ChatHeader from './ChatHeader'
import LogPanel from '../monitoring/LogPanel'

const ChatInterface: React.FC = () => {
  const { currentSession } = useSessionStore()
  const { 
    messages, 
    isTyping, 
    isConnected, 
    error, 
    sendMessage, 
    setSession, 
    clearHistory,
    setError
  } = useChatStore()

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Connect to session when current session changes
  useEffect(() => {
    if (currentSession?.session_id) {
      setSession(currentSession.session_id)
    }
  }, [currentSession?.session_id, setSession])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return
    
    try {
      await sendMessage(message)
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }

  if (!currentSession) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50">
          <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center">
            <span className="text-2xl">🤖</span>
          </div>
          <div className="text-gray-700 text-xl font-semibold mb-2">No Session Selected</div>
          <div className="text-gray-500 text-sm max-w-sm">
            Please select or create a session to start chatting with your intelligent agent.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 overflow-hidden">
        <ChatHeader 
          session={currentSession} 
          isConnected={isConnected}
          onClearHistory={clearHistory}
        />
        
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-16">
                <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-full flex items-center justify-center border border-blue-100">
                  <span className="text-3xl">👋</span>
                </div>
                <div className="text-xl font-semibold mb-3 text-gray-700">Welcome!</div>
                <div className="text-sm text-gray-500 max-w-md mx-auto leading-relaxed">
                  Start a conversation with your agent. Try asking about your <span className="font-medium text-blue-600">{currentSession.config.domain}</span> campaign!
                </div>
              </div>
            ) : (
              <MessageList messages={messages} />
            )}
            
            {isTyping && <TypingIndicator />}
            
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-red-500">⚠️</span>
                    <div className="text-sm text-red-800 font-medium">{error}</div>
                  </div>
                  <button
                    onClick={() => setError(null)}
                    className="text-red-400 hover:text-red-600 transition-colors p-1 hover:bg-red-100 rounded-lg"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          <div className="border-t border-gray-200/50 p-6 bg-gradient-to-r from-gray-50/50 to-blue-50/30">
            <MessageInput 
              onSend={handleSendMessage} 
              disabled={isTyping || !isConnected}
              placeholder={
                isConnected 
                  ? "Type your message..." 
                  : "Connecting to session..."
              }
            />
          </div>
        </div>
      </div>

      {/* Log Panel */}
      <LogPanel className="flex-shrink-0" maxHeight="max-h-64" />
    </div>
  )
}

export default ChatInterface 