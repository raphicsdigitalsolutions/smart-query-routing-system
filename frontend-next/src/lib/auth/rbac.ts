import type { Role, UserResponse } from '@/lib/api/types';

export function hasRole(user: UserResponse | null, roles: readonly Role[]): boolean {
  return Boolean(user && roles.includes(user.role));
}

export function normalizeRole(value: string | null | undefined): Role | null {
  if (value === 'student' || value === 'staff' || value === 'hod' || value === 'admin') return value;
  return null;
}
