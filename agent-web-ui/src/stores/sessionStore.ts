import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import apiClient from '../services/api'
import type { SessionInfo, SessionConfig, CreateSessionRequest } from '../types/api'

interface SessionStore {
  // State
  sessions: SessionInfo[]
  currentSession: SessionInfo | null
  isLoading: boolean
  error: string | null

  // Actions
  createSession: (config: SessionConfig, userId?: string) => Promise<SessionInfo>
  selectSession: (sessionId: string) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  refreshSessions: () => Promise<void>
  clearError: () => void
  cleanup: () => Promise<void>
}

export const useSessionStore = create<SessionStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      sessions: [],
      currentSession: null,
      isLoading: false,
      error: null,

      // Actions
      createSession: async (config: SessionConfig, userId?: string) => {
        set({ isLoading: true, error: null })
        
        try {
          const request: CreateSessionRequest = {
            config,
            user_id: userId
          }
          
          const response = await apiClient.createSession(request)
          const sessionInfo = await apiClient.getSession(response.session_id)
          
          set(state => ({
            sessions: [sessionInfo, ...state.sessions],
            currentSession: sessionInfo,
            isLoading: false
          }))
          
          return sessionInfo
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to create session'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      selectSession: async (sessionId: string) => {
        set({ isLoading: true, error: null })
        
        try {
          // Check if session is already in our list
          const existingSession = get().sessions.find(s => s.session_id === sessionId)
          
          if (existingSession) {
            set({ currentSession: existingSession, isLoading: false })
            return
          }
          
          // Fetch session info from API
          const sessionInfo = await apiClient.getSession(sessionId)
          
          set(state => ({
            sessions: [sessionInfo, ...state.sessions.filter(s => s.session_id !== sessionId)],
            currentSession: sessionInfo,
            isLoading: false
          }))
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to select session'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      deleteSession: async (sessionId: string) => {
        set({ isLoading: true, error: null })
        
        try {
          await apiClient.deleteSession(sessionId)
          
          set(state => ({
            sessions: state.sessions.filter(s => s.session_id !== sessionId),
            currentSession: state.currentSession?.session_id === sessionId ? null : state.currentSession,
            isLoading: false
          }))
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to delete session'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      refreshSessions: async () => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await apiClient.listSessions()
          
          set(state => ({
            sessions: response.sessions,
            // Update current session if it exists in the new list
            currentSession: state.currentSession 
              ? response.sessions.find(s => s.session_id === state.currentSession!.session_id) || null
              : null,
            isLoading: false
          }))
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to refresh sessions'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      cleanup: async () => {
        try {
          await apiClient.cleanupSessions()
          await get().refreshSessions()
        } catch (error) {
          console.error('Failed to cleanup sessions:', error)
        }
      },

      clearError: () => {
        set({ error: null })
      }
    }),
    {
      name: 'session-store'
    }
  )
) 