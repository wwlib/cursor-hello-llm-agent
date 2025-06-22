import React, { useEffect, useRef } from 'react'
import { useSessionStore } from '../../stores/sessionStore'
import { useChatStore } from '../../stores/chatStore'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import TypingIndicator from './TypingIndicator'
import ChatHeader from './ChatHeader'

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
        <div className="text-center">
          <div className="text-gray-500 text-lg mb-4">No Session Selected</div>
          <div className="text-gray-400 text-sm">
            Please select or create a session to start chatting with the agent.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border border-gray-200">
      <ChatHeader 
        session={currentSession} 
        isConnected={isConnected}
        onClearHistory={clearHistory}
      />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <div className="text-lg mb-2">👋 Welcome!</div>
              <div className="text-sm">
                Start a conversation with your agent. Try asking about your {currentSession.config.domain} campaign!
              </div>
            </div>
          ) : (
            <MessageList messages={messages} />
          )}
          
          {isTyping && <TypingIndicator />}
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <div className="flex items-center justify-between">
                <div className="text-sm text-red-800">{error}</div>
                <button
                  onClick={() => setError(null)}
                  className="text-red-400 hover:text-red-600"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        <div className="border-t border-gray-200 p-4">
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
  )
}

export default ChatInterface 