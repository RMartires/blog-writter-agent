'use client'

import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="flex flex-col md:flex-row justify-center md:justify-between items-center gap-4 px-4 md:px-8 py-4 md:py-6 border-t border-input-bg">
      <p className="text-text-secondary text-xs md:text-sm text-center md:text-left">
        © {new Date().getFullYear()} BlogCrafter. All rights reserved.
      </p>
      <Link
        href="/about"
        className="text-text-secondary text-xs md:text-sm hover:text-accent transition-colors"
      >
        About
      </Link>
    </footer>
  )
}

