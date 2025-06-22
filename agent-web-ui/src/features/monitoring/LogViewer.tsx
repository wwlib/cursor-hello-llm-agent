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
    <div className="h-full flex flex-col bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 overflow-hidden">
      {/* Header Controls */}
      <div className="border-b border-gray-200/50 p-6 space-y-6 bg-gradient-to-r from-white to-blue-50/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm">📊</span>
            </div>
            <h2 className="text-xl font-bold text-gray-900">System Logs</h2>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`px-3 py-1.5 rounded-full text-xs font-semibold ${
              isSubscribed 
                ? 'bg-green-100 text-green-800 border border-green-200' 
                : 'bg-gray-100 text-gray-800 border border-gray-200'
            }`}>
              {isSubscribed ? '🟢 Streaming' : '⚫ Not Connected'}
            </span>
            <button
              onClick={clearLogs}
              className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition-all duration-200 hover:scale-105 border border-gray-200"
            >
              🗑️ Clear Logs
            </button>
          </div>
        </div>

        {/* Search and Controls */}
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-400">🔍</span>
              </div>
              <input
                type="text"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white/80 backdrop-blur-sm shadow-sm"
              />
            </div>
          </div>
          <label className="flex items-center space-x-3 bg-white/80 backdrop-blur-sm px-4 py-3 rounded-xl border border-gray-200 shadow-sm">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">Auto-scroll</span>
          </label>
        </div>

        {/* Log Levels */}
        <div className="space-y-3">
          <label className="text-sm font-semibold text-gray-700">Filter by Level:</label>
          <div className="flex flex-wrap gap-2">
            {logLevels.map((level) => {
              const config = LOG_LEVEL_CONFIG[level]
              const isActive = filteredLogLevels.includes(level)
              return (
                <button
                  key={level}
                  onClick={() => handleLevelToggle(level)}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center space-x-2 hover:scale-105 ${
                    isActive
                      ? `${config.bgColor} ${config.color} border border-current shadow-sm`
                      : 'bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200'
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
      <div className="border-b border-gray-200/50 bg-gradient-to-r from-gray-50/50 to-blue-50/30">
        <nav className="flex space-x-1 px-6 py-2" aria-label="Tabs">
          {LOG_TABS.map((tab) => {
            const tabLogCount = getTabLogs(tab.id).length
            const isActive = activeTab === tab.id
            
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  isActive
                    ? 'bg-white border-blue-500 text-blue-700 shadow-sm'
                    : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-white/50'
                } whitespace-nowrap py-3 px-4 border-b-2 font-semibold text-sm flex items-center space-x-2 rounded-t-lg transition-all duration-200`}
              >
                <span className="text-base">{tab.icon}</span>
                <span>{tab.name}</span>
                {tabLogCount > 0 && (
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-bold ${
                    isActive 
                      ? 'bg-blue-100 text-blue-800' 
                      : 'bg-gray-200 text-gray-700'
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
        <div className="px-6 py-3 bg-gradient-to-r from-blue-50/50 to-indigo-50/30 border-b border-gray-200/50">
          <p className="text-sm text-gray-700 font-medium">
            📋 {LOG_TABS.find(t => t.id === activeTab)?.description}
          </p>
        </div>

        {/* Logs Display */}
        <div 
          ref={logsContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto bg-gradient-to-br from-gray-50/30 to-blue-50/20"
        >
          {activeTabLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center p-8 bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50">
                <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-gray-100 to-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-2xl">📋</span>
                </div>
                <div className="text-gray-600 text-lg font-semibold mb-2">No Logs</div>
                <div className="text-gray-500 text-sm max-w-sm">
                  {subscribedLogSources.length === 0 
                    ? 'Waiting for log sources to be available...'
                    : `No ${LOG_TABS.find(t => t.id === activeTab)?.name.toLowerCase()} logs match your current filters.`
                  }
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 space-y-3">
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
      <div className="border-t border-gray-200/50 px-6 py-4 bg-gradient-to-r from-gray-50/50 to-blue-50/30">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span className="font-medium">
            📊 Showing {activeTabLogs.length} {LOG_TABS.find(t => t.id === activeTab)?.name.toLowerCase()} logs of {logs.length} total
          </span>
          <span className="text-xs bg-white/80 px-3 py-1 rounded-full border border-gray-200">
            🔗 Sources: {subscribedLogSources.join(', ') || 'None'}
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
    <div className={`border rounded-xl p-4 ${config.bgColor} border-gray-200/50 hover:shadow-lg transition-all duration-200 hover:scale-[1.02] bg-white/80 backdrop-blur-sm`}>
      <div 
        className="flex items-start space-x-4 cursor-pointer" 
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-shrink-0 w-8 h-8 bg-white/80 rounded-lg flex items-center justify-center border border-gray-200/50">
          <span className="text-lg">{config.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-3 text-sm">
            <span className="font-mono text-gray-600 bg-gray-100/80 px-2 py-1 rounded-md">
              {formatTimestamp(log.timestamp)}
            </span>
            <span className={`font-bold px-2 py-1 rounded-md ${config.color} bg-white/80`}>
              {log.level}
            </span>
            <span className="text-gray-700 font-semibold bg-blue-50/80 px-2 py-1 rounded-md">
              {log.source}
            </span>
            <span className="text-gray-500 text-xs bg-gray-50/80 px-2 py-1 rounded-md">
              {log.logger}
            </span>
          </div>
          <div className="mt-3">
            <p className={`text-sm leading-relaxed ${expanded ? '' : 'truncate'} ${config.color} font-medium`}>
              {log.message}
            </p>
          </div>
          {expanded && (
            <div className="mt-4 text-xs text-gray-600 bg-gradient-to-r from-gray-50/80 to-blue-50/50 rounded-lg p-3 border border-gray-200/50">
              <div className="grid grid-cols-2 gap-3">
                <div><strong>Module:</strong> <code className="bg-gray-100 px-1 rounded">{log.module}</code></div>
                <div><strong>Function:</strong> <code className="bg-gray-100 px-1 rounded">{log.function}</code></div>
                <div><strong>Line:</strong> <code className="bg-gray-100 px-1 rounded">{log.line}</code></div>
                <div><strong>Source:</strong> <code className="bg-gray-100 px-1 rounded">{log.source}</code></div>
              </div>
            </div>
          )}
        </div>
        <button className="text-gray-400 hover:text-gray-700 flex-shrink-0 p-2 hover:bg-white/80 rounded-lg transition-colors">
          {expanded ? '▲' : '▼'}
        </button>
      </div>
    </div>
  )
}

export default LogViewer 