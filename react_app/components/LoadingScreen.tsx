'use client'

import Header from './Header'
import Footer from './Footer'

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

      <Footer />
    </div>
  )
}

