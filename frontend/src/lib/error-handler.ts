/**
 * Safe error handling utilities to prevent information disclosure.
 * Errors are logged without sensitive details in production.
 */

/**
 * Sanitize an error for safe display/logging.
 * Removes potentially sensitive information like stack traces, URLs, tokens.
 */
export function sanitizeError(error: unknown): string {
  if (error instanceof Error) {
    // Return only the message, not the stack trace
    const message = error.message;

    // Remove any potential sensitive data patterns
    const sanitized = message
      .replace(/Bearer\s+[A-Za-z0-9\-_]+/gi, '[TOKEN]')
      .replace(/token[=:]\s*[A-Za-z0-9\-_]+/gi, 'token=[REDACTED]')
      .replace(/password[=:]\s*\S+/gi, 'password=[REDACTED]')
      .replace(/api[_-]?key[=:]\s*\S+/gi, 'api_key=[REDACTED]')
      .replace(/https?:\/\/[^\s]+/gi, '[URL]');

    return sanitized;
  }

  if (typeof error === 'string') {
    return error;
  }

  return 'An unexpected error occurred';
}

/**
 * Safe error logger that doesn't expose sensitive information.
 * In development, logs more details for debugging.
 * In production, logs minimal information.
 */
export function logError(context: string, error: unknown): void {
  // Only log errors in development to avoid information disclosure in browser console
  // In production, errors should be sent to a proper logging service (e.g., Sentry)
  if (process.env.NODE_ENV === 'development') {
    console.error(`[${context}]`, error);
  }
  // Production: Silent - use error tracking service integration instead
}

/**
 * Handle API errors safely.
 * Returns a user-friendly message without sensitive details.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    // Known safe error messages from our API
    const safePatterns = [
      'Invalid credentials',
      'Authentication required',
      'Access denied',
      'Session expired',
      'not found',
      'already exists',
      'Invalid input',
      'Request failed',
      'Network error',
    ];

    const message = error.message.toLowerCase();
    for (const pattern of safePatterns) {
      if (message.includes(pattern.toLowerCase())) {
        return error.message;
      }
    }

    // For unknown errors, return generic message
    return 'An error occurred. Please try again.';
  }

  return 'An unexpected error occurred';
}

/**
 * Silent error handler - logs in dev, silent in prod.
 * Use for non-critical errors that shouldn't interrupt user flow.
 */
export function handleSilentError(context: string, error: unknown): void {
  if (process.env.NODE_ENV === 'development') {
    console.error(`[${context}]`, error);
  }
  // In production, errors are silently ignored
  // They should be sent to a logging service instead
}
