# Agent Web UI

A modern React-based web interface for the Agent System API, providing an intuitive chat interface for agent interaction, memory exploration, and graph visualization.

## Features

### ✅ Phase 1 Complete - Core Infrastructure
- **React 18+ with TypeScript** - Type-safe component architecture
- **Tailwind CSS** - Modern, responsive styling
- **React Router** - Client-side routing and navigation
- **Zustand** - Lightweight state management
- **API Integration** - Complete REST API client with error handling
- **WebSocket Support** - Real-time communication with agent

### ✅ Phase 2 Complete - Session & Chat
- **Session Management** - Create, select, and manage agent sessions
- **Real-time Chat** - Interactive chat interface with typing indicators
- **Message History** - Persistent conversation tracking
- **Connection Status** - Real-time connection monitoring
- **Responsive Design** - Mobile and desktop optimized

### 🚧 Coming Soon
- **Memory Browser** - Explore conversation history and entities
- **Graph Visualization** - Interactive relationship networks
- **Advanced Features** - Search, filtering, and analytics

## Getting Started

### Prerequisites

1. **Agent System API** must be running on `http://localhost:8000`
2. **Node.js 18+** and **npm** installed

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Usage

1. **Start the Agent API Server**:
   ```bash
   # From the main project directory
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

2. **Start the Web UI**:
   ```bash
   # From the agent-web-ui directory
   npm run dev
   ```

3. **Access the application** at `http://localhost:5173`

4. **Create a Session**:
   - Click the session selector in the top navigation
   - Click "New" to create a session
   - Choose domain (D&D, General, Technical)
   - Enable/disable graph memory
   - Click "Create Session"

5. **Start Chatting**:
   - Type your message in the chat input
   - Press Enter or click the send button
   - Watch for typing indicators and real-time responses

## Architecture

### Component Structure
```
src/
├── components/          # Reusable UI components
├── features/           # Feature-specific components
│   ├── chat/          # Chat interface components
│   ├── sessions/      # Session management
│   └── memory/        # Memory browser (coming soon)
├── services/          # API integration layer
├── stores/            # State management (Zustand)
├── types/             # TypeScript type definitions
└── utils/             # Helper functions
```

### State Management
- **Session Store** - Manages agent sessions and current selection
- **Chat Store** - Handles message history and real-time communication
- **WebSocket Service** - Real-time connection management

### API Integration
- **REST Client** - Full API coverage for all endpoints
- **WebSocket Client** - Real-time agent communication
- **Error Handling** - Graceful error recovery and user feedback

## Configuration

### Environment Variables
```bash
# .env.development
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=Agent System
VITE_DEBUG_MODE=true
```

### API Proxy
The development server proxies `/api/*` requests to the Agent API server automatically.

## Development

### Available Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Technologies Used
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS
- **Headless UI** - Accessible UI components
- **Heroicons** - Icon library
- **Zustand** - State management
- **Axios** - HTTP client

## Troubleshooting

### Connection Issues
- Ensure the Agent API server is running on port 8000
- Check browser console for WebSocket connection errors
- Verify API proxy configuration in `vite.config.ts`

### Session Problems
- Try refreshing the session list
- Clear browser localStorage if sessions appear corrupted
- Restart both API server and web UI

### Performance
- Large conversation histories may impact performance
- Graph visualization optimized for <1000 nodes
- WebSocket reconnection handles temporary disconnections

## Future Enhancements

### Phase 3 - Memory Browser
- Conversation history search and filtering
- Entity exploration and details
- Memory statistics and analytics

### Phase 4 - Graph Visualization
- Interactive node-link diagrams
- Entity relationship exploration
- Graph filtering and search

### Advanced Features
- Multi-session management
- Conversation export/import
- Collaborative features
- Mobile app companion

## Contributing

This is part of the larger Agent System project. See the main project README for contribution guidelines.

## License

Same as the main Agent System project.
