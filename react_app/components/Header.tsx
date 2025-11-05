'use client'

import { useAuth } from '@/components/AuthProvider'
import { useRouter } from 'next/navigation'

interface HeaderProps {
  showBackButton?: boolean
  backUrl?: string
  backLabel?: string
}

export default function Header({ showBackButton = false, backUrl, backLabel = 'Back' }: HeaderProps) {
  const { user, signOut } = useAuth()
  const router = useRouter()

  const handleBack = () => {
    if (backUrl) {
      router.push(backUrl)
    } else {
      router.push('/')
    }
  }

  return (
    <header className="flex justify-between items-center px-8 py-6 border-b border-input-bg">
      <div className="flex items-center gap-4">
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
        {showBackButton && (
          <button
            onClick={handleBack}
            className="px-4 py-2 text-text-secondary hover:text-accent transition-colors flex items-center gap-2 text-sm"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-current"
            >
              <path
                d="M19 12H5M5 12L12 19M5 12L12 5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {backLabel}
          </button>
        )}
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-text-primary text-sm font-medium">
                {user.email || user.user_metadata?.full_name || 'User'}
              </p>
            </div>
            <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center text-text-primary font-semibold">
              {(user.email || user.user_metadata?.full_name || 'U')[0].toUpperCase()}
            </div>
            <button
              onClick={signOut}
              className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors text-sm"
            >
              Sign Out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

