'use client'

import { useState } from 'react'

export default function Home() {
  const [mode, setMode] = useState<'quick' | 'detailed'>('quick')
  const [topic, setTopic] = useState('')

  const handleGenerate = () => {
    if (!topic.trim()) {
      alert('Please enter a topic or keywords')
      return
    }
    // TODO: Connect to backend API
    console.log('Generating blog post:', { topic, mode })
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="flex justify-between items-center px-8 py-6">
        <div className="flex items-center gap-2">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-accent"
          >
            <path
              d="M4 19.5V4.5C4 3.897 4.447 3.5 5 3.5H19C19.553 3.5 20 3.897 20 4.5V19.5C20 20.103 19.553 20.5 19 20.5H5C4.447 20.5 4 20.103 4 19.5Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M4 8L12 13L20 8"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-text-primary text-xl font-semibold">
            AI Blog Writer
          </span>
        </div>
        <div className="w-10 h-10 rounded-full border-2 border-text-secondary flex items-center justify-center">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-text-secondary"
          >
            <path
              d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21M16 7C16 9.20914 14.2091 11 12 11C9.79086 11 8 9.20914 8 7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-8 py-12">
        <h1 className="text-5xl font-bold text-text-primary text-center mb-4">
          Unleash Your Next Great Blog Post
        </h1>
        <p className="text-text-secondary text-lg text-center mb-8">
          Enter a few keywords or a topic, and let our AI do the rest.
        </p>

        {/* Mode Selection */}
        {/* Input Field */}
        <div className="w-full max-w-2xl mb-6">
          <div className="relative">
            <div className="absolute left-4 top-1/2 transform -translate-y-1/2">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="text-text-secondary"
              >
                <path
                  d="M21 21L15 15M17 10C17 13.866 13.866 17 10 17C6.13401 17 3 13.866 3 10C3 6.13401 6.13401 3 10 3C13.866 3 17 6.13401 17 10Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleGenerate()
                }
              }}
              placeholder="e.g., 'future of remote work trends'"
              className="w-full pl-12 pr-4 py-4 rounded-lg bg-input-bg text-text-primary placeholder-text-secondary focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
        </div>

        {/* Generate Button */}
        <button
          onClick={handleGenerate}
          className="px-8 py-4 bg-accent text-text-primary rounded-lg font-semibold text-lg hover:bg-opacity-90 transition-all shadow-lg hover:shadow-xl"
        >
          Generate Blog
        </button>
      </main>

      {/* Footer */}
      <footer className="flex justify-between items-center px-8 py-6 border-t border-input-bg">
        <p className="text-text-secondary text-sm">
          © 2024 AI Blog Writer. All rights reserved.
        </p>
        <div className="flex gap-6">
          <a
            href="#"
            className="text-text-secondary text-sm hover:text-accent transition-colors"
          >
            About
          </a>
          <a
            href="#"
            className="text-text-secondary text-sm hover:text-accent transition-colors"
          >
            Privacy Policy
          </a>
          <a
            href="#"
            className="text-text-secondary text-sm hover:text-accent transition-colors"
          >
            Contact
          </a>
        </div>
      </footer>
    </div>
  )
}

