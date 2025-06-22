import React, { useEffect, useRef, useState } from 'react'
import { useLogStore } from '../../stores/logStore'
import { useSessionStore } from '../../stores/sessionStore'
import type { LogEntry } from '../../types/api'

interface LogLevelConfig {
  color: string
  bgColor: string
  icon: string
}

const LOG_LEVEL_CONFIG: Record<string, LogLevelConfig> = {
  DEBUG: { color: 'text-gray-600', bgColor: 'bg-gray-100', icon: '🔍' },
  INFO: { color: 'text-blue-600', bgColor: 'bg-blue-50', icon: 'ℹ️' },
  WARNING: { color: 'text-yellow-600', bgColor: 'bg-yellow-50', icon: '⚠️' },
  ERROR: { color: 'text-red-600', bgColor: 'bg-red-50', icon: '❌' },
  CRITICAL: { color: 'text-red-800', bgColor: 'bg-red-100', icon: '🚨' }
}

interface LogTab {
  id: string
  name: string
  sources: string[]
  icon: string
  description: string
}

const LOG_TABS: LogTab[] = [
  {
    id: 'agent',
    name: 'Agent',
    sources: ['agent'],
    icon: '🤖',
    description: 'Agent reasoning and decision making'
  },
  {
    id: 'llm',
    name: 'LLM/AI',
    sources: ['ollama_general', 'ollama_digest', 'ollama_embed'],
    icon: '🧠',
    description: 'AI model interactions and processing'
  },
  {
    id: 'memory',
    name: 'Memory',
    sources: ['memory_manager'],
    icon: '💾',
    description: 'Memory storage and retrieval'
  },
  {
    id: 'api',
    name: 'API',
    sources: ['api'],
    icon: '🌐',
    description: 'API requests and responses'
  },
  {
    id: 'all',
    name: 'All',
    sources: [],
    icon: '📋',
    description: 'All log entries'
  }
]

const LogViewer: React.FC = () => {
  const { currentSession } = useSessionStore()
  const {
    logs,
    availableLogSources,
    subscribedLogSources,
    isSubscribed,
    filteredLogLevels,
    logLevels,
    initializeLogStreaming,
    subscribeToLogs,
    unsubscribeFromLogs,
    clearLogs,
    setFilteredLogLevels,
    cleanup
  } = useLogStore()

  const [activeTab, setActiveTab] = useState('llm') // Start with LLM tab
  const [autoScroll, setAutoScroll] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const logsEndRef = useRef<HTMLDivElement>(null)
  const logsContainerRef = useRef<HTMLDivElement>(null)

  // Initialize log streaming when component mounts
  useEffect(() => {
    if (currentSession) {
      initializeLogStreaming()
    }
    
    return () => {
      cleanup()
    }
  }, [currentSession, initializeLogStreaming, cleanup])

  // Auto-subscribe to all available sources when they become available
  useEffect(() => {
    if (availableLogSources.length > 0 && subscribedLogSources.length === 0) {
      console.log('🔍 LOG_VIEWER: Auto-subscribing to all available sources:', availableLogSources)
      subscribeToLogs(availableLogSources)
    }
  }, [availableLogSources, subscribedLogSources, subscribeToLogs])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  // Handle scroll to detect if user scrolled up (disable auto-scroll)
  const handleScroll = () => {
    if (!logsContainerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current
    const isAtBottom = scrollHeight - scrollTop <= clientHeight + 100
    
    if (!isAtBottom && autoScroll) {
      setAutoScroll(false)
    } else if (isAtBottom && !autoScroll) {
      setAutoScroll(true)
    }
  }

  const handleLevelToggle = (level: typeof logLevels[0]) => {
    const newLevels = filteredLogLevels.includes(level)
      ? filteredLogLevels.filter(l => l !== level)
      : [...filteredLogLevels, level]
    
    setFilteredLogLevels(newLevels)
  }

  // Get logs for the active tab
  const getTabLogs = (tabId: string): LogEntry[] => {
    const tab = LOG_TABS.find(t => t.id === tabId)
    if (!tab) return []

    let tabLogs = logs
    
    // Filter by tab sources (unless it's "all" tab)
    if (tab.sources.length > 0) {
      tabLogs = logs.filter(log => tab.sources.includes(log.source))
    }

    // Apply search filter
    if (searchTerm) {
      tabLogs = tabLogs.filter(log => 
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.logger.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.module.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    return tabLogs
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const timeString = date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit'
    })
    const milliseconds = date.getMilliseconds().toString().padStart(3, '0')
    return `${timeString}.${milliseconds}`
  }

  const activeTabLogs = getTabLogs(activeTab)

  if (!currentSession) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-gray-500 text-lg mb-4">No Session Selected</div>
          <div className="text-gray-400 text-sm">
            Please select a session to view logs.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header Controls */}
      <div className="border-b border-gray-200 p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">System Logs</h2>
          <div className="flex items-center space-x-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              isSubscribed 
                ? 'bg-green-100 text-green-800' 
                : 'bg-gray-100 text-gray-800'
            }`}>
              {isSubscribed ? 'Streaming' : 'Not Connected'}
            </span>
            <button
              onClick={clearLogs}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md text-gray-700 transition-colors"
            >
              Clear Logs
            </button>
          </div>
        </div>

        {/* Search and Controls */}
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Auto-scroll</span>
          </label>
        </div>

        {/* Log Levels */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Log Levels:</label>
          <div className="flex flex-wrap gap-2">
            {logLevels.map((level) => {
              const config = LOG_LEVEL_CONFIG[level]
              const isActive = filteredLogLevels.includes(level)
              return (
                <button
                  key={level}
                  onClick={() => handleLevelToggle(level)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors flex items-center space-x-1 ${
                    isActive
                      ? `${config.bgColor} ${config.color} border`
                      : 'bg-gray-100 text-gray-400 border border-gray-300 hover:bg-gray-200'
                  }`}
                >
                  <span>{config.icon}</span>
                  <span>{level}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 px-4" aria-label="Tabs">
          {LOG_TABS.map((tab) => {
            const tabLogCount = getTabLogs(tab.id).length
            const isActive = activeTab === tab.id
            
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  isActive
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <span className="text-base">{tab.icon}</span>
                <span>{tab.name}</span>
                {tabLogCount > 0 && (
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    isActive 
                      ? 'bg-blue-100 text-blue-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {tabLogCount}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tab Description */}
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
          <p className="text-sm text-gray-600">
            {LOG_TABS.find(t => t.id === activeTab)?.description}
          </p>
        </div>

        {/* Logs Display */}
        <div 
          ref={logsContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto bg-gray-50"
        >
          {activeTabLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-gray-500 text-lg mb-2">No Logs</div>
                <div className="text-gray-400 text-sm">
                  {subscribedLogSources.length === 0 
                    ? 'Waiting for log sources to be available...'
                    : `No ${LOG_TABS.find(t => t.id === activeTab)?.name.toLowerCase()} logs match your current filters.`
                  }
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 space-y-1">
              {activeTabLogs.map((log, index) => {
                const config = LOG_LEVEL_CONFIG[log.level] || LOG_LEVEL_CONFIG.INFO
                return (
                  <LogEntryRow 
                    key={`${log.timestamp}-${index}`} 
                    log={log}
                    config={config}
                    formatTimestamp={formatTimestamp}
                  />
                )
              })}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Footer Stats */}
      <div className="border-t border-gray-200 px-4 py-2 bg-gray-50">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Showing {activeTabLogs.length} {LOG_TABS.find(t => t.id === activeTab)?.name.toLowerCase()} logs of {logs.length} total
          </span>
          <span>
            Sources: {subscribedLogSources.join(', ') || 'None'}
          </span>
        </div>
      </div>
    </div>
  )
}

interface LogEntryRowProps {
  log: LogEntry
  config: LogLevelConfig
  formatTimestamp: (timestamp: string) => string
}

const LogEntryRow: React.FC<LogEntryRowProps> = ({ log, config, formatTimestamp }) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={`border rounded-md p-3 ${config.bgColor} border-gray-200 hover:shadow-sm transition-shadow`}>
      <div 
        className="flex items-start space-x-3 cursor-pointer" 
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-lg flex-shrink-0">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 text-sm">
            <span className="font-mono text-gray-500">
              {formatTimestamp(log.timestamp)}
            </span>
            <span className={`font-medium ${config.color}`}>
              {log.level}
            </span>
            <span className="text-gray-600 font-medium">
              {log.source}
            </span>
            <span className="text-gray-500 text-xs">
              {log.logger}
            </span>
          </div>
          <div className="mt-1">
            <p className={`text-sm ${expanded ? '' : 'truncate'} ${config.color}`}>
              {log.message}
            </p>
          </div>
          {expanded && (
            <div className="mt-2 text-xs text-gray-500 bg-white bg-opacity-50 rounded p-2">
              <div><strong>Module:</strong> {log.module}</div>
              <div><strong>Function:</strong> {log.function}</div>
              <div><strong>Line:</strong> {log.line}</div>
              <div><strong>Source:</strong> {log.source}</div>
            </div>
          )}
        </div>
        <button className="text-gray-400 hover:text-gray-600 flex-shrink-0">
          {expanded ? '▲' : '▼'}
        </button>
      </div>
    </div>
  )
}

export default LogViewer 