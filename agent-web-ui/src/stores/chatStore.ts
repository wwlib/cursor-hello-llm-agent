import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { v4 as uuidv4 } from 'uuid'
import wsService from '../services/websocket'
import apiClient from '../services/api'
import type { ChatMessage, WebSocketResponse } from '../types/api'

interface ChatStore {
  // State
  messages: ChatMessage[]
  isTyping: boolean
  isConnected: boolean
  error: string | null
  currentSessionId: string | null

  // Actions
  setSession: (sessionId: string) => Promise<void>
  sendMessage: (message: string, context?: Record<string, any>) => Promise<void>
  addMessage: (message: Omit<ChatMessage, 'id'>) => void
  clearHistory: () => void
  setTyping: (isTyping: boolean) => void
  setError: (error: string | null) => void
  disconnect: () => void
}

export const useChatStore = create<ChatStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      messages: [],
      isTyping: false,
      isConnected: false,
      error: null,
      currentSessionId: null,

      // Actions
      setSession: async (sessionId: string) => {
        try {
          // Disconnect from previous session if any
          if (get().currentSessionId && get().currentSessionId !== sessionId) {
            wsService.disconnect()
          }
          
          set({ 
            currentSessionId: sessionId,
            error: null,
            messages: [], // Clear messages when switching sessions
            isTyping: false
          })

          // Connect to WebSocket for this session
          await wsService.connect(sessionId)
          
          // Set up event handlers
          wsService.on('query_response', (response: WebSocketResponse) => {
            get().setTyping(false)
            get().addMessage({
              type: 'agent',
              content: response.data.message || response.data.response || '',
              timestamp: response.data.timestamp || new Date().toISOString(),
              session_id: sessionId
            })
          })

          wsService.on('typing_start', () => {
            get().setTyping(true)
          })

          wsService.on('typing_end', () => {
            get().setTyping(false)
          })

          wsService.on('error', (response: WebSocketResponse) => {
            get().setTyping(false)
            get().setError(response.data.message || 'An error occurred')
          })

          set({ isConnected: true })
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to connect to session'
          set({ error: errorMessage, isConnected: false })
          throw error
        }
      },

      sendMessage: async (message: string, context?: Record<string, any>) => {
        const { currentSessionId } = get()
        
        if (!currentSessionId) {
          set({ error: 'No active session' })
          return
        }

        // Add user message to chat
        get().addMessage({
          type: 'user',
          content: message,
          timestamp: new Date().toISOString(),
          session_id: currentSessionId
        })

        // Set typing indicator
        set({ isTyping: true, error: null })

        try {
          if (wsService.isConnected) {
            // Send via WebSocket for real-time response
            wsService.queryAgent(message, context)
          } else {
            // Fallback to REST API
            const response = await apiClient.queryAgent(currentSessionId, {
              message,
              context
            })

            get().setTyping(false)
            get().addMessage({
              type: 'agent',
              content: response.response,
              timestamp: response.timestamp,
              session_id: currentSessionId
            })
          }
        } catch (error) {
          get().setTyping(false)
          const errorMessage = error instanceof Error ? error.message : 'Failed to send message'
          set({ error: errorMessage })
          
          // Add error message to chat
          get().addMessage({
            type: 'system',
            content: `Error: ${errorMessage}`,
            timestamp: new Date().toISOString(),
            session_id: currentSessionId
          })
        }
      },

      addMessage: (message: Omit<ChatMessage, 'id'>) => {
        const newMessage: ChatMessage = {
          ...message,
          id: uuidv4()
        }
        
        set(state => ({
          messages: [...state.messages, newMessage]
        }))
      },

      clearHistory: () => {
        set({ messages: [] })
      },

      setTyping: (isTyping: boolean) => {
        set({ isTyping })
      },

      setError: (error: string | null) => {
        set({ error })
      },

      disconnect: () => {
        wsService.disconnect()
        set({ 
          isConnected: false,
          currentSessionId: null,
          isTyping: false 
        })
      }
    }),
    {
      name: 'chat-store'
    }
  )
) 