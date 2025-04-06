import { useState } from 'react'
import { PaperAirplaneIcon } from '@heroicons/react/24/solid'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage = input.trim()
    setInput('')
    setIsLoading(true)

    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      console.log('Sending request to backend...')
      // Connection to the backend
      const response = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage,
          forceRefresh: false
        }),
      })

      console.log('Response status:', response.status)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log('Response data:', data)
      
      // Add assistant message to chat with query type
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.response,
        source: data.metadata.source,
        queryType: data.metadata.query_type
      }])
    } catch (error) {
      console.error('Error details:', error)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Error: ${error.message}. Please make sure the backend server is running on port 8000.` 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const getQueryTypeColor = (queryType) => {
    return queryType === 'timesensitive' ? 'text-red-500' : 'text-green-500'
  }

  const getQueryTypeLabel = (queryType) => {
    return queryType === 'timesensitive' ? 'Time-Sensitive' : 'Evergreen'
  }

  return (
    <div className="main-container">
      {/* Header */}
      <header className="header">
        <h1>Semantic Cache Chat</h1>
      </header>

      {/* Messages container */}
      <div className="messages-container">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message-container ${
              message.role === 'user' ? 'user-message' : 'assistant-message'
            }`}
          >
            <p>{message.content}</p>
            {message.source && (
              <div className="message-metadata">
                <span>Source: {message.source}</span>
                {message.queryType && (
                  <span className={getQueryTypeColor(message.queryType)}>
                    Type: {getQueryTypeLabel(message.queryType)}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="loading-indicator">
            <p>Thinking...</p>
          </div>
        )}
      </div>

      {/* Input container */}
      <div className="input-container">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="chat-input"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center"
          >
            <PaperAirplaneIcon className="h-5 w-5" />
          </button>
        </form>
      </div>
    </div>
  )
}

export default App