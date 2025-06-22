import type { WebSocketMessage, WebSocketResponse } from '../types/api'

type WebSocketEventHandler = (data: WebSocketResponse) => void

export class WebSocketService {
  private socket: WebSocket | null = null
  private sessionId: string | null = null
  private eventHandlers: Map<string, WebSocketEventHandler[]> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private heartbeatInterval: number | null = null
  private isConnecting = false

  constructor() {
    this.setupEventHandlers()
  }

  private setupEventHandlers() {
    // Initialize default event handler arrays
    const eventTypes = [
      'query_response',
      'typing_start',
      'typing_end',
      'status_response',
      'memory_response',
      'search_response',
      'graph_response',
      'memory_update',
      'graph_update',
      'error'
    ]
    
    eventTypes.forEach(type => {
      this.eventHandlers.set(type, [])
    })
  }

  async connect(sessionId: string): Promise<void> {
    if (this.isConnecting || (this.socket && this.socket.readyState === WebSocket.OPEN)) {
      return
    }

    this.isConnecting = true
    this.sessionId = sessionId

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    const url = `${wsUrl}/api/v1/ws/sessions/${sessionId}`

    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(url)

        this.socket.onopen = () => {
          console.log('WebSocket connected')
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.startHeartbeat()
          resolve()
        }

        this.socket.onmessage = (event) => {
          try {
            const response: WebSocketResponse = JSON.parse(event.data)
            this.handleMessage(response)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.socket.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason)
          this.isConnecting = false
          this.stopHeartbeat()
          
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => this.reconnect(), this.reconnectDelay)
          }
        }

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnecting = false
          reject(error)
        }
      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  private async reconnect() {
    if (!this.sessionId || this.isConnecting) return

    this.reconnectAttempts++
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    try {
      await this.connect(this.sessionId)
    } catch (error) {
      console.error('Reconnection failed:', error)
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => this.reconnect(), this.reconnectDelay * this.reconnectAttempts)
      }
    }
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.sendMessage({ type: 'heartbeat', data: {} })
    }, 30000) // 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private handleMessage(response: WebSocketResponse) {
    const handlers = this.eventHandlers.get(response.type) || []
    handlers.forEach(handler => {
      try {
        handler(response)
      } catch (error) {
        console.error('Error in WebSocket message handler:', error)
      }
    })
  }

  sendMessage(message: WebSocketMessage) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send message')
      return false
    }

    try {
      this.socket.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('Failed to send WebSocket message:', error)
      return false
    }
  }

  // Convenience methods for common operations
  queryAgent(message: string, context?: Record<string, any>) {
    return this.sendMessage({
      type: 'query',
      data: { message, context }
    })
  }

  getStatus() {
    return this.sendMessage({
      type: 'get_status',
      data: {}
    })
  }

  getMemory(type?: string, limit?: number, offset?: number) {
    return this.sendMessage({
      type: 'get_memory',
      data: { type, limit, offset }
    })
  }

  searchMemory(query: string, filters?: Record<string, any>) {
    return this.sendMessage({
      type: 'search_memory',
      data: { query, filters }
    })
  }

  getGraph(format?: string, include_metadata?: boolean) {
    return this.sendMessage({
      type: 'get_graph',
      data: { format, include_metadata }
    })
  }

  ping() {
    return this.sendMessage({
      type: 'ping',
      data: { timestamp: Date.now() }
    })
  }

  // Event subscription methods
  on(eventType: string, handler: WebSocketEventHandler) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, [])
    }
    this.eventHandlers.get(eventType)!.push(handler)
  }

  off(eventType: string, handler: WebSocketEventHandler) {
    const handlers = this.eventHandlers.get(eventType)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect')
      this.socket = null
    }
    this.sessionId = null
    this.reconnectAttempts = 0
  }

  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN
  }

  get connectionState(): string {
    if (!this.socket) return 'disconnected'
    
    switch (this.socket.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'closed'
      default: return 'unknown'
    }
  }
}

// Create singleton instance
export const wsService = new WebSocketService()
export default wsService 