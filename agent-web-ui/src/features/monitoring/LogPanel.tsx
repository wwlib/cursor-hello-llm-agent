import React, { useEffect, useRef, useState } from 'react'
import { useLogStore } from '../../stores/logStore'
import { useSessionStore } from '../../stores/sessionStore'
import { ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/24/outline'

interface LogPanelProps {
  className?: string
  maxHeight?: string
}

interface LogTab {
  id: string
  name: string
  sources: string[]
  icon: string
  color: string
}

const PANEL_TABS: LogTab[] = [
  {
    id: 'llm',
    name: 'AI',
    sources: ['ollama_general', 'ollama_digest', 'ollama_embed'],
    icon: '🧠',
    color: 'blue'
  },
  {
    id: 'agent',
    name: 'Agent',
    sources: ['agent'],
    icon: '🤖',
    color: 'green'
  },
  {
    id: 'system',
    name: 'System',
    sources: ['memory_manager', 'api'],
    icon: '⚙️',
    color: 'gray'
  }
]

const LogPanel: React.FC<LogPanelProps> = ({ 
  className = '', 
  maxHeight = 'max-h-64' 
}) => {
  const { currentSession } = useSessionStore()
  const {
    logs,
    availableLogSources,
    subscribedLogSources,
    isSubscribed,
    initializeLogStreaming,
    subscribeToLogs,
    unsubscribeFromLogs,
    clearLogs,
    cleanup
  } = useLogStore()

  const [isExpanded, setIsExpanded] = useState(false)
  const [activeTab, setActiveTab] = useState('llm') // Start with LLM tab
  const [autoSubscribe, setAutoSubscribe] = useState(true)
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
    if (autoSubscribe && availableLogSources.length > 0 && subscribedLogSources.length === 0) {
      console.log('🔍 LOG_PANEL: Auto-subscribing to all available sources:', availableLogSources)
      subscribeToLogs(availableLogSources)
    }
  }, [availableLogSources, subscribedLogSources, autoSubscribe, subscribeToLogs])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (isExpanded && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, isExpanded])

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit'
    })
  }

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'DEBUG': return 'text-gray-500'
      case 'INFO': return 'text-blue-600'
      case 'WARNING': return 'text-yellow-600'
      case 'ERROR': return 'text-red-600'
      case 'CRITICAL': return 'text-red-800'
      default: return 'text-gray-600'
    }
  }

  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'DEBUG': return '🔍'
      case 'INFO': return 'ℹ️'
      case 'WARNING': return '⚠️'
      case 'ERROR': return '❌'
      case 'CRITICAL': return '🚨'
      default: return 'ℹ️'
    }
  }

  // Get logs for the active tab
  const getTabLogs = (tabId: string) => {
    const tab = PANEL_TABS.find(t => t.id === tabId)
    if (!tab) return []

    return logs
      .filter(log => tab.sources.includes(log.source))
      .filter(log => ['INFO', 'WARNING', 'ERROR', 'CRITICAL'].includes(log.level))
      .slice(-15) // Last 15 logs for compact view
  }

  const activeTabLogs = getTabLogs(activeTab)
  const errorCount = logs.filter(log => log.level === 'ERROR' || log.level === 'CRITICAL').length
  const warningCount = logs.filter(log => log.level === 'WARNING').length

  if (!currentSession) {
    return null
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-700">System Logs</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            isSubscribed 
              ? 'bg-green-100 text-green-800' 
              : 'bg-gray-100 text-gray-800'
          }`}>
            {isSubscribed ? 'Live' : 'Off'}
          </span>
          {(errorCount > 0 || warningCount > 0) && (
            <div className="flex items-center space-x-1">
              {errorCount > 0 && (
                <span className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded-full">
                  {errorCount} errors
                </span>
              )}
              {warningCount > 0 && (
                <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                  {warningCount} warnings
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {logs.length > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                clearLogs()
              }}
              className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
            >
              Clear
            </button>
          )}
          {isExpanded ? (
            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <>
          {/* Mini Tabs */}
          <div className="border-b border-gray-200 px-3 py-2">
            <div className="flex space-x-1">
              {PANEL_TABS.map((tab) => {
                const tabLogCount = getTabLogs(tab.id).length
                const isActive = activeTab === tab.id
                
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-2 py-1 rounded text-xs font-medium transition-colors flex items-center space-x-1 ${
                      isActive
                        ? `bg-${tab.color}-100 text-${tab.color}-800 border border-${tab.color}-300`
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.name}</span>
                    {tabLogCount > 0 && (
                      <span className={`px-1 py-0.5 rounded text-xs ${
                        isActive ? 'bg-white bg-opacity-50' : 'bg-gray-200'
                      }`}>
                        {tabLogCount}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Logs Content */}
          <div className={`${maxHeight} overflow-y-auto bg-gray-50`} ref={logsContainerRef}>
            {activeTabLogs.length === 0 ? (
              <div className="p-4 text-center">
                <div className="text-gray-500 text-sm">No recent {PANEL_TABS.find(t => t.id === activeTab)?.name} logs</div>
                <div className="text-gray-400 text-xs mt-1">
                  Logs will appear here when the system is active
                </div>
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {activeTabLogs.map((log, index) => (
                  <div 
                    key={`${log.timestamp}-${index}`}
                    className="flex items-start space-x-2 p-2 rounded hover:bg-white hover:shadow-sm text-xs transition-colors"
                  >
                    <span className="text-sm flex-shrink-0">{getLogLevelIcon(log.level)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-gray-500 text-xs">
                          {formatTimestamp(log.timestamp)}
                        </span>
                        <span className={`font-medium text-xs ${getLogLevelColor(log.level)}`}>
                          {log.level}
                        </span>
                        <span className="text-gray-600 text-xs font-medium">
                          {log.source}
                        </span>
                      </div>
                      <div className="mt-0.5">
                        <p className="text-xs text-gray-700 truncate" title={log.message}>
                          {log.message}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </>
      )}

      {/* Footer with quick stats when collapsed */}
      {!isExpanded && activeTabLogs.length > 0 && (
        <div className="px-3 py-2 bg-gray-50 text-xs text-gray-600 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <span>Last: {activeTabLogs[activeTabLogs.length - 1]?.level} - {activeTabLogs[activeTabLogs.length - 1]?.source}</span>
            <span>{activeTabLogs.length} recent entries</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default LogPanel 