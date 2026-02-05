'use client';

import { useTranslations } from 'next-intl';
import { AlertCircle, X } from 'lucide-react';

interface ErrorAlertProps {
  message: string | string[];
  onDismiss?: () => void;
  className?: string;
}

export function ErrorAlert({ message, onDismiss, className = '' }: ErrorAlertProps) {
  const tCommon = useTranslations('common');
  const messages = Array.isArray(message) ? message : [message];

  if (messages.length === 0 || messages.every(m => !m)) {
    return null;
  }

  return (
    <div className={`bg-destructive/10 text-destructive text-sm p-3 rounded-md flex items-start gap-2 ${className}`}>
      <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
      <div className="flex-1">
        {messages.map((msg, i) => (
          <div key={i}>{msg}</div>
        ))}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-destructive hover:text-destructive/80 flex-shrink-0"
          aria-label={tCommon('close')}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
