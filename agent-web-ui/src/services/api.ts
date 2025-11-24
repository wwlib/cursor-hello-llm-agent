import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import type {
  CreateSessionRequest,
  CreateSessionResponse,
  SessionInfo,
  SessionListResponse,
  AgentQueryRequest,
  AgentQueryResponse,
  AgentStatusResponse,
  MemoryQueryParams,
  MemoryDataResponse,
  MemorySearchRequest,
  MemorySearchResponse,
  MemoryStatsResponse,
  GraphQueryParams,
  GraphDataResponse,
  EntityDetailsResponse,
  GraphStatsResponse,
  HealthResponse,
  SessionLogsResponse,
  SessionLogContentsResponse
} from '../types/api'

class AgentAPIClient {
  private axiosInstance: AxiosInstance
  private baseURL: string

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    
    this.axiosInstance = axios.create({
      baseURL: this.baseURL,
      timeout: 180000, // Increase to 3 minutes for session creation
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor for auth tokens (future)
    this.axiosInstance.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // Response interceptor for error handling
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error)
        if (error.response?.status === 401) {
          // Handle authentication errors
          localStorage.removeItem('auth_token')
        }
        return Promise.reject(error)
      }
    )
  }

  // Health Check
  async getHealth(): Promise<HealthResponse> {
    const response: AxiosResponse<HealthResponse> = await this.axiosInstance.get('/health')
    return response.data
  }

  // Session Management
  async createSession(request: CreateSessionRequest): Promise<CreateSessionResponse> {
    const response: AxiosResponse<CreateSessionResponse> = await this.axiosInstance.post(
      '/api/v1/sessions',
      request
    )
    return response.data
  }

  async getSession(sessionId: string): Promise<SessionInfo> {
    const response: AxiosResponse<SessionInfo> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}`
    )
    return response.data
  }

  async deleteSession(sessionId: string): Promise<{ status: string }> {
    const response: AxiosResponse<{ status: string }> = await this.axiosInstance.delete(
      `/api/v1/sessions/${sessionId}`
    )
    return response.data
  }

  async listSessions(): Promise<SessionListResponse> {
    const response: AxiosResponse<SessionListResponse> = await this.axiosInstance.get(
      '/api/v1/sessions'
    )
    return response.data
  }

  async cleanupSessions(): Promise<{ status: string; cleaned_count: number }> {
    const response = await this.axiosInstance.post('/api/v1/sessions/cleanup')
    return response.data
  }

  async listDormantSessions(): Promise<{ sessions: any[]; total: number; status: string }> {
    const response: AxiosResponse<{ sessions: any[]; total: number; status: string }> = await this.axiosInstance.get(
      '/api/v1/sessions/dormant'
    )
    return response.data
  }

  async restoreSession(sessionId: string): Promise<{ status: string; message: string; session_info: any }> {
    const response: AxiosResponse<{ status: string; message: string; session_info: any }> = await this.axiosInstance.post(
      `/api/v1/sessions/${sessionId}/restore`
    )
    return response.data
  }

  async getRegistryStats(): Promise<{ stats: any; status: string }> {
    const response: AxiosResponse<{ stats: any; status: string }> = await this.axiosInstance.get(
      '/api/v1/sessions/registry/stats'
    )
    return response.data
  }

  // Agent Interaction
  async queryAgent(sessionId: string, request: AgentQueryRequest): Promise<AgentQueryResponse> {
    const response: AxiosResponse<AgentQueryResponse> = await this.axiosInstance.post(
      `/api/v1/sessions/${sessionId}/query`,
      request
    )
    return response.data
  }

  async getAgentStatus(sessionId: string): Promise<AgentStatusResponse> {
    const response: AxiosResponse<AgentStatusResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/status`
    )
    return response.data
  }

  // Memory Operations
  async getMemoryData(sessionId: string, params: MemoryQueryParams = {}): Promise<MemoryDataResponse> {
    const response: AxiosResponse<MemoryDataResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/memory`,
      { params }
    )
    return response.data
  }

  async searchMemory(sessionId: string, request: MemorySearchRequest): Promise<MemorySearchResponse> {
    const response: AxiosResponse<MemorySearchResponse> = await this.axiosInstance.post(
      `/api/v1/sessions/${sessionId}/memory/search`,
      request
    )
    return response.data
  }

  async getMemoryStats(sessionId: string): Promise<MemoryStatsResponse> {
    const response: AxiosResponse<MemoryStatsResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/memory/stats`
    )
    return response.data
  }

  // Graph Operations
  async getGraphData(sessionId: string, params: GraphQueryParams = {}): Promise<GraphDataResponse> {
    const response: AxiosResponse<GraphDataResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/graph`,
      { params }
    )
    return response.data
  }

  async getEntityDetails(sessionId: string, entityId: string): Promise<EntityDetailsResponse> {
    const response: AxiosResponse<EntityDetailsResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/graph/entity/${entityId}`
    )
    return response.data
  }

  async getGraphStats(sessionId: string): Promise<GraphStatsResponse> {
    const response: AxiosResponse<GraphStatsResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/graph/stats`
    )
    return response.data
  }

  // Log File Operations
  async listSessionLogs(sessionId: string): Promise<SessionLogsResponse> {
    const response: AxiosResponse<SessionLogsResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/logs`
    )
    return response.data
  }

  async getSessionLogContents(sessionId: string, logFilename: string): Promise<SessionLogContentsResponse> {
    const response: AxiosResponse<SessionLogContentsResponse> = await this.axiosInstance.get(
      `/api/v1/sessions/${sessionId}/logs/${logFilename}`
    )
    return response.data
  }
}

// Create singleton instance
export const apiClient = new AgentAPIClient()
export default apiClient 