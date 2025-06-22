import React, { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { 
  Bars3Icon, 
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  CircleStackIcon,
  ShareIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  QuestionMarkCircleIcon
} from '@heroicons/react/24/outline'
import { useSessionStore } from '../../stores/sessionStore'
import SessionSelector from './SessionSelector'

interface SidebarItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  current?: boolean
}

const navigation: SidebarItem[] = [
  { name: 'Chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'Memory', href: '/memory', icon: CircleStackIcon },
  { name: 'Graph', href: '/graph', icon: ShareIcon },
  { name: 'Logs', href: '/logs', icon: DocumentTextIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
  { name: 'Help', href: '/help', icon: QuestionMarkCircleIcon },
]

const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const { currentSession } = useSessionStore()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-full max-w-xs flex-col bg-white shadow-2xl">
          <div className="flex h-16 items-center justify-between px-6 bg-gradient-to-r from-blue-600 to-indigo-600">
            <h1 className="text-xl font-bold text-white">Agent System</h1>
            <button
              type="button"
              className="text-blue-100 hover:text-white transition-colors"
              onClick={() => setSidebarOpen(false)}
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <SidebarContent currentPath={location.pathname} />
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col">
        <div className="flex min-h-0 flex-1 flex-col bg-white/80 backdrop-blur-xl border-r border-gray-200/50 shadow-xl">
          <div className="flex h-16 items-center px-6 bg-gradient-to-r from-blue-600 to-indigo-600">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">🤖</span>
              </div>
              <h1 className="text-xl font-bold text-white">Agent System</h1>
            </div>
          </div>
          <SidebarContent currentPath={location.pathname} />
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-72">
        {/* Header */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200/50 bg-white/80 backdrop-blur-xl px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          <button
            type="button"
            className="-m-2.5 p-2.5 text-gray-700 hover:text-gray-900 lg:hidden transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>

          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              <SessionSelector />
            </div>
            
            <div className="flex items-center gap-x-4 lg:gap-x-6 ml-auto">
              {currentSession && (
                <div className="flex items-center text-sm text-gray-600">
                  <div className="flex items-center gap-x-2 bg-green-50 px-3 py-1.5 rounded-full border border-green-200">
                    <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="font-medium text-green-700">Active Session</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="py-8">
          <div className="px-4 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

interface SidebarContentProps {
  currentPath: string
}

const SidebarContent: React.FC<SidebarContentProps> = ({ currentPath }) => {
  return (
    <nav className="flex flex-1 flex-col p-4">
      <ul role="list" className="flex flex-1 flex-col gap-y-2">
        <li>
          <ul role="list" className="space-y-1">
            {navigation.map((item) => {
              const isCurrent = currentPath === item.href
              return (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`group flex gap-x-3 rounded-xl p-3 text-sm font-semibold transition-all duration-200 ${
                      isCurrent
                        ? 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200 shadow-sm'
                        : 'text-gray-700 hover:text-blue-700 hover:bg-gray-50 hover:scale-105'
                    }`}
                  >
                    <item.icon
                      className={`h-6 w-6 shrink-0 transition-colors ${
                        isCurrent ? 'text-blue-600' : 'text-gray-500 group-hover:text-blue-600'
                      }`}
                    />
                    {item.name}
                    {isCurrent && (
                      <div className="ml-auto w-2 h-2 bg-blue-500 rounded-full"></div>
                    )}
                  </Link>
                </li>
              )
            })}
          </ul>
        </li>
        
        {/* Footer section */}
        <li className="mt-auto">
          <div className="text-xs text-gray-500 px-3 py-2 border-t border-gray-200 bg-gray-50/50 rounded-lg">
            <div className="font-medium">Agent System v1.0</div>
            <div className="mt-1">Intelligent conversation platform</div>
          </div>
        </li>
      </ul>
    </nav>
  )
}

export default MainLayout 