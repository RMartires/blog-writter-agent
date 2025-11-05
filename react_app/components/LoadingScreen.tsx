'use client'

import Header from './Header'

interface LoadingScreenProps {
  message?: string
}

export default function LoadingScreen({ message = 'Researching keywords...' }: LoadingScreenProps) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      {/* Main Content - Loading */}
      <main className="flex-1 flex flex-col items-center justify-center px-8 py-12">
        {/* Spinning Loader - Circular with gap */}
        <div className="relative w-16 h-16 mb-6 flex items-center justify-center">
          <div className="w-16 h-16 border-4 border-accent/20 rounded-full"></div>
          <div className="absolute w-16 h-16 border-4 border-transparent border-t-accent rounded-full animate-spin"></div>
        </div>
        
        {/* Loading Message */}
        <p className="text-text-primary text-lg font-medium">
          {message}
        </p>
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

