import React, { useEffect, useState } from 'react';
import {
  FileText,
  Image,
  MapPin,
  Clock,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Search,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { EvidenceDocument, claimsApi } from '../api';

interface EvidencePanelProps {
  eventId: string;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ eventId }) => {
  const [evidenceList, setEvidenceList] = useState<EvidenceDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchEvidence = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await claimsApi.getEvidence(eventId);
      setEvidenceList(docs || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load evidence records');
      setEvidenceList([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, [eventId]);

  const filteredDocs = evidenceList.filter((doc) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      doc.file_name.toLowerCase().includes(q) ||
      doc.document_type.toLowerCase().includes(q) ||
      (doc.snippet_text && doc.snippet_text.toLowerCase().includes(q)) ||
      (doc.page_or_cell_ref && doc.page_or_cell_ref.toLowerCase().includes(q))
    );
  });

  const getDocTypeIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'INSPECTION_PHOTO':
      case 'PHOTO':
      case 'IMAGE':
        return <Image className="w-4 h-4 text-emerald-500" />;
      default:
        return <FileText className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-xs text-foreground">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-teal-50 dark:bg-[#0A2340] text-[#14B8A6] dark:text-[#22D3EE] border border-teal-200 dark:border-[#1E3A5F]">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              Multi-Source Evidence Fusion
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-900/60">
                {evidenceList.length} {evidenceList.length === 1 ? 'Source' : 'Sources'}
              </span>
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Corroborating shift reports, site photos, QC inspection logs, and spatial telemetry.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Search filter */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] text-slate-900 dark:text-[#F5F7FA] placeholder:text-slate-400 dark:placeholder:text-[#94A8B8] focus:outline-hidden focus:ring-1 focus:ring-[#FF7A18]"
            />
          </div>
          <button
            type="button"
            onClick={fetchEvidence}
            disabled={loading}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors"
            title="Refresh Evidence"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Body */}
      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center text-muted-foreground">
          <RefreshCw className="w-6 h-6 animate-spin mb-2 text-[#14B8A6] dark:text-[#22D3EE]" />
          <p className="text-xs">Fusing multi-source evidence...</p>
        </div>
      ) : error ? (
        <div className="my-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Evidence Service Unavailable</p>
            <p className="mt-0.5 text-amber-700 dark:text-amber-400">{error}</p>
          </div>
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="py-8 text-center text-muted-foreground">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-xs font-medium">No fine-grained evidence records found</p>
          <p className="text-[11px] mt-0.5">
            {searchQuery
              ? 'No documents match your filter criteria.'
              : 'Direct claim text is available; auxiliary multi-source artifacts have not been linked yet.'}
          </p>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {filteredDocs.map((doc) => (
            <div
              key={doc.evidence_id}
              className="p-3.5 rounded-xl border border-border bg-card-subtle hover:border-primary/40 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-card border border-border shadow-2xs">
                      {getDocTypeIcon(doc.document_type)}
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-foreground truncate max-w-[200px]" title={doc.file_name}>
                        {doc.file_name}
                      </h4>
                      <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">
                        {doc.document_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    {doc.relation && (
                      <span
                        className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                          doc.relation.toUpperCase() === 'CORROBORATES'
                            ? 'bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900/60'
                            : doc.relation.toUpperCase() === 'CONTRADICTS'
                            ? 'bg-rose-100 dark:bg-rose-950/70 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-900/60'
                            : 'bg-secondary text-secondary-foreground border border-border'
                        }`}
                      >
                        {doc.relation.toUpperCase() === 'CORROBORATES'
                          ? '✓ Corroborates'
                          : doc.relation.toUpperCase() === 'CONTRADICTS'
                          ? '⚠ Contradicts'
                          : doc.relation}
                      </span>
                    )}
                    {doc.ocr_confidence != null && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200/50 dark:border-emerald-800/50">
                        <CheckCircle2 className="w-3 h-3" />
                        {Math.round(doc.ocr_confidence * 100)}%
                      </span>
                    )}
                  </div>
                </div>

                {doc.page_or_cell_ref && (
                  <div className="mb-2 text-[11px] text-muted-foreground flex items-center gap-1">
                    <span className="font-medium text-foreground">Reference:</span> {doc.page_or_cell_ref}
                  </div>
                )}

                {doc.snippet_text && (
                  <blockquote className="text-xs text-foreground/90 italic bg-card p-2.5 rounded-lg border-l-2 border-[#1565C0] dark:border-blue-400 mb-2">
                    &ldquo;{doc.snippet_text}&rdquo;
                  </blockquote>
                )}
              </div>

              <div className="pt-2 border-t border-border/60 flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted-foreground">
                <div className="flex items-center gap-3">
                  {(doc.gps_lat != null && doc.gps_lon != null) && (
                    <span className="inline-flex items-center gap-1 font-mono">
                      <MapPin className="w-3 h-3 text-red-500" />
                      {doc.gps_lat.toFixed(4)}, {doc.gps_lon.toFixed(4)}
                    </span>
                  )}
                  {doc.timestamp && (
                    <span className="inline-flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(doc.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                </div>

                {doc.source_url && (
                  <a
                    href={doc.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[#1565C0] dark:text-blue-400 hover:underline font-medium"
                  >
                    View Original <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
