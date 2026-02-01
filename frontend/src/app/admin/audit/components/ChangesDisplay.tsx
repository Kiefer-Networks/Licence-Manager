'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Plus, Minus, Edit2 } from 'lucide-react';
import { AuditLogChanges } from '@/lib/api';

interface ChangesDisplayProps {
  changes: AuditLogChanges | null | undefined;
  compact?: boolean;
}

type ChangeType = 'added' | 'removed' | 'changed' | 'unchanged';

interface ChangeEntry {
  field: string;
  oldValue: unknown;
  newValue: unknown;
  type: ChangeType;
}

function getChangeType(oldVal: unknown, newVal: unknown): ChangeType {
  if (oldVal === undefined || oldVal === null) return 'added';
  if (newVal === undefined || newVal === null) return 'removed';
  if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) return 'changed';
  return 'unchanged';
}

function formatValue(value: unknown): string {
  if (value === null) return 'null';
  if (value === undefined) return '-';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function truncateValue(value: string, maxLength: number = 50): string {
  if (value.length <= maxLength) return value;
  return value.slice(0, maxLength) + '...';
}

function extractChanges(changes: AuditLogChanges): ChangeEntry[] {
  const entries: ChangeEntry[] = [];

  // Handle "old" and "new" structure
  if (changes.old || changes.new) {
    const oldData = (changes.old || {}) as Record<string, unknown>;
    const newData = (changes.new || {}) as Record<string, unknown>;
    const allKeys = new Set([...Object.keys(oldData), ...Object.keys(newData)]);

    for (const key of allKeys) {
      const oldVal = oldData[key];
      const newVal = newData[key];
      const type = getChangeType(oldVal, newVal);

      if (type !== 'unchanged') {
        entries.push({ field: key, oldValue: oldVal, newValue: newVal, type });
      }
    }
  } else {
    // Handle flat structure (all fields are changed values)
    for (const [key, value] of Object.entries(changes)) {
      if (key !== 'old' && key !== 'new') {
        entries.push({ field: key, oldValue: undefined, newValue: value, type: 'changed' });
      }
    }
  }

  return entries;
}

function ChangeIcon({ type }: { type: ChangeType }) {
  switch (type) {
    case 'added':
      return <Plus className="h-3.5 w-3.5 text-emerald-600" />;
    case 'removed':
      return <Minus className="h-3.5 w-3.5 text-red-600" />;
    case 'changed':
      return <Edit2 className="h-3.5 w-3.5 text-amber-600" />;
    default:
      return null;
  }
}

function getTypeBgColor(type: ChangeType): string {
  switch (type) {
    case 'added':
      return 'bg-emerald-50';
    case 'removed':
      return 'bg-red-50';
    case 'changed':
      return 'bg-amber-50';
    default:
      return '';
  }
}

export function ChangesDisplay({ changes, compact = false }: ChangesDisplayProps) {
  const t = useTranslations('audit');
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());

  if (!changes || Object.keys(changes).length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        {t('noChanges')}
      </p>
    );
  }

  const changeEntries = extractChanges(changes);

  if (changeEntries.length === 0) {
    // No old/new structure, just show raw data
    return (
      <div className="bg-zinc-50 rounded-lg p-3 overflow-auto max-h-64">
        <pre className="text-xs font-mono whitespace-pre-wrap">
          {JSON.stringify(changes, null, 2)}
        </pre>
      </div>
    );
  }

  const toggleField = (field: string) => {
    const newExpanded = new Set(expandedFields);
    if (newExpanded.has(field)) {
      newExpanded.delete(field);
    } else {
      newExpanded.add(field);
    }
    setExpandedFields(newExpanded);
  };

  if (compact) {
    // Compact view for table summary
    const summary = changeEntries.slice(0, 3).map(e => e.field).join(', ');
    const more = changeEntries.length > 3 ? ` +${changeEntries.length - 3}` : '';
    return (
      <span className="text-sm text-muted-foreground">
        {summary}{more}
      </span>
    );
  }

  return (
    <div className="space-y-1">
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-zinc-100 text-left">
              <th className="px-3 py-2 font-medium w-8"></th>
              <th className="px-3 py-2 font-medium">{t('field')}</th>
              <th className="px-3 py-2 font-medium">{t('before')}</th>
              <th className="px-3 py-2 font-medium">{t('after')}</th>
            </tr>
          </thead>
          <tbody>
            {changeEntries.map((entry) => {
              const oldFormatted = formatValue(entry.oldValue);
              const newFormatted = formatValue(entry.newValue);
              const isLong = oldFormatted.length > 50 || newFormatted.length > 50;
              const isExpanded = expandedFields.has(entry.field);

              return (
                <tr key={entry.field} className={`border-t ${getTypeBgColor(entry.type)}`}>
                  <td className="px-3 py-2">
                    <ChangeIcon type={entry.type} />
                  </td>
                  <td className="px-3 py-2 font-mono text-xs font-medium">
                    {entry.field}
                    {isLong && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 ml-1"
                        onClick={() => toggleField(entry.field)}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                      </Button>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-red-700">
                    {entry.type === 'added' ? (
                      <span className="text-zinc-400">-</span>
                    ) : isExpanded ? (
                      <pre className="whitespace-pre-wrap break-all">{oldFormatted}</pre>
                    ) : (
                      truncateValue(oldFormatted)
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-emerald-700">
                    {entry.type === 'removed' ? (
                      <span className="text-zinc-400">-</span>
                    ) : isExpanded ? (
                      <pre className="whitespace-pre-wrap break-all">{newFormatted}</pre>
                    ) : (
                      truncateValue(newFormatted)
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
