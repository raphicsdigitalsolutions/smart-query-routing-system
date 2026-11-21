import type { Metadata, Viewport } from 'next';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { getCurrentUser } from '@/lib/auth/session';
import { AppProviders } from '@/components/providers/AppProviders';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Smart Query — University Communication Hub',
    template: '%s · Smart Query',
  },
  description:
    'Smart Query routes university enquiries to the right department and staff member, with an auditable ticket workflow and staff-only AI assistance.',
  applicationName: 'Smart Query Routing System',
  keywords: ['university', 'query routing', 'ticket management', 'communication hub'],
  icons: {
    icon: [{ url: '/favicon.svg', type: 'image/svg+xml' }],
    shortcut: '/favicon.svg',
    apple: '/favicon.svg',
  },
};

export const viewport: Viewport = {
  themeColor: '#102A43',
  width: 'device-width',
  initialScale: 1,
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const initialUser = await getCurrentUser();

  return (
    <html lang="en">
      <body>
        <AppRouterCacheProvider options={{ enableCssLayer: true }}>
          <AppProviders initialUser={initialUser}>{children}</AppProviders>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
