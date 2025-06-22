import React from 'react'
import type { ChatMessage } from '../../types/api'

interface MessageListProps {
  messages: ChatMessage[]
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  )
}

interface MessageBubbleProps {
  message: ChatMessage
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.type === 'user'
  const isSystem = message.type === 'system'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-3xl rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-indigo-600 text-white'
            : isSystem
            ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className="whitespace-pre-wrap break-words">
          {message.content}
        </div>
        <div
          className={`text-xs mt-1 ${
            isUser
              ? 'text-indigo-200'
              : isSystem
              ? 'text-yellow-600'
              : 'text-gray-500'
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}

export default MessageList 