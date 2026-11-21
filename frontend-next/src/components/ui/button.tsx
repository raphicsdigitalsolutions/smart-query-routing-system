'use client';

import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-all duration-150 disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600/40 focus-visible:ring-offset-2 active:scale-[0.985]',
  {
    variants: {
      variant: {
        primary: 'bg-navy-900 text-white shadow-sm hover:bg-navy-800 hover:shadow-md',
        teal: 'bg-teal-600 text-white shadow-sm hover:bg-teal-700 hover:shadow-md',
        outline: 'border border-slate-300 bg-white text-navy-800 shadow-sm hover:border-slate-400 hover:bg-slate-50',
        ghost: 'text-navy-700 hover:bg-slate-100 hover:text-navy-900',
        soft: 'bg-teal-50 text-teal-800 hover:bg-teal-100',
        danger: 'bg-rose-600 text-white shadow-sm hover:bg-rose-700',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
        lg: 'h-11 px-6',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: { variant: 'primary', size: 'default' },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, type, ...props }: ButtonProps) {
  const Component = asChild ? Slot : 'button';
  return (
    <Component
      className={cn(buttonVariants({ variant, size }), className)}
      type={asChild ? undefined : type ?? 'button'}
      {...props}
    />
  );
}

export { buttonVariants };
