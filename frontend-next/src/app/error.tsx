'use client';

import { useEffect } from 'react';
import { ErrorState } from '@/components/common/ErrorState';

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-screen max-w-xl items-center px-4">
      <ErrorState title="Page could not be loaded" message={error.message} onRetry={reset} className="w-full" />
    </div>
  );
}
