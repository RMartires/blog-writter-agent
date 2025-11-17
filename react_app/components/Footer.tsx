'use client'

import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="flex justify-between items-center px-8 py-6 border-t border-input-bg">
      <p className="text-text-secondary text-sm">
        © {new Date().getFullYear()} BlogCrafter. All rights reserved.
      </p>
      <Link
        href="/about"
        className="text-text-secondary text-sm hover:text-accent transition-colors"
      >
        About
      </Link>
    </footer>
  )
}

