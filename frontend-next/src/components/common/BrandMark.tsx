import { cn } from '@/lib/utils';

interface BrandMarkProps {
  className?: string;
  iconClassName?: string;
  /** Size of the square mark in pixels. */
  size?: number;
  showWordmark?: boolean;
  /** Use a light mark on dark backgrounds. */
  inverted?: boolean;
  title?: string;
  subtitle?: string;
}

/**
 * Smart Query brand mark: a message bubble with a teal routing chevron.
 * Shared by the auth screens, application shell and error surfaces so the
 * identity stays consistent everywhere.
 */
export function BrandMark({
  className,
  iconClassName,
  size = 40,
  showWordmark = false,
  inverted = false,
  title = 'Smart Query',
  subtitle = 'University Communication Hub',
}: BrandMarkProps) {
  return (
    <span className={cn('inline-flex items-center gap-3', className)}>
      <span
        className={cn(
          'relative inline-flex shrink-0 items-center justify-center rounded-[11px] shadow-sm',
          inverted ? 'bg-white' : 'bg-navy-900',
          iconClassName,
        )}
        style={{ width: size, height: size }}
        aria-hidden="true"
      >
        <svg viewBox="0 0 64 64" className="h-[72%] w-[72%]" focusable="false">
          <path
            d="M14 19a6 6 0 0 1 6-6h24a6 6 0 0 1 6 6v18a6 6 0 0 1-6 6H29l-11 8v-8a6 6 0 0 1-4-5.6V19Z"
            fill={inverted ? '#102A43' : '#FFFFFF'}
          />
          <path
            d="M25 24.5 34.5 29 25 33.5"
            fill="none"
            stroke="#0D9488"
            strokeWidth="5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      {showWordmark ? (
        <span className="min-w-0 leading-tight">
          <span className={cn('block truncate text-sm font-semibold', inverted ? 'text-white' : 'text-navy-900')}>
            {title}
          </span>
          <span className={cn('block truncate text-[11px]', inverted ? 'text-teal-200' : 'text-slate-500')}>
            {subtitle}
          </span>
        </span>
      ) : null}
    </span>
  );
}
