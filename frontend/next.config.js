const createNextIntlPlugin = require('next-intl/plugin');

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

// Public API URL for client-side (CSP headers, browser requests)
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
// Internal backend URL for server-side rewrites (Docker network)
const backendUrl = process.env.BACKEND_URL || apiUrl;

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  outputFileTracingIncludes: {
    '/*': ['./messages/**'],
  },
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'cdn.hibob.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'cdn.auth0.com',
        pathname: '/**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          {
            // NOTE: 'unsafe-inline' is required for Next.js hydration scripts.
            // Next.js injects inline scripts during SSR which cannot use nonces yet.
            // See: https://github.com/vercel/next.js/discussions/42170
            // TODO: Switch to nonce-based CSP when Next.js adds native support.
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              `img-src 'self' ${apiUrl} https://lh3.googleusercontent.com https://upload.wikimedia.org https://raw.githubusercontent.com https://resources.jetbrains.com https://cdn.hibob.com https://cdn.auth0.com https://www.mailjet.com https://cursor.com https://www.cursor.com https://huggingface.co data: blob:`,
              "font-src 'self' data:",
              `connect-src 'self' ${apiUrl}`,
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "object-src 'none'",
            ].join('; '),
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
