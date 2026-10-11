import { useState, useEffect } from 'react';
import { fetchAuditLogs, type IncidentEvent } from '../lib/api';
import { FileText, Search, ChevronDown, ChevronUp } from 'lucide-react';

export default function AuditTrailView() {
  const [logs, setLogs] = useState<IncidentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterActor, setFilterActor] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const loadLogs = async () => {
    try {
      const data = await fetchAuditLogs();
      setLogs(data);
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const filteredLogs = logs.filter(log => {
    const actorMatches = filterActor === 'ALL' || (log.actor_id && log.actor_id.toUpperCase().includes(filterActor.toUpperCase()));
    const termMatches = !searchTerm ||
      (log.event_type && log.event_type.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (log.incident_id && log.incident_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (log.actor_id && log.actor_id.toLowerCase().includes(searchTerm.toLowerCase()));
    return actorMatches && termMatches;
  });

  const getActionBadgeColor = (action: string) => {
    if (!action) return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
    const a = action.toUpperCase();
    if (a.includes('VERIFIED') || a.includes('RESOLVED') || a.includes('CLOSE')) {
      return 'bg-green-500/20 text-green-300 border-green-500/40';
    }
    if (a.includes('FAIL') || a.includes('ANOMALY') || a.includes('REJECT') || a.includes('ESCALAT')) {
      return 'bg-red-500/20 text-red-300 border-red-500/40';
    }
    if (a.includes('INVESTIGAT') || a.includes('TOOL') || a.includes('LEAK_CONFIRMED')) {
      return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    }
    if (a.includes('WORK_ORDER') || a.includes('CLAIM') || a.includes('REPAIR')) {
      return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    }
    return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
  };

  if (loading) {
    return <div className="p-8 text-[var(--color-pipesense-muted)]">Loading immutable audit trail...</div>;
  }

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-[var(--color-pipesense-cyan)]" />
            <h1 className="text-2xl font-hud font-bold text-[var(--color-pipesense-cyan)]">IMMUTABLE AUDIT TRAIL</h1>
          </div>
          <p className="text-sm text-[var(--color-pipesense-muted)] mt-1">
            Chronological audit log recording anomaly triggers, AI agent reasoning, crew dispatches, and verification verdicts.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-pipesense-muted)]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search event, actor, or ID..."
              className="bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-md pl-9 pr-4 py-2 text-sm focus:outline-none focus:border-[var(--color-pipesense-cyan)] transition-colors w-60"
            />
          </div>

          <div className="flex items-center bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-lg p-1 text-xs font-mono">
            {['ALL', 'SYSTEM', 'AGENT', 'TECHNICIAN'].map(actor => (
              <button
                key={actor}
                onClick={() => setFilterActor(actor)}
                className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                  filterActor === actor
                    ? 'bg-[var(--color-pipesense-cyan)] text-black font-bold'
                    : 'text-[var(--color-pipesense-muted)] hover:text-white'
                }`}
              >
                {actor === 'AGENT' ? 'AGENT (LOCAL)' : actor}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Log Feed */}
      <div className="flex-1 overflow-auto bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl p-5 custom-scrollbar">
        {filteredLogs.length === 0 ? (
          <div className="text-center py-16 text-[var(--color-pipesense-muted)] text-sm">
            No audit records matching your criteria. Run the demo or trigger an anomaly to populate logs.
          </div>
        ) : (
          <div className="space-y-3">
            {filteredLogs.map((log, idx) => {
              const isExpanded = expandedIdx === idx;
              const actionName = log.event_type || log.action || 'UNKNOWN_ACTION';
              return (
                <div
                  key={idx}
                  className="p-4 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] hover:border-white/20 rounded-xl transition-all"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-xs">
                    <div className="flex items-center gap-3">
                      <span className="text-[var(--color-pipesense-muted)] text-[11px]">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded border text-[10px] font-bold uppercase ${getActionBadgeColor(actionName)}`}>
                        {actionName.replace(/_/g, ' ')}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[var(--color-pipesense-muted)] text-[10px]">
                        Actor: <strong className="text-white">{log.actor_id || 'SYSTEM'}</strong>
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      {log.incident_id && (
                        <span className="text-[var(--color-pipesense-cyan)] font-bold">
                          {log.incident_id}
                        </span>
                      )}
                      {log.details && Object.keys(log.details).length > 0 && (
                        <button
                          onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                          className="flex items-center gap-1 text-[var(--color-pipesense-cyan)] hover:underline cursor-pointer text-[11px]"
                        >
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          {isExpanded ? 'Hide Payload' : 'Inspect Details'}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Summary row */}
                  {log.details && (
                    <div className="mt-2 text-xs text-[var(--color-pipesense-muted)] font-mono">
                      {log.details.message && <div>{log.details.message}</div>}
                      {log.details.finding && <div>Finding: <span className="text-white">{log.details.finding}</span></div>}
                      {log.details.notes && <div>Note: <span className="text-white">{log.details.notes}</span></div>}
                    </div>
                  )}

                  {/* Expandable JSON Payload */}
                  {isExpanded && log.details && (
                    <pre className="mt-3 p-3 bg-black/60 border border-[var(--color-pipesense-border)] rounded-lg text-[10px] font-mono text-[var(--color-pipesense-muted)] overflow-x-auto leading-relaxed">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
