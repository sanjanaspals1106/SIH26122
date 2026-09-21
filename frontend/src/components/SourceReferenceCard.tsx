import React from 'react';
import { cn } from '@/lib/utils';
import { FileText, ImageIcon, Hash } from 'lucide-react';
import { ExecutionEvent, SourceReference } from '@/api';

export interface SourceReferenceCardProps {
  event: ExecutionEvent;
  sourceReferences?: SourceReference[];
  className?: string;
}

export function SourceReferenceCard({
  event,
  sourceReferences = [],
  className,
}: SourceReferenceCardProps) {
  const hasDocId = Boolean(event.document_id);
  const hasPhoto = Boolean(event.photo_path);
  const hasRefs = sourceReferences.length > 0;

  // If completely devoid of source evidence metadata, render nothing to keep UX compact
  if (!hasDocId && !hasPhoto && !hasRefs) {
    return null;
  }

  return (
    <div
      className={cn(
        'p-3.5 rounded-xl bg-card-subtle border border-border space-y-2.5 text-xs',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-primary" />
          Source Evidence Context
        </span>
        <span className="text-[10px] font-mono text-muted-foreground">
          Coarse Provenance
        </span>
      </div>

      <div className="space-y-2">
        {hasDocId && (
          <div className="flex items-center justify-between text-[11px] bg-card p-2 rounded-lg border border-border/60">
            <span className="text-muted-foreground flex items-center gap-1">
              <Hash className="w-3 h-3 text-muted-foreground" />
              Source Document:
            </span>
            <span className="font-mono font-bold text-foreground">
              {event.document_id}
            </span>
          </div>
        )}

        {hasPhoto && (
          <div className="flex items-center justify-between text-[11px] bg-card p-2 rounded-lg border border-border/60">
            <span className="text-muted-foreground flex items-center gap-1">
              <ImageIcon className="w-3 h-3 text-accent" />
              Attached Photo:
            </span>
            <span className="font-mono text-accent truncate max-w-[200px]" title={event.photo_path || ''}>
              {event.photo_path?.split('/').pop()}
            </span>
          </div>
        )}

        {hasRefs && (
          <div className="space-y-1.5 pt-1">
            {sourceReferences.map((ref) => (
              <div
                key={ref.reference_id}
                className="p-2 bg-card rounded-lg border border-border/60 space-y-1 text-[11px]"
              >
                <div className="flex items-center justify-between font-mono text-[10px] text-muted-foreground">
                  <span className="font-bold text-primary">{ref.file_name || 'Source File'}</span>
                  {ref.sheet_name && <span>Sheet: {ref.sheet_name}</span>}
                  {ref.row_cell_ref && <span>Ref: {ref.row_cell_ref}</span>}
                </div>
                {ref.raw_snippet && (
                  <p
                    className="text-foreground/90 font-mono text-[10px] bg-muted/40 p-1.5 rounded border border-border/40 truncate"
                    title={ref.raw_snippet}
                  >
                    "{ref.raw_snippet}"
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
