import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import wsService from '../services/websocket'
import type { VerboseStatusMessage, WebSocketResponse } from '../types/api'

interface VerboseStore {
  // State
  messages: VerboseStatusMessage[]
  isSubscribed: boolean
  isVisible: boolean
  currentSessionId: string | null

  // Actions
  setSession: (sessionId: string) => void
  subscribeToVerboseStatus: () => Promise<void>
  unsubscribeFromVerboseStatus: () => Promise<void>
  addMessage: (message: VerboseStatusMessage) => void
  clearMessages: () => void
  setVisible: (visible: boolean) => void
  disconnect: () => void
}

export const useVerboseStore = create<VerboseStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      messages: [],
      isSubscribed: false,
      isVisible: false,
      currentSessionId: null,

      // Actions
      setSession: (sessionId: string) => {
        // Clear messages when switching sessions
        set({ 
          currentSessionId: sessionId,
          messages: [],
          isSubscribed: false
        })
      },

      subscribeToVerboseStatus: async () => {
        try {
          if (!wsService.isConnected) {
            console.warn('Cannot subscribe to verbose status: WebSocket not connected')
            return
          }

          // Clear existing verbose-related event handlers to prevent duplicates
          wsService.clearEventHandlers('verbose_status')
          wsService.clearEventHandlers('verbose_subscribed')
          wsService.clearEventHandlers('verbose_unsubscribed')

          // Set up event handler for verbose status messages
          wsService.on('verbose_status', (response: WebSocketResponse) => {
            const message: VerboseStatusMessage = response.data
            get().addMessage(message)
          })

          // Set up subscription confirmation handler
          wsService.on('verbose_subscribed', (response: WebSocketResponse) => {
            console.log('Successfully subscribed to verbose status:', response.data)
            set({ isSubscribed: true })
          })

          // Set up unsubscription confirmation handler
          wsService.on('verbose_unsubscribed', (response: WebSocketResponse) => {
            console.log('Successfully unsubscribed from verbose status:', response.data)
            set({ isSubscribed: false })
          })

          // Send subscription request
          const success = wsService.subscribeToVerboseStatus()
          if (!success) {
            console.error('Failed to send verbose status subscription request')
          }
        } catch (error) {
          console.error('Error subscribing to verbose status:', error)
        }
      },

      unsubscribeFromVerboseStatus: async () => {
        try {
          if (wsService.isConnected) {
            wsService.unsubscribeFromVerboseStatus()
          }
          set({ isSubscribed: false })
        } catch (error) {
          console.error('Error unsubscribing from verbose status:', error)
        }
      },

      addMessage: (message: VerboseStatusMessage) => {
        set(state => ({
          messages: [...state.messages, message]
        }))
      },

      clearMessages: () => {
        set({ messages: [] })
      },

      setVisible: (visible: boolean) => {
        set({ isVisible: visible })
      },

      disconnect: () => {
        get().unsubscribeFromVerboseStatus()
        set({ 
          messages: [],
          isSubscribed: false,
          currentSessionId: null
        })
      }
    }),
    {
      name: 'verbose-store'
    }
  )
)

