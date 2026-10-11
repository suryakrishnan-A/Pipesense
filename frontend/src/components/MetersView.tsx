import { useState, useEffect } from 'react';
import { fetchMeters, type MeterInventoryItem } from '../lib/api';
import { Thermometer, Search, AlertCircle } from 'lucide-react';

export default function MetersView() {
  const [meters, setMeters] = useState<MeterInventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchMeters();
        setMeters(data);
      } catch (err: any) {
        console.error('Failed to load meters', err);
        setError('Failed to connect to backend meter inventory API.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredMeters = meters.filter(m =>
    m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (m.building_name && m.building_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const activeCount = meters.filter(m => m.is_active).length;

  if (loading) {
    return <div className="p-8 text-[var(--color-pipesense-muted)]">Loading meter inventory...</div>;
  }

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Thermometer className="w-6 h-6 text-[var(--color-pipesense-cyan)]" />
            <h1 className="text-2xl font-hud font-bold text-[var(--color-pipesense-cyan)]">METER INVENTORY & HEALTH</h1>
          </div>
          <p className="text-sm text-[var(--color-pipesense-muted)] mt-1">
            Physical ultrasonic flow sensors, pressure meters, and telemetry collection nodes.
          </p>
        </div>
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-pipesense-muted)]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search meter name or zone..."
            className="bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-md pl-9 pr-4 py-2 text-sm focus:outline-none focus:border-[var(--color-pipesense-cyan)] transition-colors w-64"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl">
          <div className="text-xs font-mono text-[var(--color-pipesense-muted)]">TOTAL METERS</div>
          <div className="text-2xl font-bold font-mono text-[var(--color-pipesense-cyan)] mt-1">{meters.length}</div>
          <div className="text-[11px] text-[var(--color-pipesense-muted)] mt-1">Installed topology sensors</div>
        </div>
        <div className="p-4 bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl">
          <div className="text-xs font-mono text-[var(--color-pipesense-muted)]">OPERATIONAL STATUS</div>
          <div className="text-2xl font-bold font-mono text-[var(--color-pipesense-green)] mt-1">{activeCount} / {meters.length}</div>
          <div className="text-[11px] text-[var(--color-pipesense-muted)] mt-1">100% telemetry online</div>
        </div>
        <div className="p-4 bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl">
          <div className="text-xs font-mono text-[var(--color-pipesense-muted)]">SAMPLING INTERVAL</div>
          <div className="text-2xl font-bold font-mono text-[#E5C07B] mt-1">1,000 ms</div>
          <div className="text-[11px] text-[var(--color-pipesense-muted)] mt-1">High-frequency telemetry mesh</div>
        </div>
        <div className="p-4 bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl">
          <div className="text-xs font-mono text-[var(--color-pipesense-muted)]">BACKEND DATA SOURCE</div>
          <div className="text-xl font-bold font-mono text-white mt-1">SQLite DB</div>
          <div className="text-[11px] text-[var(--color-pipesense-muted)] mt-1">topology.db persisted</div>
        </div>
      </div>

      {/* Meter Table */}
      <div className="flex-1 overflow-auto bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl relative">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--color-pipesense-bg)] text-[var(--color-pipesense-muted)] font-mono text-xs uppercase sticky top-0 z-10">
            <tr>
              <th className="px-6 py-4 font-medium">Meter ID</th>
              <th className="px-6 py-4 font-medium">Device Name</th>
              <th className="px-6 py-4 font-medium">Pipeline Location</th>
              <th className="px-6 py-4 font-medium">Sensor Type</th>
              <th className="px-6 py-4 font-medium">Engineering Unit</th>
              <th className="px-6 py-4 font-medium">Health Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-pipesense-border)]">
            {filteredMeters.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-[var(--color-pipesense-muted)]">
                  No meters found matching search criteria.
                </td>
              </tr>
            ) : (
              filteredMeters.map(meter => (
                <tr key={meter.id} className="hover:bg-[var(--color-pipesense-bg)] transition-colors">
                  <td className="px-6 py-4 font-mono font-bold text-[var(--color-pipesense-cyan)] text-xs">
                    {meter.id.substring(0, 13)}...
                  </td>
                  <td className="px-6 py-4 font-mono font-medium">{meter.name}</td>
                  <td className="px-6 py-4 font-mono text-xs">
                    <span className="text-white font-medium">{meter.building_name || 'Main Trunk'}</span>
                    <span className="text-[var(--color-pipesense-muted)] block text-[10px]">Node: {meter.node_name}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 rounded bg-[var(--color-pipesense-cyan)]/15 text-[var(--color-pipesense-cyan)] border border-[var(--color-pipesense-cyan)]/30 text-xs font-mono font-bold">
                      {meter.meter_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-xs">{meter.unit}</td>
                  <td className="px-6 py-4">
                    <span className="flex items-center gap-1.5 text-xs text-[var(--color-pipesense-green)] font-mono font-bold">
                      <span className="w-2 h-2 rounded-full bg-[var(--color-pipesense-green)] animate-pulse" />
                      OPERATIONAL
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
