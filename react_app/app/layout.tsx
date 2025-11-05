import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Blog Writer',
  description: 'Generate high-quality blog posts with AI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

