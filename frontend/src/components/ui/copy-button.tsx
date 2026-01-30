'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Button } from './button';
import { cn } from '@/lib/utils';

interface CopyButtonProps {
  value: string;
  className?: string;
  size?: 'default' | 'sm' | 'icon';
  variant?: 'default' | 'ghost' | 'outline';
  showText?: boolean;
}

export function CopyButton({
  value,
  className,
  size = 'icon',
  variant = 'ghost',
  showText = false,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = value;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      onClick={handleCopy}
      className={cn(
        size === 'icon' && 'h-7 w-7',
        copied && 'text-emerald-600',
        className
      )}
      title={copied ? 'Copied!' : 'Copy to clipboard'}
    >
      {copied ? (
        <Check className="h-3.5 w-3.5" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
      {showText && <span className="ml-1.5">{copied ? 'Copied' : 'Copy'}</span>}
    </Button>
  );
}

// Inline version for use within text
export function CopyableText({
  children,
  value,
  className,
}: {
  children: React.ReactNode;
  value?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const textToCopy = value || (typeof children === 'string' ? children : '');
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Silent fail
    }
  };

  return (
    <span
      onClick={handleCopy}
      className={cn(
        'cursor-pointer hover:bg-zinc-100 rounded px-1 -mx-1 inline-flex items-center gap-1 transition-colors',
        copied && 'bg-emerald-50 text-emerald-700',
        className
      )}
      title={copied ? 'Copied!' : 'Click to copy'}
    >
      {children}
      {copied && <Check className="h-3 w-3" />}
    </span>
  );
}
