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
  isLongOperation: boolean
  operationStartTime: number | null

  // Actions
  setSession: (sessionId: string) => Promise<void>
  sendMessage: (message: string, context?: Record<string, any>) => Promise<void>
  addMessage: (message: Omit<ChatMessage, 'id'>) => void
  clearHistory: () => void
  setTyping: (isTyping: boolean) => void
  setError: (error: string | null) => void
  setLongOperation: (isLong: boolean) => void
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
      isLongOperation: false,
      operationStartTime: null,

      // Actions
      setSession: async (sessionId: string) => {
        try {
          // Disconnect from previous session if any
          if (get().currentSessionId && get().currentSessionId !== sessionId) {
            wsService.disconnect()
          }
          
          // Clear only chat-related event handlers to prevent duplicates
          wsService.clearEventHandlers('query_response')
          wsService.clearEventHandlers('typing_start')
          wsService.clearEventHandlers('typing_end')
          wsService.clearEventHandlers('error')
          wsService.clearEventHandlers('connection_established')
          
          set({ 
            currentSessionId: sessionId,
            error: null,
            messages: [], // Clear messages when switching sessions
            isTyping: false
          })

          // Connect to WebSocket for this session
          await wsService.connect(sessionId)
          
          // Set up event handlers (these will be fresh handlers)
          wsService.on('query_response', (response: WebSocketResponse) => {
            get().setTyping(false)
            get().setLongOperation(false)
            get().addMessage({
              type: 'agent',
              content: response.data.message || response.data.response || '',
              timestamp: response.data.timestamp || new Date().toISOString(),
              session_id: sessionId
            })
          })

          wsService.on('typing_start', () => {
            const startTime = Date.now()
            // Only update operationStartTime if we're currently typing (to avoid race conditions)
            if (get().isTyping) {
              set({ 
                operationStartTime: startTime,
                isLongOperation: false
              })
            }
            
            // If typing continues for more than 10 seconds, consider it a long operation
            setTimeout(() => {
              if (get().isTyping && !get().isLongOperation) {
                get().setLongOperation(true)
              }
            }, 10000)
          })

          wsService.on('typing_end', () => {
            get().setTyping(false)
            get().setLongOperation(false)
          })

          wsService.on('error', (response: WebSocketResponse) => {
            get().setTyping(false)
            get().setError(response.data.message || response.data.error || 'An error occurred')
          })

          // Handle connection state changes
          wsService.on('connection_established', (response: WebSocketResponse) => {
            console.log('WebSocket connection established:', response.data)
            set({ isConnected: true, error: null })
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

        // Set typing indicator with immediate timer start as fallback
        const messageStartTime = Date.now()
        set({ 
          isTyping: true, 
          error: null,
          isLongOperation: false,
          operationStartTime: messageStartTime  // Start timer immediately, will be updated by typing_start if received
        })

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
        set({ 
          isTyping,
          // Reset operationStartTime when typing stops
          operationStartTime: isTyping ? get().operationStartTime : null
        })
      },

      setError: (error: string | null) => {
        set({ error })
      },

      setLongOperation: (isLong: boolean) => {
        set({ 
          isLongOperation: isLong,
          // Reset operationStartTime when long operation ends
          operationStartTime: isLong ? get().operationStartTime : null
        })
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