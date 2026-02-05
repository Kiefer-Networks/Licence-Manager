import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { detectLocaleFromHeader } from '@/lib/locales';

// Locale cookie settings
const LOCALE_COOKIE_NAME = 'locale';
const LOCALE_COOKIE_MAX_AGE = 365 * 24 * 60 * 60; // 1 year

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

/**
 * Set locale cookie on a response if not already present in request.
 */
function setLocaleCookie(
  response: NextResponse,
  request: NextRequest,
  localeCookie: ReturnType<typeof request.cookies.get>
): void {
  if (!localeCookie) {
    const acceptLanguage = request.headers.get('accept-language');
    const detectedLocale = detectLocaleFromHeader(acceptLanguage);
    response.cookies.set(LOCALE_COOKIE_NAME, detectedLocale, {
      path: '/',
      maxAge: LOCALE_COOKIE_MAX_AGE,
      sameSite: 'lax',
    });
  }
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const response = NextResponse.next();
  const localeCookie = request.cookies.get(LOCALE_COOKIE_NAME);

  // Handle locale detection and cookie setting
  setLocaleCookie(response, request, localeCookie);

  // Allow public routes without authentication check
  if (publicRoutes.some(route => pathname.startsWith(route))) {
    return response;
  }

  // Allow static files and API routes
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return response;
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
    const redirectResponse = NextResponse.redirect(signinUrl);
    setLocaleCookie(redirectResponse, request, localeCookie);
    return redirectResponse;
  }

  // Root path redirects
  if (pathname === '/') {
    const redirectUrl = accessToken ? '/dashboard' : '/auth/signin';
    const redirectResponse = NextResponse.redirect(new URL(redirectUrl, request.url));
    setLocaleCookie(redirectResponse, request, localeCookie);
    return redirectResponse;
  }

  return response;
}

export const config = {
  matcher: [
    // Match all paths except static files and API routes
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
