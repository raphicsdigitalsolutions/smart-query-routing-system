import 'server-only';

import { timingSafeEqual } from 'node:crypto';

export function csrfTokensMatch(expected: string | null | undefined, actual: string | null | undefined): boolean {
  if (!expected || !actual) return false;
  const left = Buffer.from(expected);
  const right = Buffer.from(actual);
  if (left.length !== right.length) return false;
  return timingSafeEqual(left, right);
}
