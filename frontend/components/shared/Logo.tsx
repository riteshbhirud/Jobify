import Link from "next/link"
import { Zap } from "lucide-react"

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={className}>
      <div className="flex items-center gap-2 group">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg group-hover:shadow-glow transition-shadow duration-300">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <span className="text-xl font-bold text-gradient">
          Jobify
        </span>
      </div>
    </Link>
  )
}
