import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Supported locales
const locales = ['en', 'de'];
const defaultLocale = 'en';

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
  const response = NextResponse.next();

  // Handle locale detection and cookie setting
  const localeCookie = request.cookies.get('locale');
  if (!localeCookie) {
    // Detect locale from Accept-Language header
    const acceptLanguage = request.headers.get('accept-language');
    let detectedLocale = defaultLocale;

    if (acceptLanguage) {
      const preferredLocale = acceptLanguage
        .split(',')
        .map((lang) => lang.split(';')[0].trim().substring(0, 2))
        .find((lang) => locales.includes(lang));

      if (preferredLocale) {
        detectedLocale = preferredLocale;
      }
    }

    // Set locale cookie for future requests
    response.cookies.set('locale', detectedLocale, {
      path: '/',
      maxAge: 365 * 24 * 60 * 60, // 1 year
      sameSite: 'lax',
    });
  }

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
    // Copy locale cookie to redirect response
    if (!localeCookie) {
      const acceptLanguage = request.headers.get('accept-language');
      let detectedLocale = defaultLocale;
      if (acceptLanguage) {
        const preferredLocale = acceptLanguage
          .split(',')
          .map((lang) => lang.split(';')[0].trim().substring(0, 2))
          .find((lang) => locales.includes(lang));
        if (preferredLocale) {
          detectedLocale = preferredLocale;
        }
      }
      redirectResponse.cookies.set('locale', detectedLocale, {
        path: '/',
        maxAge: 365 * 24 * 60 * 60,
        sameSite: 'lax',
      });
    }
    return redirectResponse;
  }

  // Root path redirects
  if (pathname === '/') {
    const redirectUrl = accessToken ? '/dashboard' : '/auth/signin';
    const redirectResponse = NextResponse.redirect(new URL(redirectUrl, request.url));
    // Copy locale cookie to redirect response
    if (!localeCookie) {
      const acceptLanguage = request.headers.get('accept-language');
      let detectedLocale = defaultLocale;
      if (acceptLanguage) {
        const preferredLocale = acceptLanguage
          .split(',')
          .map((lang) => lang.split(';')[0].trim().substring(0, 2))
          .find((lang) => locales.includes(lang));
        if (preferredLocale) {
          detectedLocale = preferredLocale;
        }
      }
      redirectResponse.cookies.set('locale', detectedLocale, {
        path: '/',
        maxAge: 365 * 24 * 60 * 60,
        sameSite: 'lax',
      });
    }
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
