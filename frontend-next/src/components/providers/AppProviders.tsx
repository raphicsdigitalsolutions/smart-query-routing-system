'use client';

import type { ReactNode } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { Toaster } from 'sonner';
import { muiTheme } from '@/theme/muiTheme';
import type { UserResponse } from '@/lib/api/types';
import { SessionProvider } from './SessionProvider';

interface AppProvidersProps {
  children: ReactNode;
  initialUser?: UserResponse | null;
}

export function AppProviders({ children, initialUser }: AppProvidersProps) {
  return (
    <ThemeProvider theme={muiTheme}>
      <SessionProvider initialUser={initialUser}>
        {children}
        <Toaster
          position="top-right"
          richColors
          closeButton
          toastOptions={{
            classNames: {
              toast: '!rounded-xl !border-slate-200 !shadow-lg',
            },
          }}
        />
      </SessionProvider>
    </ThemeProvider>
  );
}
