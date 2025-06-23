// Session Types
export interface SessionConfig {
  domain?: string
  llm_model?: string
  embed_model?: string
  max_memory_size?: number
  enable_graph?: boolean
  custom_config?: Record<string, any>
}

export interface CreateSessionRequest {
  config: SessionConfig
  user_id?: string
}

export interface CreateSessionResponse {
  session_id: string
  status: string
}

export interface SessionInfo {
  session_id: string
  user_id?: string
  created_at: string
  last_activity: string
  status: string
  config: SessionConfig
}

export interface SessionListResponse {
  sessions: SessionInfo[]
  total: number
}

// Agent Types
export interface AgentQueryRequest {
  message: string
  context?: Record<string, any>
}

export interface AgentQueryResponse {
  response: string
  session_id: string
  timestamp: string
  memory_updates?: any[]
  graph_updates?: any[]
}

export interface AgentStatusResponse {
  status: string
  session_id: string
  config: SessionConfig
  last_activity: string
}

// Memory Types
export interface MemoryQueryParams {
  type?: 'conversations' | 'entities' | 'relationships'
  limit?: number
  offset?: number
}

export interface MemoryDataResponse {
  data: any[]
  total: number
  pagination: {
    limit: number
    offset: number
    has_more: boolean
  }
}

export interface MemorySearchRequest {
  query: string
  filters?: Record<string, any>
}

export interface MemorySearchResponse {
  results: any[]
  relevance_scores: number[]
  total: number
}

export interface MemoryStatsResponse {
  conversation_count: number
  entity_count: number
  relationship_count: number
  total_memory_size: number
}

// Graph Types
export interface GraphQueryParams {
  format?: 'json' | 'd3'
  include_metadata?: boolean
}

export interface GraphNode {
  id: string
  name: string
  type: string
  description: string
  metadata?: Record<string, any>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  description: string
  metadata?: Record<string, any>
}

export interface GraphDataResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  metadata: Record<string, any>
  stats?: {
    nodes: number
    edges: number
    total_entities: number
    total_relationships: number
  }
}

export interface EntityDetailsResponse {
  entity_id: string
  type: string
  properties: Record<string, any>
  relationships: Array<{
    type: string
    target_entity: string
    properties: Record<string, any>
  }>
}

export interface GraphStatsResponse {
  node_count: number
  edge_count: number
  entity_types: Record<string, number>
  relationship_types: Record<string, number>
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'query' | 'heartbeat' | 'get_status' | 'get_memory' | 'search_memory' | 'get_graph' | 'ping' | 'get_log_sources' | 'subscribe_logs' | 'unsubscribe_logs'
  data: any
}

export interface WebSocketResponse {
  type: string
  data: any
  session_id?: string
  timestamp?: string
}

// Log Streaming Types
export interface LogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  logger: string
  message: string
  source: string
  session_id: string
  module: string
  function: string
  line: number
}

export interface LogSubscriptionRequest {
  connection_id: string
  log_sources: string[]
}

export interface LogSourcesResponse {
  available_sources: string[]
}

export interface LogStreamMessage {
  type: 'log_stream'
  data: LogEntry
}

export interface LogSubscriptionResponse {
  type: 'logs_subscribed' | 'logs_unsubscribed'
  data: {
    connection_id: string
    subscribed_sources?: string[]
    unsubscribed_sources?: string[]
  }
}

// Chat Types
export interface ChatMessage {
  id: string
  type: 'user' | 'agent' | 'system'
  content: string
  timestamp: string
  session_id: string
}

// Health Check
export interface HealthResponse {
  status: string
  session_count: number
  timestamp: string
} 