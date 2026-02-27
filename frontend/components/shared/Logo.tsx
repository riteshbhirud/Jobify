import Link from "next/link"
import Image from "next/image"

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={className}>
      <div className="flex items-center gap-2.5 group">
        <Image
          src="/logo.png"
          alt="ApplyAFK"
          width={36}
          height={24}
          className="group-hover:brightness-110 transition-all duration-200"
        />
        <span className="text-xl font-bold">
          <span className="text-foreground">Apply</span>
          <span className="text-gradient">AFK</span>
        </span>
      </div>
    </Link>
  )
}
