'use client'

import { useAuth } from '@/components/AuthProvider'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'

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
    <header className="flex justify-between items-center px-4 md:px-8 py-4 md:py-6 border-b border-input-bg">
      <div className="flex items-center gap-2 md:gap-4">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/favicon.ico"
            alt="BlogCrafter logo"
            width={28}
            height={28}
            className="rounded-md w-6 h-6 md:w-7 md:h-7"
            priority
          />
          <span className="text-text-primary text-lg md:text-xl font-semibold">
            BlogCrafter
          </span>
        </Link>
        {showBackButton && (
          <button
            onClick={handleBack}
            className="px-3 md:px-4 py-2 text-text-secondary hover:text-accent transition-colors flex items-center gap-1 md:gap-2 text-xs md:text-sm"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-current w-3 h-3 md:w-4 md:h-4"
            >
              <path
                d="M19 12H5M5 12L12 19M5 12L12 5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span className="hidden sm:inline">{backLabel}</span>
          </button>
        )}
      </div>
      <div className="flex items-center gap-2 md:gap-4">
        {user && (
          <div className="flex items-center gap-2 md:gap-3">
            <div className="text-right hidden md:block">
              <p className="text-text-primary text-sm font-medium">
                {user.email || user.user_metadata?.full_name || 'User'}
              </p>
            </div>
            <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-accent flex items-center justify-center text-text-primary font-semibold text-sm md:text-base">
              {(user.email || user.user_metadata?.full_name || 'U')[0].toUpperCase()}
            </div>
            <button
              onClick={signOut}
              className="px-3 md:px-4 py-2 text-text-secondary hover:text-text-primary transition-colors text-xs md:text-sm"
            >
              Sign Out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

