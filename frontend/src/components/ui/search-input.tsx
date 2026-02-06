'use client';

import { useTranslations } from 'next-intl';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  onSearch?: () => void;
  placeholder?: string;
  showButtons?: boolean;
  onClear?: () => void;
  className?: string;
  autoFocus?: boolean;
}

export function SearchInput({
  value,
  onChange,
  onSearch,
  placeholder,
  showButtons = false,
  onClear,
  className = '',
  autoFocus = false,
}: SearchInputProps) {
  const tCommon = useTranslations('common');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onSearch) {
      onSearch();
    }
  };

  const handleClear = () => {
    onChange('');
    if (onClear) {
      onClear();
    }
  };

  if (showButtons) {
    return (
      <div className={`flex gap-2 ${className}`}>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={placeholder || tCommon('search')}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-9 h-9 bg-muted/50 border-input"
            autoFocus={autoFocus}
          />
        </div>
        {onSearch && (
          <Button variant="outline" size="sm" onClick={onSearch}>
            {tCommon('search')}
          </Button>
        )}
        {value && (
          <Button variant="ghost" size="sm" onClick={handleClear}>
            {tCommon('clear')}
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder={placeholder || tCommon('search')}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        className="pl-9 h-9 bg-muted/50 border-input pr-8"
        autoFocus={autoFocus}
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
