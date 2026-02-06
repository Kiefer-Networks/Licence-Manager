'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { Input } from './input';
import { Check, ChevronsUpDown, X, User } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface EmployeeOption {
  id: string;
  full_name: string;
  email: string;
  avatar?: string;
}

interface EmployeeAutocompleteProps {
  employees: EmployeeOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  noOwnerLabel?: string;
  allowNone?: boolean;
  disabled?: boolean;
}

export function EmployeeAutocomplete({
  employees,
  value,
  onChange,
  placeholder,
  noOwnerLabel,
  allowNone = true,
  disabled = false,
}: EmployeeAutocompleteProps) {
  const t = useTranslations('common');
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  // Find selected employee
  const selectedEmployee = useMemo(() =>
    employees.find(emp => emp.id === value),
    [employees, value]
  );

  // Filter employees based on search
  const filteredEmployees = useMemo(() => {
    if (!search) return employees;
    const searchLower = search.toLowerCase();
    return employees.filter(emp =>
      emp.full_name.toLowerCase().includes(searchLower) ||
      emp.email.toLowerCase().includes(searchLower)
    );
  }, [employees, search]);

  // Build options list with "no owner" option
  const options = useMemo(() => {
    const list: Array<{ id: string; label: string; email?: string; isNone?: boolean }> = [];
    if (allowNone) {
      list.push({ id: '', label: noOwnerLabel || t('noOwner'), isNone: true });
    }
    filteredEmployees.forEach(emp => {
      list.push({ id: emp.id, label: emp.full_name, email: emp.email });
    });
    return list;
  }, [allowNone, noOwnerLabel, t, filteredEmployees]);

  // Reset highlighted index when options change
  useEffect(() => {
    setHighlightedIndex(0);
  }, [options.length]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (open && listRef.current) {
      const highlighted = listRef.current.querySelector('[data-highlighted="true"]');
      if (highlighted) {
        highlighted.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex, open]);

  const handleSelect = (id: string) => {
    onChange(id);
    setOpen(false);
    setSearch('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => Math.min(prev + 1, options.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (options[highlightedIndex]) {
          handleSelect(options[highlightedIndex].id);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setOpen(false);
        setSearch('');
        break;
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange('');
    setSearch('');
    inputRef.current?.focus();
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Input
          ref={inputRef}
          value={open ? search : (selectedEmployee ? `${selectedEmployee.full_name} (${selectedEmployee.email})` : '')}
          onChange={(e) => {
            setSearch(e.target.value);
            if (!open) setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || t('searchEmployee')}
          disabled={disabled}
          className="pr-16"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {value && !disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 hover:bg-muted rounded"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          )}
          <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>

      {open && (
        <div
          ref={listRef}
          className="absolute z-50 mt-1 w-full bg-popover border rounded-md shadow-lg max-h-60 overflow-auto"
        >
          {options.length === 0 ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              {t('noResults')}
            </div>
          ) : (
            options.map((option, index) => (
              <div
                key={option.id || '__none__'}
                data-highlighted={index === highlightedIndex}
                onClick={() => handleSelect(option.id)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 cursor-pointer text-sm',
                  index === highlightedIndex && 'bg-accent',
                  value === option.id && 'bg-muted/50'
                )}
                onMouseEnter={() => setHighlightedIndex(index)}
              >
                {option.isNone ? (
                  <>
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">{option.label}</span>
                  </>
                ) : (
                  <>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{option.label}</div>
                      {option.email && (
                        <div className="text-xs text-muted-foreground truncate">{option.email}</div>
                      )}
                    </div>
                  </>
                )}
                {value === option.id && (
                  <Check className="h-4 w-4 text-foreground ml-auto flex-shrink-0" />
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
