import { useState, useEffect } from 'react';
import { fetchIncidents } from '../lib/api';
import { Search } from 'lucide-react';

export default function IncidentsView() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchIncidents();
        setIncidents(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="p-8 text-[var(--color-pipesense-muted)]">Loading incidents...</div>;
  }

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-hud font-bold text-[var(--color-pipesense-cyan)]">INCIDENTS & EVIDENCE</h1>
          <p className="text-sm text-[var(--color-pipesense-muted)]">Manage detected anomalies and investigation state.</p>
        </div>
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-pipesense-muted)]" />
          <input 
            type="text" 
            placeholder="Search incident ID or zone..."
            className="bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-md pl-9 pr-4 py-2 text-sm focus:outline-none focus:border-[var(--color-pipesense-cyan)] transition-colors w-64"
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl relative">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-pipesense-bg)] text-[var(--color-pipesense-muted)] font-mono text-xs uppercase sticky top-0 z-10">
            <tr>
              <th className="px-6 py-4 font-medium">Incident ID</th>
              <th className="px-6 py-4 font-medium">Zone/Asset</th>
              <th className="px-6 py-4 font-medium">Severity</th>
              <th className="px-6 py-4 font-medium">State</th>
              <th className="px-6 py-4 font-medium">Current Flow</th>
              <th className="px-6 py-4 font-medium">Baseline</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-pipesense-border)]">
            {incidents.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-[var(--color-pipesense-muted)]">
                  No active incidents found.
                </td>
              </tr>
            ) : (
              incidents.map(inc => (
                <tr key={inc.incident_id} className="hover:bg-[var(--color-pipesense-bg)] transition-colors cursor-pointer">
                  <td className="px-6 py-4 font-mono font-bold text-[var(--color-pipesense-cyan)]">{inc.incident_id}</td>
                  <td className="px-6 py-4 font-mono">{inc.zone}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-md text-xs font-bold ${
                      inc.severity === 'HIGH' || inc.severity === 'CRITICAL' ? 'bg-[var(--color-pipesense-red)]/20 text-[var(--color-pipesense-red)]' : 
                      inc.severity === 'MEDIUM' ? 'bg-[var(--color-pipesense-amber)]/20 text-[var(--color-pipesense-amber)]' : 
                      'bg-[var(--color-pipesense-green)]/20 text-[var(--color-pipesense-green)]'
                    }`}>
                      {inc.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-xs">{inc.state}</td>
                  <td className="px-6 py-4 font-mono">{inc.current_flow_lpm} L/min</td>
                  <td className="px-6 py-4 font-mono">{inc.baseline_flow_lpm} L/min</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
