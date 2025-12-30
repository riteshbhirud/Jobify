import { Sidebar } from "./Sidebar"
import { DashboardHeader } from "./DashboardHeader"

interface DashboardLayoutProps {
  children: React.ReactNode
  user: {
    email?: string | undefined
    id: string
  }
}

export function DashboardLayout({ children, user }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="md:pl-64 flex flex-col flex-1">
        <DashboardHeader user={user} />
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  )
}
