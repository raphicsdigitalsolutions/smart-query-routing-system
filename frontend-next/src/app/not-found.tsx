import Link from 'next/link';
import { Compass } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4">
      <Card className="w-full p-8 text-center">
        <Compass className="mx-auto h-10 w-10 text-teal-700" aria-hidden="true" />
        <p className="mt-4 text-sm font-semibold text-teal-700">404</p>
        <h1 className="mt-1 text-2xl font-semibold text-navy-900">Page not found</h1>
        <p className="mt-2 text-sm text-slate-500">The page you requested does not exist.</p>
        <Button asChild className="mt-6"><Link href="/dashboard">Go to overview</Link></Button>
      </Card>
    </div>
  );
}
