// frontend/app/layout.tsx

import './globals.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'ApplyAFK - Never Miss a New Role',
  description: 'AI-powered job application automation. Be first to apply, cover every role that fits you.',
  icons: {
    icon: '/icon.png',
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'Inter, sans-serif' }}>{children}</body>
    </html>
  )
}