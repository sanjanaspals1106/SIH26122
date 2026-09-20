import React, { useEffect, useState, useMemo } from 'react';
import {
  Network,
  List,
  Eye,
  RefreshCw,
  AlertCircle,
  Info,
  Maximize2,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { KnowledgeGraphData, claimsApi } from '../api';

interface KnowledgeGraphProps {
  eventId: string;
}

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({ eventId }) => {
  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  const fetchGraph = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await claimsApi.getKnowledgeGraph(eventId);
      setGraphData(data);
      if (data?.nodes?.length) {
        setSelectedNodeId(data.nodes[0].id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch knowledge graph');
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [eventId]);

  const getNodeColor = (type: string) => {
    switch (type.toUpperCase()) {
      case 'CLAIM':
        return { bg: '#FF7A18', border: '#E06810', text: '#ffffff', badgeBg: 'bg-orange-100 dark:bg-orange-950/60', badgeText: 'text-orange-800 dark:text-orange-300' };
      case 'ACTIVITY':
        return { bg: '#10b981', border: '#059669', text: '#ffffff', badgeBg: 'bg-emerald-100 dark:bg-emerald-950/60', badgeText: 'text-emerald-800 dark:text-emerald-300' };
      case 'WBS':
        return { bg: '#f59e0b', border: '#d97706', text: '#ffffff', badgeBg: 'bg-amber-100 dark:bg-amber-950/60', badgeText: 'text-amber-800 dark:text-amber-300' };
      case 'DOCUMENT':
        return { bg: '#14B8A6', border: '#0F766E', text: '#ffffff', badgeBg: 'bg-teal-100 dark:bg-teal-950/60', badgeText: 'text-teal-800 dark:text-teal-300' };
      case 'LOCATION':
        return { bg: '#22D3EE', border: '#0284C7', text: '#061526', badgeBg: 'bg-cyan-100 dark:bg-cyan-950/60', badgeText: 'text-cyan-800 dark:text-cyan-300' };
      default:
        return { bg: '#0A2340', border: '#1E3A5F', text: '#ffffff', badgeBg: 'bg-slate-100 dark:bg-slate-800', badgeText: 'text-slate-800 dark:text-slate-200' };
    }
  };

  // Compute 2D node coordinates in SVG space (circular / hierarchical layout)
  const nodeLayout = useMemo(() => {
    if (!graphData?.nodes?.length) return new Map<string, { x: number; y: number }>();
    const map = new Map<string, { x: number; y: number }>();
    const nodes = graphData.nodes;

    // Center node is typically the claim node
    const claimNode = nodes.find((n) => n.type.toUpperCase() === 'CLAIM') || nodes[0];
    map.set(claimNode.id, { x: 300, y: 180 });

    const outerNodes = nodes.filter((n) => n.id !== claimNode.id);
    const radius = 140;
    outerNodes.forEach((node, i) => {
      const angle = (i / outerNodes.length) * 2 * Math.PI - Math.PI / 2;
      map.set(node.id, {
        x: 300 + radius * Math.cos(angle),
        y: 180 + radius * Math.sin(angle),
      });
    });

    return map;
  }, [graphData]);

  const selectedNode = useMemo(() => {
    return graphData?.nodes?.find((n) => n.id === selectedNodeId) || null;
  }, [graphData, selectedNodeId]);

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-teal-50 dark:bg-[#0A2340] text-[#14B8A6] dark:text-[#22D3EE] border border-teal-200 dark:border-[#1E3A5F]">
            <Network className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              Construction Knowledge Graph
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300">
                Cross-Entity Reasoning
              </span>
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Multi-hop graph relationships linking physical claims, WBS nodes, and audit trails.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Mode Switcher */}
          <div className="flex items-center bg-card-subtle p-1 rounded-lg border border-border">
            <button
              type="button"
              onClick={() => setViewMode('graph')}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                viewMode === 'graph'
                  ? 'bg-card text-[#1565C0] dark:text-blue-300 shadow-xs border border-border'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Graph View
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                viewMode === 'list'
                  ? 'bg-card text-[#1565C0] dark:text-blue-300 shadow-xs border border-border'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              Accessible List
            </button>
          </div>

          <button
            type="button"
            onClick={fetchGraph}
            disabled={loading}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-card-subtle transition-colors"
            title="Reload Graph"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Body */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center text-muted-foreground">
          <RefreshCw className="w-7 h-7 animate-spin mb-2 text-[#1565C0]" />
          <p className="text-xs font-medium">Traversing entity graph...</p>
        </div>
      ) : error ? (
        <div className="my-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 text-xs text-amber-700 dark:text-amber-300 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Knowledge Graph Unavailable</p>
            <p className="mt-0.5 text-amber-600 dark:text-amber-400">{error}</p>
          </div>
        </div>
      ) : !graphData || !graphData.nodes?.length ? (
        <div className="py-12 text-center text-slate-400 dark:text-slate-500">
          <Network className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-xs font-medium">No graph entities found for this claim</p>
          <p className="text-[11px] mt-0.5">Entity relationship graph will populate as cross-references are resolved.</p>
        </div>
      ) : viewMode === 'graph' ? (
        <div className="mt-4 flex flex-col lg:flex-row gap-4">
          {/* SVG Canvas */}
          <div className="flex-1 relative bg-slate-50 dark:bg-slate-950/60 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden min-h-[380px] flex items-center justify-center">
            {/* Zoom Controls */}
            <div className="absolute top-3 right-3 flex items-center gap-1 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xs p-1 rounded-lg border border-slate-200 dark:border-slate-700 shadow-2xs z-10">
              <button
                type="button"
                onClick={() => setZoom((z) => Math.min(1.5, z + 0.1))}
                className="p-1 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <span className="text-[10px] font-mono px-1 text-slate-500">{Math.round(zoom * 100)}%</span>
              <button
                type="button"
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.1))}
                className="p-1 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setZoom(1)}
                className="p-1 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Reset Zoom"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>

            <svg
              viewBox="0 0 600 360"
              className="w-full h-[360px] select-none transition-transform duration-200"
              style={{ transform: `scale(${zoom})` }}
            >
              <defs>
                <marker
                  id="arrowhead"
                  markerWidth="8"
                  markerHeight="6"
                  refX="18"
                  refY="3"
                  orient="auto"
                >
                  <polygon points="0 0, 8 3, 0 6" fill="#94a3b8" />
                </marker>
              </defs>

              {/* Edges */}
              {graphData.edges.map((edge, idx) => {
                const src = nodeLayout.get(edge.source);
                const tgt = nodeLayout.get(edge.target);
                if (!src || !tgt) return null;

                const midX = (src.x + tgt.x) / 2;
                const midY = (src.y + tgt.y) / 2;

                return (
                  <g key={idx} className="transition-opacity">
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke="#94a3b8"
                      strokeWidth="1.5"
                      strokeDasharray={edge.confidence ? undefined : '4 2'}
                      markerEnd="url(#arrowhead)"
                      className="dark:stroke-slate-600"
                    />
                    <rect
                      x={midX - 35}
                      y={midY - 8}
                      width="70"
                      height="16"
                      rx="3"
                      fill="#f8fafc"
                      className="dark:fill-slate-900"
                    />
                    <text
                      x={midX}
                      y={midY + 3}
                      textAnchor="middle"
                      className="text-[9px] fill-slate-500 dark:fill-slate-400 font-mono font-medium"
                    >
                      {edge.relationship}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {graphData.nodes.map((node) => {
                const pos = nodeLayout.get(node.id);
                if (!pos) return null;
                const isSelected = node.id === selectedNodeId;
                const style = getNodeColor(node.type);

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onClick={() => setSelectedNodeId(node.id)}
                    className="cursor-pointer group"
                  >
                    <circle
                      r={isSelected ? 26 : 22}
                      fill={style.bg}
                      stroke={isSelected ? '#ffffff' : style.border}
                      strokeWidth={isSelected ? 3 : 2}
                      className="transition-all duration-150 filter drop-shadow-sm group-hover:scale-110"
                    />
                    <text
                      textAnchor="middle"
                      dy="4"
                      fill={style.text}
                      className="text-[10px] font-bold pointer-events-none"
                    >
                      {node.type.slice(0, 3)}
                    </text>
                    <text
                      textAnchor="middle"
                      dy="36"
                      className="text-[11px] font-medium fill-slate-700 dark:fill-slate-200 pointer-events-none"
                    >
                      {node.label.length > 20 ? `${node.label.slice(0, 18)}…` : node.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Selected Node Details Sidecard */}
          <div className="w-full lg:w-72 bg-card-subtle rounded-xl border border-border p-4 flex flex-col justify-between">
            {selectedNode ? (
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-border mb-3">
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${getNodeColor(selectedNode.type).badgeBg} ${getNodeColor(selectedNode.type).badgeText}`}>
                    {selectedNode.type}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    ID: {selectedNode.id}
                  </span>
                </div>

                <h4 className="text-sm font-semibold text-foreground mb-2">
                  {selectedNode.label}
                </h4>

                {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                  <div className="space-y-1.5 mt-3 text-xs">
                    <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Node Properties</p>
                    {Object.entries(selectedNode.properties).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between text-[11px]">
                        <span className="text-muted-foreground capitalize">{key}:</span>
                        <span className="font-mono text-foreground font-semibold">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Connected Edges */}
                <div className="mt-4 pt-3 border-t border-border">
                  <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Connected Relationships</p>
                  <div className="space-y-1.5 text-xs">
                    {graphData.edges
                      .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                      .map((e, idx) => (
                        <div
                          key={idx}
                          className="p-2 rounded-lg bg-card border border-border flex items-center justify-between gap-1 text-[11px]"
                        >
                          <span className="font-mono font-semibold text-[#1565C0] dark:text-blue-400">
                            {e.relationship}
                          </span>
                          <span className="text-muted-foreground truncate max-w-[120px]">
                            {e.source === selectedNode.id ? `→ ${e.target}` : `← ${e.source}`}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-muted-foreground text-xs">
                Select a node to view entity attributes
              </div>
            )}

            <div className="pt-3 border-t border-border text-[11px] text-muted-foreground flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
              <span>Click any circle to inspect relationships.</span>
            </div>
          </div>
        </div>
      ) : (
        /* Accessible Screen Reader / Tabular Mode */
        <div className="mt-4 space-y-4">
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/60 text-xs text-blue-900 dark:text-blue-200 flex items-start gap-2">
            <Info className="w-4 h-4 mt-0.5 shrink-0 text-[#1565C0] dark:text-blue-400" />
            <span>
              Accessible graph presentation: full semantic breakdown of nodes and relationships.
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Nodes Table */}
            <div className="border border-border rounded-xl overflow-hidden bg-card">
              <div className="bg-card-subtle px-3.5 py-2 border-b border-border text-xs font-semibold text-foreground">
                Entities ({graphData.nodes.length})
              </div>
              <div className="divide-y divide-border">
                {graphData.nodes.map((node) => (
                  <div key={node.id} className="p-3 text-xs flex items-center justify-between">
                    <div>
                      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-sm mr-2 ${getNodeColor(node.type).badgeBg} ${getNodeColor(node.type).badgeText}`}>
                        {node.type}
                      </span>
                      <span className="font-semibold text-foreground">{node.label}</span>
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground">{node.id}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Edges Table */}
            <div className="border border-border rounded-xl overflow-hidden bg-card">
              <div className="bg-card-subtle px-3.5 py-2 border-b border-border text-xs font-semibold text-foreground">
                Relationships ({graphData.edges.length})
              </div>
              <div className="divide-y divide-border">
                {graphData.edges.map((edge, idx) => (
                  <div key={idx} className="p-3 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-mono text-[#1565C0] dark:text-blue-400 font-semibold mr-2">
                        {edge.relationship}
                      </span>
                      <span className="text-foreground">
                        {edge.source} &rarr; {edge.target}
                      </span>
                    </div>
                    {edge.confidence != null && (
                      <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                        {Math.round(edge.confidence * 100)}% conf
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
