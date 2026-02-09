// frontend/app/layout.tsx

import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'ApplyAFK - Never Miss a New Role',
  description: 'AI-powered job application automation. Be first to apply, cover every role that fits you.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}