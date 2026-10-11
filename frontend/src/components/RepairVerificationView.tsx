import { useState, useEffect } from 'react';
import {
  fetchWorkOrders,
  fetchIncidents,
  completeWorkOrder,
  verifyWorkOrder,
  repairWorkOrder,
  type PipeWorkOrder,
  type PipeIncident
} from '../lib/api';
import { CheckSquare, ShieldCheck, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function RepairVerificationView() {
  const [workOrders, setWorkOrders] = useState<PipeWorkOrder[]>([]);
  const [incidents, setIncidents] = useState<PipeIncident[]>([]);
  const [selectedWoId, setSelectedWoId] = useState<string>('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [wos, incs] = await Promise.all([fetchWorkOrders(), fetchIncidents()]);
      setWorkOrders(wos);
      setIncidents(incs);
      if (wos.length > 0 && !selectedWoId) {
        setSelectedWoId(wos[0].work_order_id);
      }
    } catch (err) {
      console.error('Failed to load work orders for verification', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const selectedWo = workOrders.find(w => w.work_order_id === selectedWoId) || workOrders[0];
  const relatedIncident = selectedWo ? incidents.find(i => i.incident_id === selectedWo.incident_id) : null;

  const handleClaimComplete = async () => {
    if (!selectedWo) return;
    setActionLoading(true);
    setActionMessage(null);
    try {
      await completeWorkOrder(selectedWo.work_order_id);
      setActionMessage({
        type: 'info',
        text: 'Technician completion claim logged. Incident moved to REPAIR_VERIFICATION. Awaiting physical telemetry check.'
      });
      await loadData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to claim completion.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerify = async (telemetryVal: number) => {
    if (!selectedWo) return;
    setActionLoading(true);
    setActionMessage(null);
    try {
      const res = await verifyWorkOrder(selectedWo.work_order_id, telemetryVal);
      if (res.state === 'RESOLVED') {
        setActionMessage({
          type: 'success',
          text: `VERIFIED & RESOLVED: Telemetry confirmed at ${telemetryVal} L/min (at baseline). Incident closed officially!`
        });
      } else {
        setActionMessage({
          type: 'error',
          text: `VERIFICATION REJECTED: Telemetry is ${telemetryVal} L/min. Leak flow is STILL ACTIVE! Ticket escalated to Senior Supervisor.`
        });
      }
      await loadData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Verification check failed.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartSecondRepair = async () => {
    if (!selectedWo) return;
    setActionLoading(true);
    setActionMessage(null);
    try {
      await repairWorkOrder(selectedWo.work_order_id);
      setActionMessage({
        type: 'info',
        text: 'Senior Supervisor dispatched: replacing damaged 2-inch pipe section.'
      });
      await loadData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to initiate secondary repair.' });
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-[var(--color-pipesense-muted)]">Loading verification gateway...</div>;
  }

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-hidden">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <CheckSquare className="w-6 h-6 text-[var(--color-pipesense-cyan)]" />
          <h1 className="text-2xl font-hud font-bold text-[var(--color-pipesense-cyan)]">REPAIR VERIFICATION GATEWAY</h1>
        </div>
        <p className="text-sm text-[var(--color-pipesense-muted)] mt-1">
          Strict closed-loop enforcement: <span className="text-white font-medium">"Repair completion is rejected without telemetry verification."</span>
        </p>
      </div>

      {actionMessage && (
        <div
          className={`p-4 rounded-xl border text-sm flex items-center gap-3 font-mono ${
            actionMessage.type === 'success'
              ? 'bg-green-500/10 border-green-500/40 text-green-300'
              : actionMessage.type === 'error'
              ? 'bg-red-500/10 border-red-500/40 text-red-300'
              : 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300'
          }`}
        >
          {actionMessage.type === 'success' && <CheckCircle2 className="w-5 h-5 flex-shrink-0" />}
          {actionMessage.type === 'error' && <AlertTriangle className="w-5 h-5 flex-shrink-0" />}
          {actionMessage.type === 'info' && <ShieldCheck className="w-5 h-5 flex-shrink-0" />}
          <span>{actionMessage.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* Left: Work Order Selection */}
        <div className="bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl p-5 flex flex-col space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="font-hud font-bold text-sm tracking-wider uppercase text-white">SELECT WORK ORDER</h2>
            <span className="text-xs font-mono text-[var(--color-pipesense-muted)]">{workOrders.length} Available</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            {workOrders.length === 0 ? (
              <div className="text-xs text-[var(--color-pipesense-muted)] text-center py-8">
                No active work orders. Inject an anomaly or run the demo to generate a work order.
              </div>
            ) : (
              workOrders.map(wo => {
                const isSelected = wo.work_order_id === selectedWo?.work_order_id;
                return (
                  <div
                    key={wo.work_order_id}
                    onClick={() => setSelectedWoId(wo.work_order_id)}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-[var(--color-pipesense-cyan)]/15 border-[var(--color-pipesense-cyan)] text-white shadow-[0_0_15px_rgba(0,240,255,0.15)]'
                        : 'bg-[var(--color-pipesense-bg)] border-[var(--color-pipesense-border)] text-[var(--color-pipesense-muted)] hover:border-white/20 hover:text-white'
                    }`}
                  >
                    <div className="flex justify-between items-center font-mono">
                      <span className="font-bold text-[var(--color-pipesense-cyan)]">{wo.work_order_id}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        wo.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                        wo.status === 'IN_PROGRESS' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {wo.status}
                      </span>
                    </div>
                    <div className="mt-1 text-[11px] truncate">{wo.notes || 'Routine maintenance'}</div>
                    <div className="mt-1 text-[10px] font-mono text-[var(--color-pipesense-muted)]">Target: {wo.incident_id}</div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Center & Right: Verification Cockpit */}
        <div className="lg:col-span-2 bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl p-6 flex flex-col justify-between space-y-6">
          {selectedWo ? (
            <>
              {/* Context Header */}
              <div className="p-4 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-xl space-y-3">
                <div className="flex flex-wrap justify-between items-center gap-2">
                  <div>
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)]">ACTIVE WORK ORDER:</span>
                    <span className="ml-2 font-mono font-bold text-lg text-white">{selectedWo.work_order_id}</span>
                  </div>
                  <div>
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)]">INCIDENT STATE:</span>
                    <span className={`ml-2 px-2.5 py-1 rounded text-xs font-mono font-bold ${
                      relatedIncident?.state === 'RESOLVED' ? 'bg-green-500/20 text-green-300 border border-green-500/40' :
                      relatedIncident?.state === 'OPEN' ? 'bg-red-500/20 text-red-300 border border-red-500/40' :
                      'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}>
                      {relatedIncident?.state || 'UNKNOWN'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono pt-2 border-t border-[var(--color-pipesense-border)]">
                  <div>
                    <span className="text-[var(--color-pipesense-muted)] block text-[10px]">ZONE / RISER</span>
                    <span className="text-white font-medium">{relatedIncident?.zone || 'BLDG-04'}</span>
                  </div>
                  <div>
                    <span className="text-[var(--color-pipesense-muted)] block text-[10px]">BASELINE FLOW</span>
                    <span className="text-white font-medium">{relatedIncident?.baseline_flow_lpm || 18.4} L/min</span>
                  </div>
                  <div>
                    <span className="text-[var(--color-pipesense-muted)] block text-[10px]">PEAK SPIKE FLOW</span>
                    <span className="text-red-400 font-medium">{relatedIncident?.current_flow_lpm || 64.2} L/min</span>
                  </div>
                  <div>
                    <span className="text-[var(--color-pipesense-muted)] block text-[10px]">WORK ORDER STATUS</span>
                    <span className="text-[var(--color-pipesense-cyan)] font-medium">{selectedWo.status}</span>
                  </div>
                </div>
              </div>

              {/* 3-Stage Closed-Loop Workflow */}
              <div className="space-y-4">
                <h3 className="font-hud font-bold text-sm tracking-wider uppercase text-[var(--color-pipesense-cyan)]">
                  CLOSED-LOOP VERIFICATION STAGES
                </h3>

                {/* Stage 1 */}
                <div className="p-4 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-xl flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold text-white flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-[var(--color-pipesense-cyan)]/20 text-[var(--color-pipesense-cyan)] flex items-center justify-center text-xs font-mono font-bold">1</span>
                      Field Completion Claim
                    </div>
                    <p className="text-xs text-[var(--color-pipesense-muted)] mt-1">
                      Technician claims physical work completed (e.g. replaced washer).
                    </p>
                  </div>
                  <button
                    onClick={handleClaimComplete}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-[var(--color-pipesense-cyan)]/20 hover:bg-[var(--color-pipesense-cyan)]/30 border border-[var(--color-pipesense-cyan)]/50 rounded-lg text-xs font-mono text-[var(--color-pipesense-cyan)] uppercase font-bold tracking-wider transition-all cursor-pointer"
                  >
                    Claim Complete
                  </button>
                </div>

                {/* Stage 2 */}
                <div className="p-4 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-bold text-white flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs font-mono font-bold">2</span>
                        Sensor Telemetry Verification
                      </div>
                      <p className="text-xs text-[var(--color-pipesense-muted)] mt-1">
                        Physical flow meter is queried to mathematically prove leak cessation.
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    <button
                      onClick={() => handleVerify(61.8)}
                      disabled={actionLoading}
                      className="px-4 py-2.5 bg-red-500/15 hover:bg-red-500/25 border border-red-500/40 rounded-lg text-xs font-mono text-red-300 uppercase font-bold tracking-wider flex items-center gap-2 cursor-pointer transition-all"
                    >
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      Test Bad Repair (61.8 L/min &rarr; REJECT)
                    </button>
                    <button
                      onClick={() => handleVerify(18.2)}
                      disabled={actionLoading}
                      className="px-4 py-2.5 bg-green-500/20 hover:bg-green-500/30 border border-green-500/50 rounded-lg text-xs font-mono text-green-300 uppercase font-bold tracking-wider flex items-center gap-2 cursor-pointer transition-all"
                    >
                      <CheckCircle2 className="w-4 h-4 text-green-400" />
                      Test Good Repair (18.2 L/min &rarr; PASS)
                    </button>
                  </div>
                </div>

                {/* Stage 3 */}
                <div className="p-4 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-xl flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold text-white flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center text-xs font-mono font-bold">3</span>
                      Escalated Secondary Repair Dispatch
                    </div>
                    <p className="text-xs text-[var(--color-pipesense-muted)] mt-1">
                      If telemetry verification failed, dispatch Senior Supervisor for structural pipe replacement.
                    </p>
                  </div>
                  <button
                    onClick={handleStartSecondRepair}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/50 rounded-lg text-xs font-mono text-purple-300 uppercase font-bold tracking-wider transition-all cursor-pointer"
                  >
                    Dispatch Supervisor
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-16 text-[var(--color-pipesense-muted)]">
              No work order selected.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
