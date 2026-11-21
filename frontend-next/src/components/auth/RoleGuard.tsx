'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';
import { ShieldAlert } from 'lucide-react';
import { LoadingScreen } from '@/components/common/LoadingScreen';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { Role } from '@/lib/api/types';
import { useSession } from '@/hooks/useSession';

interface RoleGuardProps {
  roles: Role[];
  children: ReactNode;
}

export function RoleGuard({ roles, children }: RoleGuardProps) {
  const { status, hasRole } = useSession();

  if (status === 'loading') return <LoadingScreen fullScreen={false} />;
  if (!hasRole(...roles)) {
    return (
      <Card className="border-rose-200 bg-rose-50 p-6">
        <div className="flex gap-4">
          <ShieldAlert className="h-6 w-6 shrink-0 text-rose-600" aria-hidden="true" />
          <div>
            <h2 className="text-lg font-semibold text-rose-900">Access restricted</h2>
            <p className="mt-1 text-sm text-rose-700">
              Your role does not have access to this view. Backend authorization remains the final authority.
            </p>
            <Button asChild variant="outline" size="sm" className="mt-4">
              <Link href="/dashboard">Back to overview</Link>
            </Button>
          </div>
        </div>
      </Card>
    );
  }
  return <>{children}</>;
}
