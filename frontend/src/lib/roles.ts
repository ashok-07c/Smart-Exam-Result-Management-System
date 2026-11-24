import type { Role } from './types';

/** Landing page for each of the three supported roles. */
export function homeForRole(role: Role): string {
  if (role === 'EXAM_ADMIN') return '/admin/dashboard';
  if (role === 'FACULTY') return '/faculty/dashboard';
  return '/student/dashboard';
}
