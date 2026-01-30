import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that are always public (no authentication required)
const publicRoutes = [
  '/auth/signin',
  '/auth/error',
  '/unauthorized',
  '/setup',  // Setup page is public for initial configuration
];

// Routes that require authentication
const protectedRoutes = [
  '/dashboard',
  '/providers',
  '/users',
  '/licenses',
  '/reports',
  '/settings',
  '/admin',
  '/profile',
];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes without authentication check
  if (publicRoutes.some(route => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Allow static files and API routes
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Check for authentication cookie (httpOnly cookie set by backend)
  // Note: We can only check presence, not validate the token server-side
  // Full validation happens on the backend when the token is used
  const accessToken = request.cookies.get('access_token');

  // Check if this is a protected route
  const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));

  if (isProtectedRoute && !accessToken) {
    // Redirect to signin with callback URL
    const signinUrl = new URL('/auth/signin', request.url);
    // Only set callback for safe paths (prevent open redirect)
    if (pathname.startsWith('/') && !pathname.includes(':') && !pathname.startsWith('//')) {
      signinUrl.searchParams.set('callbackUrl', pathname);
    }
    return NextResponse.redirect(signinUrl);
  }

  // Root path redirects
  if (pathname === '/') {
    if (accessToken) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    } else {
      return NextResponse.redirect(new URL('/auth/signin', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all paths except static files and API routes
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
