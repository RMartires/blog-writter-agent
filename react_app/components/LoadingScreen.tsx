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
      <main className="flex-1 flex flex-col items-center justify-center px-4 md:px-8 py-8 md:py-12">
        {/* Spinning Loader - Circular with gap */}
        <div className="relative w-12 h-12 md:w-16 md:h-16 mb-6 flex items-center justify-center">
          <div className="w-12 h-12 md:w-16 md:h-16 border-4 border-accent/20 rounded-full"></div>
          <div className="absolute w-12 h-12 md:w-16 md:h-16 border-4 border-transparent border-t-accent rounded-full animate-spin"></div>
        </div>
        
        {/* Loading Message */}
        <p className="text-text-primary text-base md:text-lg font-medium px-4 text-center">
          {message}
        </p>
      </main>

      <Footer />
    </div>
  )
}

