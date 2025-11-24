import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { LogEntry } from '../types/api'
import wsService from '../services/websocket'

interface LogStore {
  // State
  logs: LogEntry[]
  availableLogSources: string[]
  subscribedLogSources: string[]
  isSubscribed: boolean
  maxLogEntries: number
  logLevels: ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')[]
  filteredLogLevels: ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')[]
  
  // Actions
  setAvailableLogSources: (sources: string[]) => void
  setSubscribedLogSources: (sources: string[]) => void
  addLogEntry: (log: LogEntry) => void
  clearLogs: () => void
  setMaxLogEntries: (max: number) => void
  setFilteredLogLevels: (levels: ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')[]) => void
  
  // WebSocket actions
  initializeLogStreaming: () => void
  subscribeToLogs: (sources: string[]) => void
  unsubscribeFromLogs: (sources?: string[]) => void
  cleanup: () => void
}

export const useLogStore = create<LogStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      logs: [],
      availableLogSources: [],
      subscribedLogSources: [],
      isSubscribed: false,
      maxLogEntries: 1000,
      logLevels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
      filteredLogLevels: ['INFO', 'WARNING', 'ERROR', 'CRITICAL'],
      
      // Actions
      setAvailableLogSources: (sources) => 
        set({ availableLogSources: sources }, false, 'setAvailableLogSources'),
      
      setSubscribedLogSources: (sources) => 
        set({ 
          subscribedLogSources: sources,
          isSubscribed: sources.length > 0
        }, false, 'setSubscribedLogSources'),
      
      addLogEntry: (log) => 
        set((state) => {
          // Only add if log level is in filtered levels
          if (!state.filteredLogLevels.includes(log.level)) {
            return state
          }
          
          const newLogs = [...state.logs, log]
          
          // Keep only the last maxLogEntries
          if (newLogs.length > state.maxLogEntries) {
            return { logs: newLogs.slice(-state.maxLogEntries) }
          }
          
          return { logs: newLogs }
        }, false, 'addLogEntry'),
      
      clearLogs: () => 
        set({ logs: [] }, false, 'clearLogs'),
      
      setMaxLogEntries: (max) => 
        set((state) => ({
          maxLogEntries: max,
          logs: state.logs.slice(-max)
        }), false, 'setMaxLogEntries'),
      
      setFilteredLogLevels: (levels) => 
        set({ filteredLogLevels: levels }, false, 'setFilteredLogLevels'),
      
      // WebSocket actions
      initializeLogStreaming: () => {
        // Clear existing log-related event handlers to prevent duplicates
        wsService.clearEventHandlers('log_sources_response')
        wsService.clearEventHandlers('logs_subscribed')
        wsService.clearEventHandlers('logs_unsubscribed')
        wsService.clearEventHandlers('log_stream')
        
        // Set up WebSocket event listeners
        wsService.on('log_sources_response', (response) => {
          const { available_sources } = response.data
          get().setAvailableLogSources(available_sources)
        })
        
        wsService.on('logs_subscribed', (response) => {
          const { subscribed_sources } = response.data
          if (subscribed_sources) {
            get().setSubscribedLogSources(subscribed_sources)
          }
        })
        
        wsService.on('logs_unsubscribed', (response) => {
          const { unsubscribed_sources } = response.data
          if (unsubscribed_sources) {
            const currentSources = get().subscribedLogSources
            const remainingSources = currentSources.filter(
              source => !unsubscribed_sources.includes(source)
            )
            get().setSubscribedLogSources(remainingSources)
          }
        })
        
        wsService.on('log_stream', (response) => {
          get().addLogEntry(response.data)
        })
        
        wsService.on('connection_established', (response) => {
          // Request available log sources after connection is established
          setTimeout(() => {
            wsService.getLogSources()
          }, 100) // Small delay to ensure connection is fully ready
        })
        
        // Request available log sources immediately if already connected
        if (wsService.isConnected) {
          wsService.getLogSources()
        }
      },
      
      subscribeToLogs: (sources) => {
        wsService.subscribeToLogs(sources)
      },
      
      unsubscribeFromLogs: (sources) => {
        wsService.unsubscribeFromLogs(sources)
      },
      
      cleanup: () => {
        const { subscribedLogSources } = get()
        if (subscribedLogSources.length > 0) {
          wsService.unsubscribeFromLogs()
        }
        set({
          logs: [],
          subscribedLogSources: [],
          isSubscribed: false
        }, false, 'cleanup')
      }
    }),
    {
      name: 'log-store',
    }
  )
) 