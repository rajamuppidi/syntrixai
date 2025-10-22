'use client';

import { getStatusColor, getStatusIcon } from '../lib/utils';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  const safeStatus = status || 'pending';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${getStatusColor(safeStatus)} ${sizeClasses[size]}`}
    >
      <span className="text-base">{getStatusIcon(safeStatus)}</span>
      <span className="capitalize">{safeStatus}</span>
    </span>
  );
}

