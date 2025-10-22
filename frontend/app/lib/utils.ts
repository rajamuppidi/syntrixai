import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(dateString: string): string {
  if (!dateString) return 'N/A';
  
  try {
    const date = new Date(dateString.replace('Z', '+00:00'));
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString || 'N/A';
  }
}

export function getStatusColor(status: string): string {
  const safeStatus = (status || 'pending').toLowerCase();
  
  switch (safeStatus) {
    case 'approved':
      return 'text-emerald-600 bg-emerald-50 border-emerald-200';
    case 'denied':
      return 'text-red-600 bg-red-50 border-red-200';
    case 'pending':
    case 'processing':
      return 'text-amber-600 bg-amber-50 border-amber-200';
    case 'extracted':
      return 'text-blue-600 bg-blue-50 border-blue-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
}

export function getStatusIcon(status: string): string {
  const safeStatus = (status || 'pending').toLowerCase();
  
  switch (safeStatus) {
    case 'approved':
      return '✓';
    case 'denied':
      return '✕';
    case 'pending':
    case 'processing':
      return '⏳';
    case 'extracted':
      return '📋';
    default:
      return '•';
  }
}

export function truncateId(id: string, length: number = 8): string {
  return id.substring(0, length);
}

export function formatAuthNumber(authNumber?: string): string {
  return authNumber || 'N/A';
}

