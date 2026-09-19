import React from 'react';
import { cn } from '@/lib/utils';

export type ClaimStatus = 
  | 'EXTRACTED' 
  | 'MATCHED' 
  | 'REVIEW_REQUIRED' 
  | 'VALIDATED' 
  | 'APPROVED' 
  | 'EDITED' 
  | 'REJECTED' 
  | 'HOLD' 
  | 'UNMATCHED';

const statusConfig: Record<ClaimStatus, { borderClass: string; textClass: string; bgClass: string; label: string }> = {
  EXTRACTED: { borderClass: 'border-l-status-extracted', textClass: 'text-status-extracted', bgClass: 'bg-status-extracted/10', label: 'Extracted' },
  MATCHED: { borderClass: 'border-l-status-extracted', textClass: 'text-status-extracted', bgClass: 'bg-status-extracted/10', label: 'Matched' },
  UNMATCHED: { borderClass: 'border-l-status-review', textClass: 'text-status-review', bgClass: 'bg-status-review/10', label: 'Unmatched' },
  REVIEW_REQUIRED: { borderClass: 'border-l-status-review', textClass: 'text-status-review', bgClass: 'bg-status-review/10', label: 'Review Required' },
  VALIDATED: { borderClass: 'border-l-status-validated', textClass: 'text-status-validated', bgClass: 'bg-status-validated/10', label: 'Validated' },
  APPROVED: { borderClass: 'border-l-status-approved', textClass: 'text-status-approved', bgClass: 'bg-status-approved/10', label: 'Approved' },
  EDITED: { borderClass: 'border-l-status-approved', textClass: 'text-status-approved', bgClass: 'bg-status-approved/10', label: 'Edited' },
  REJECTED: { borderClass: 'border-l-status-rejected', textClass: 'text-status-rejected', bgClass: 'bg-status-rejected/10', label: 'Rejected' },
  HOLD: { borderClass: 'border-l-status-review border-dashed', textClass: 'text-status-review', bgClass: 'bg-status-review/10', label: 'On Hold' },
};

export const getStatusConfig = (status: ClaimStatus) => statusConfig[status] || statusConfig['EXTRACTED'];

interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: ClaimStatus;
  variant?: 'left-border' | 'badge' | 'dot';
}

export function StatusBadge({ status, className, variant = 'badge', children, ...props }: StatusBadgeProps) {
  const config = getStatusConfig(status);
  
  if (variant === 'badge') {
    return (
      <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', config.bgClass, config.textClass, className)} {...props}>
        {config.label}
      </span>
    );
  }

  if (variant === 'dot') {
    return (
      <span className={cn('flex items-center gap-1.5', className)} {...props}>
        <span className={cn('h-2 w-2 rounded-full', config.bgClass.replace('/10', ''))} />
        <span className={cn('text-sm font-medium', config.textClass)}>{config.label}</span>
      </span>
    );
  }

  // default left-border treatment for rows/cards
  return (
    <div className={cn('pl-3 border-l-4 py-0.5', config.borderClass, className)} {...props}>
      {children || <span className={cn("text-sm font-medium", config.textClass)}>{config.label}</span>}
    </div>
  );
}
