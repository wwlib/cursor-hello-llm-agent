import React, { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { 
  ChevronDownIcon, 
  PlusIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  ArrowUturnLeftIcon,
  ClockIcon,
  ArchiveBoxIcon
} from '@heroicons/react/24/outline'
import { useSessionStore } from '../../stores/sessionStore'
import type { SessionConfig } from '../../types/api'

const SessionSelector: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [activeTab, setActiveTab] = useState<'active' | 'dormant'>('active')
  const { 
    sessions, 
    dormantSessions,
    currentSession, 
    isLoading, 
    error,
    selectSession, 
    createSession, 
    deleteSession, 
    refreshSessions,
    refreshDormantSessions,
    restoreSession,
    clearError
  } = useSessionStore()

  useEffect(() => {
    // Load sessions on mount
    refreshSessions()
    refreshDormantSessions()
  }, [refreshSessions, refreshDormantSessions])

  const handleCreateSession = async (config: SessionConfig) => {
    try {
      await createSession(config)
      setShowCreateModal(false)
    } catch (error) {
      console.error('Failed to create session:', error)
      // Keep modal open on error so user can see the error message
    }
  }

  const handleDeleteSession = async (sessionId: string) => {
    if (confirm('Are you sure you want to delete this session?')) {
      try {
        await deleteSession(sessionId)
      } catch (error) {
        console.error('Failed to delete session:', error)
      }
    }
  }

  const handleRestoreSession = async (sessionId: string) => {
    try {
      await restoreSession(sessionId)
      setIsOpen(false)
    } catch (error) {
      console.error('Failed to restore session:', error)
    }
  }

  return (
    <>
      <div className="relative">
        <button
          type="button"
          className="flex items-center gap-x-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
          onClick={() => setIsOpen(!isOpen)}
        >
          <span>
            {currentSession 
              ? `Session: ${currentSession.session_id.slice(0, 8)}...`
              : 'No Session Selected'
            }
          </span>
          <ChevronDownIcon className="h-4 w-4 text-gray-400" />
        </button>

        {isOpen && (
          <div className="absolute right-0 z-10 mt-2 w-96 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
            <div className="px-3 py-2 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-900">Sessions</h3>
                <button
                  type="button"
                  className="flex items-center gap-x-1 rounded-md bg-indigo-600 px-2 py-1 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500"
                  onClick={() => {
                    setShowCreateModal(true)
                    setIsOpen(false)
                  }}
                >
                  <PlusIcon className="h-3 w-3" />
                  New
                </button>
              </div>
              
              {/* Tabs */}
              <div className="flex mt-2 space-x-1">
                <button
                  type="button"
                  className={`px-3 py-1 text-xs font-medium rounded-md ${
                    activeTab === 'active' 
                      ? 'bg-indigo-100 text-indigo-700' 
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                  onClick={() => setActiveTab('active')}
                >
                  Active ({sessions.length})
                </button>
                <button
                  type="button"
                  className={`px-3 py-1 text-xs font-medium rounded-md ${
                    activeTab === 'dormant' 
                      ? 'bg-indigo-100 text-indigo-700' 
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                  onClick={() => setActiveTab('dormant')}
                >
                  <ArchiveBoxIcon className="h-3 w-3 inline mr-1" />
                  Saved ({dormantSessions.length})
                </button>
              </div>
            </div>

            <div className="max-h-64 overflow-y-auto">
              {isLoading ? (
                <div className="px-3 py-2 text-sm text-gray-500">Loading sessions...</div>
              ) : activeTab === 'active' ? (
                sessions.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-500">No active sessions found</div>
                ) : (
                  sessions.map((session) => (
                    <div
                      key={session.session_id}
                      className={`group flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 ${
                        currentSession?.session_id === session.session_id ? 'bg-indigo-50' : ''
                      }`}
                    >
                      <div 
                        className="flex-1 cursor-pointer"
                        onClick={() => {
                          selectSession(session.session_id)
                          setIsOpen(false)
                        }}
                      >
                        <div className="font-medium text-gray-900">
                          {session.session_id.slice(0, 8)}...
                        </div>
                        <div className="text-xs text-gray-500">
                          {session.config.domain || 'Default'} • {' '}
                          {new Date(session.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-x-1 opacity-0 group-hover:opacity-100">
                        <button
                          type="button"
                          className="rounded p-1 text-gray-400 hover:text-red-600"
                          onClick={() => handleDeleteSession(session.session_id)}
                        >
                          <TrashIcon className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  ))
                )
              ) : (
                dormantSessions.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-500">No saved sessions found</div>
                ) : (
                  dormantSessions.map((session) => (
                    <div
                      key={session.session_id}
                      className="group flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50"
                    >
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">
                          {session.session_id.slice(0, 8)}...
                        </div>
                        <div className="text-xs text-gray-500">
                          {session.domain} • {session.conversation_count} msgs • {' '}
                          {new Date(session.last_activity).toLocaleDateString()}
                        </div>
                        {session.last_message && (
                          <div className="text-xs text-gray-400 truncate mt-1">
                            "{session.last_message}"
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-x-1 opacity-0 group-hover:opacity-100">
                        <button
                          type="button"
                          className="rounded p-1 text-gray-400 hover:text-indigo-600"
                          onClick={() => handleRestoreSession(session.session_id)}
                          title="Restore session"
                        >
                          <ArrowUturnLeftIcon className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  ))
                )
              )}
            </div>

            {error && (
              <div className="px-3 py-2 border-t border-gray-100 text-xs text-red-600">
                {error}
                <button
                  className="ml-2 underline"
                  onClick={clearError}
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Session Modal */}
      <CreateSessionModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreateSession={handleCreateSession}
      />
    </>
  )
}

interface CreateSessionModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateSession: (config: SessionConfig) => void
}

const CreateSessionModal: React.FC<CreateSessionModalProps> = ({
  isOpen,
  onClose,
  onCreateSession
}) => {
  const { isLoading, error } = useSessionStore()
  const [config, setConfig] = useState<SessionConfig>({
    domain: 'dnd',
    enable_graph: true
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onCreateSession(config)
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                  Create New Session
                </Dialog.Title>

                <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                  <div>
                    <label htmlFor="domain" className="block text-sm font-medium text-gray-700">
                      Domain
                    </label>
                    <select
                      id="domain"
                      value={config.domain || ''}
                      onChange={(e) => setConfig({ ...config, domain: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                    >
                      <option value="dnd">D&D Campaign</option>
                      <option value="general">General</option>
                      <option value="technical">Technical</option>
                    </select>
                  </div>

                  <div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={config.enable_graph || false}
                        onChange={(e) => setConfig({ ...config, enable_graph: e.target.checked })}
                        className="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        disabled={isLoading}
                      />
                      <span className="ml-2 text-sm text-gray-700">Enable Graph Memory</span>
                    </label>
                    {config.enable_graph && (
                      <p className="mt-1 text-xs text-gray-500">
                        ⚠️ Graph memory initialization may take 2-3 minutes for complex domains
                      </p>
                    )}
                  </div>

                  {error && (
                    <div className="rounded-md bg-red-50 p-3">
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  )}

                  {isLoading && (
                    <div className="rounded-md bg-blue-50 p-3">
                      <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                        <p className="text-sm text-blue-700">
                          Creating session... This may take up to 3 minutes for graph memory initialization.
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="mt-6 flex justify-end gap-3">
                    <button
                      type="button"
                      className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={onClose}
                      disabled={isLoading}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                      disabled={isLoading}
                    >
                      {isLoading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>}
                      {isLoading ? 'Creating...' : 'Create Session'}
                    </button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

export default SessionSelector 