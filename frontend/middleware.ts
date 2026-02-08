// frontend/middleware.ts

import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          cookiesToSet.forEach(({ name, value, options }) => {
            request.cookies.set(name, value)
            response.cookies.set(name, value, options)
          })
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  const pathname = request.nextUrl.pathname

  // Protected routes - redirect to login if not authenticated
  if (
    pathname.startsWith('/dashboard') ||
    pathname.startsWith('/onboarding') ||
    pathname.startsWith('/subscribe')
  ) {
    if (!user) {
      return NextResponse.redirect(new URL('/auth/login', request.url))
    }

    // Fetch profile once for all protected route checks
    const { data: profile } = await supabase
      .from('users')
      .select('onboarding_completed, subscription_status')
      .eq('id', user.id)
      .single()

    const isSubscribed =
      profile?.subscription_status === 'active' ||
      profile?.subscription_status === 'trialing'

    // Dashboard and onboarding require active subscription
    if (pathname.startsWith('/dashboard') || pathname.startsWith('/onboarding')) {
      if (!isSubscribed) {
        // Route to reactivate if they already completed onboarding before
        const target = profile?.onboarding_completed
          ? '/subscribe/reactivate'
          : '/subscribe'
        return NextResponse.redirect(new URL(target, request.url))
      }
    }

    // Dashboard also requires completed onboarding
    if (pathname.startsWith('/dashboard')) {
      if (!profile?.onboarding_completed) {
        return NextResponse.redirect(new URL('/onboarding', request.url))
      }
    }

    // Subscribe pages - redirect forward if already subscribed
    if (pathname.startsWith('/subscribe')) {
      if (isSubscribed) {
        if (profile?.onboarding_completed) {
          return NextResponse.redirect(new URL('/dashboard', request.url))
        } else {
          return NextResponse.redirect(new URL('/onboarding', request.url))
        }
      }
    }
  }

  // Auth routes - redirect based on status if already authenticated
  if (pathname === '/auth/login' || pathname === '/auth/signup') {
    if (user) {
      const { data: profile } = await supabase
        .from('users')
        .select('onboarding_completed, subscription_status')
        .eq('id', user.id)
        .single()

      const isSubscribed =
        profile?.subscription_status === 'active' ||
        profile?.subscription_status === 'trialing'

      if (!isSubscribed) {
        return NextResponse.redirect(new URL('/subscribe', request.url))
      } else if (profile?.onboarding_completed) {
        return NextResponse.redirect(new URL('/dashboard', request.url))
      } else {
        return NextResponse.redirect(new URL('/onboarding', request.url))
      }
    }
  }

  return response
}

export const config = {
  matcher: ['/dashboard/:path*', '/auth/login', '/auth/signup', '/onboarding/:path*', '/subscribe/:path*'],
}
