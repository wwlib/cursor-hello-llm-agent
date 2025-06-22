import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import ChatInterface from './features/chat/ChatInterface'
import LogViewer from './features/monitoring/LogViewer'

function App() {
  return (
    <Router>
      <div className="h-screen">
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat" element={<ChatInterface />} />
            <Route path="memory" element={<div className="text-center text-gray-500">Memory Browser - Coming Soon</div>} />
            <Route path="graph" element={<div className="text-center text-gray-500">Graph Visualization - Coming Soon</div>} />
            <Route path="logs" element={<LogViewer />} />
            <Route path="settings" element={<div className="text-center text-gray-500">Settings - Coming Soon</div>} />
            <Route path="help" element={<div className="text-center text-gray-500">Help - Coming Soon</div>} />
          </Route>
        </Routes>
      </div>
    </Router>
  )
}

export default App
