'use client';

import { ChevronDown, RotateCcw, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  EMPTY_TICKET_FILTERS,
  TICKET_PRIORITIES,
  TICKET_STATUSES,
  type TicketFilters as TicketFiltersValue,
} from '@/lib/api/types';
import { prettyLabel } from '@/lib/utils';

interface TicketFiltersProps {
  value: TicketFiltersValue;
  onChange: (next: TicketFiltersValue) => void;
}

interface SelectFilterProps {
  label: string;
  value: string;
  placeholder: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}

function SelectFilter({ label, value, placeholder, options, onChange }: SelectFilterProps) {
  return (
    <label className="block min-w-0">
      <span className="field-label">{label}</span>
      <span className="relative block">
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="field-input appearance-none pr-9"
        >
          <option value="">{placeholder}</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
      </span>
    </label>
  );
}

export function TicketFilters({ value, onChange }: TicketFiltersProps) {
  const hasFilters = Object.values(value).some(Boolean);

  return (
    <div className="surface-card p-4 sm:p-5">
      <form onSubmit={(event) => event.preventDefault()} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <label className="block min-w-0">
          <span className="field-label">Search</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              type="search"
              value={value.search}
              onChange={(event) => onChange({ ...value, search: event.target.value })}
              placeholder="Subject or description"
              className="field-input field-input-with-icon"
            />
          </span>
        </label>

        <SelectFilter
          label="Status"
          value={value.status}
          placeholder="All statuses"
          options={TICKET_STATUSES.map((status) => ({ value: status, label: prettyLabel(status) }))}
          onChange={(status) => onChange({ ...value, status: status as TicketFiltersValue['status'] })}
        />

        <SelectFilter
          label="Priority"
          value={value.priority}
          placeholder="All priorities"
          options={TICKET_PRIORITIES.map((priority) => ({ value: priority, label: prettyLabel(priority) }))}
          onChange={(priority) => onChange({ ...value, priority: priority as TicketFiltersValue['priority'] })}
        />

        <SelectFilter
          label="Escalated"
          value={value.escalated}
          placeholder="All"
          options={[
            { value: 'true', label: 'Yes' },
            { value: 'false', label: 'No' },
          ]}
          onChange={(escalated) => onChange({ ...value, escalated: escalated as TicketFiltersValue['escalated'] })}
        />

        <div className="flex items-end">
          <Button type="button" variant="outline" className="w-full" disabled={!hasFilters} onClick={() => onChange({ ...EMPTY_TICKET_FILTERS })}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Clear filters
          </Button>
        </div>
      </form>
    </div>
  );
}
