import Link from "next/link"

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={className}>
      <div className="flex items-center space-x-2">
        <span className="text-2xl">🚀</span>
        <span className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          Jobify
        </span>
      </div>
    </Link>
  )
}
