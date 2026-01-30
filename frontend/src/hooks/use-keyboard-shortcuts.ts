'use client';

import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  callback: () => void;
  description: string;
}

const defaultShortcuts: ShortcutConfig[] = [
  { key: 'd', alt: true, callback: () => {}, description: 'Go to Dashboard' },
  { key: 'l', alt: true, callback: () => {}, description: 'Go to Licenses' },
  { key: 'u', alt: true, callback: () => {}, description: 'Go to Users' },
  { key: 'p', alt: true, callback: () => {}, description: 'Go to Providers' },
  { key: 'r', alt: true, callback: () => {}, description: 'Go to Reports' },
  { key: 's', alt: true, callback: () => {}, description: 'Go to Settings' },
  { key: 'k', ctrl: true, callback: () => {}, description: 'Open Quick Search' },
];

/**
 * Hook for handling keyboard shortcuts.
 * Returns a function to register additional shortcuts.
 */
export function useKeyboardShortcuts(additionalShortcuts: ShortcutConfig[] = []) {
  const router = useRouter();

  // Navigation shortcuts
  const navigationShortcuts: ShortcutConfig[] = [
    { key: 'd', alt: true, callback: () => router.push('/dashboard'), description: 'Go to Dashboard' },
    { key: 'l', alt: true, callback: () => router.push('/licenses'), description: 'Go to Licenses' },
    { key: 'u', alt: true, callback: () => router.push('/users'), description: 'Go to Users' },
    { key: 'p', alt: true, callback: () => router.push('/providers'), description: 'Go to Providers' },
    { key: 'r', alt: true, callback: () => router.push('/reports'), description: 'Go to Reports' },
    { key: 's', alt: true, callback: () => router.push('/settings'), description: 'Go to Settings' },
  ];

  const allShortcuts = [...navigationShortcuts, ...additionalShortcuts];

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.contentEditable === 'true'
      ) {
        return;
      }

      for (const shortcut of allShortcuts) {
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();

        if (ctrlMatch && altMatch && shiftMatch && keyMatch) {
          event.preventDefault();
          shortcut.callback();
          return;
        }
      }
    },
    [allShortcuts]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return {
    shortcuts: allShortcuts,
  };
}

/**
 * Get shortcut key display string (e.g., "Alt+D")
 */
export function getShortcutDisplay(shortcut: ShortcutConfig): string {
  const parts: string[] = [];
  if (shortcut.ctrl) parts.push('Ctrl');
  if (shortcut.alt) parts.push('Alt');
  if (shortcut.shift) parts.push('Shift');
  parts.push(shortcut.key.toUpperCase());
  return parts.join('+');
}
