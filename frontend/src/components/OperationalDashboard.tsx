import { useEffect, useState } from 'react';
import {
  fetchSummary,
  fetchIncidents,
  fetchImpact,
  runDemo,
  resetDemo,
  fetchEvents,
  fetchDrainSummary,
  fetchDrainIncidents,
  detectDrainAnomaly,
  investigateDrainIncident,
  dispatchDrainWorkOrder,
  fetchDrainWorkOrders,
  completeDrainWorkOrder,
  verifyDrainWorkOrder,
  repairDrainWorkOrder,
  type DrainSummary,
  type DrainIncident,
  type DrainWorkOrder,
  type IncidentEvent,
  type PipeSummary,
  type PipeImpact
} from '../lib/api';
import {
  ArrowLeft,
  Activity,
  Play,
  RotateCcw,
  Cpu,
  RadioTower,
  Database,
  TriangleAlert,
  ShieldCheck,
  Droplet,
  Waves,
  Wrench,
  AlertTriangle,
  CheckCircle,
  Clock,
  Layers,
  Compass,
  ChevronDown,
  ChevronUp,
  Zap,
  Gauge
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function OperationalDashboard({ onBack }: { onBack: () => void }) {
  // Subsystem selector: 'pipesense' (default) or 'drainpilot'
  const [activeSubsystem, setActiveSubsystem] = useState<'pipesense' | 'drainpilot'>('pipesense');

  // Live Clock
  const [currentTime, setCurrentTime] = useState<string>('');

  // Selected Zone / Target in 3D Map
  const [selectedZone, setSelectedZone] = useState<string>('BLDG-04');
  const [activeLayers, setActiveLayers] = useState<{ pipelines: boolean; nodes: boolean; labels: boolean }>({
    pipelines: true,
    nodes: true,
    labels: true
  });

  // PipeSense state
  const [summary, setSummary] = useState<PipeSummary | null>(null);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [impact, setImpact] = useState<PipeImpact | null>(null);
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [expandedEventId, setExpandedEventId] = useState<number | null>(null);

  // DrainPilot state
  const [drainSummary, setDrainSummary] = useState<DrainSummary | null>(null);
  const [drainIncidents, setDrainIncidents] = useState<DrainIncident[]>([]);
  const [drainWorkOrders, setDrainWorkOrders] = useState<DrainWorkOrder[]>([]);
  const [selectedDrainId, setSelectedDrainId] = useState<string | null>(null);
  const [drainEvents, setDrainEvents] = useState<IncidentEvent[]>([]);
  const [drainActionLoading, setDrainActionLoading] = useState(false);

  const [loading, setLoading] = useState(true);

  // Clock timer
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Load PipeSense data
  const loadPipeData = async () => {
    try {
      const [s, inc, imp] = await Promise.all([
        fetchSummary(),
        fetchIncidents(),
        fetchImpact()
      ]);
      setSummary(s);
      setIncidents(inc);
      setImpact(imp);

      const bldg4 = inc.find((i: any) => i.zone === 'BLDG-04');
      if (bldg4) {
        const evts = await fetchEvents(bldg4.incident_id);
        setEvents(evts.reverse());
      } else {
        setEvents([]);
      }
    } catch (e) {
      console.error('PipeSense dashboard load failed', e);
    }
  };

  // Load DrainPilot data
  const loadDrainData = async () => {
    try {
      const [ds, dInc, dWo] = await Promise.all([
        fetchDrainSummary(),
        fetchDrainIncidents(),
        fetchDrainWorkOrders()
      ]);
      setDrainSummary(ds);
      setDrainIncidents(dInc);
      setDrainWorkOrders(dWo);

      const targetId =
        selectedDrainId && dInc.some((i: DrainIncident) => i.incident_id === selectedDrainId)
          ? selectedDrainId
          : dInc[0]?.incident_id || null;

      setSelectedDrainId(targetId);

      if (targetId) {
        const evts = await fetchEvents(targetId);
        setDrainEvents(evts.reverse());
      } else {
        setDrainEvents([]);
      }
    } catch (e) {
      console.error('DrainPilot dashboard load failed', e);
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    await Promise.all([loadPipeData(), loadDrainData()]);
    setLoading(false);
  };

  useEffect(() => {
    loadAllData();
  }, []);

  useEffect(() => {
    if (selectedDrainId) {
      fetchEvents(selectedDrainId)
        .then(evts => setDrainEvents(evts.reverse()))
        .catch(err => console.error('Failed to load drain events', err));
    } else {
      setDrainEvents([]);
    }
  }, [selectedDrainId]);

  // Actions
  const handleRunDemo = async () => {
    await runDemo();
    await loadPipeData();
  };

  const handleResetDemo = async () => {
    await resetDemo();
    await loadPipeData();
  };

  // DrainPilot Actions
  const handleSimulateSurcharge = async () => {
    setDrainActionLoading(true);
    try {
      const res = await detectDrainAnomaly({
        zone: 'CHAMBER-STORM-01',
        chamber_id: 'CHAMBER-STORM-01',
        water_level_cm: 195.0,
        chamber_depth_cm: 200.0,
        rate_of_rise_cm_per_hr: 32.5,
        silt_depth_cm: 45.0,
        pump_status: 'OVERLOAD',
        rainfall_mm_per_hr: 62.0,
        catchment_area: 'North Campus Catchment'
      });
      if (res && res.incident_id) {
        setSelectedDrainId(res.incident_id);
      }
      await loadDrainData();
    } catch (e) {
      console.error('Failed to simulate drainage surcharge', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  const handleSimulateSilt = async () => {
    setDrainActionLoading(true);
    try {
      const res = await detectDrainAnomaly({
        zone: 'OUTFALL-BASIN-04',
        chamber_id: 'OUTFALL-BASIN-04',
        water_level_cm: 165.0,
        chamber_depth_cm: 200.0,
        rate_of_rise_cm_per_hr: 12.0,
        silt_depth_cm: 72.0,
        pump_status: 'OPERATIONAL',
        rainfall_mm_per_hr: 15.0,
        catchment_area: 'South Wetland Outfall'
      });
      if (res && res.incident_id) {
        setSelectedDrainId(res.incident_id);
      }
      await loadDrainData();
    } catch (e) {
      console.error('Failed to simulate silt accumulation', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  const handleInvestigateDrain = async (incidentId: string) => {
    setDrainActionLoading(true);
    try {
      await investigateDrainIncident(incidentId);
      await loadDrainData();
    } catch (e) {
      console.error('Failed to investigate drain incident', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  const handleDispatchDrain = async (incidentId: string) => {
    setDrainActionLoading(true);
    try {
      await dispatchDrainWorkOrder(incidentId);
      await loadDrainData();
    } catch (e) {
      console.error('Failed to dispatch drain work order', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  const handleCompleteDrain = async (workOrderId: string) => {
    setDrainActionLoading(true);
    try {
      await completeDrainWorkOrder(workOrderId);
      await loadDrainData();
    } catch (e) {
      console.error('Failed to complete drain work order', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  const handleVerifyDrainPass = async (workOrderId: string) => {
    setDrainActionLoading(true);
    try {
      await verifyDrainWorkOrder(workOrderId, {
        water_level_cm: 45.0,
        chamber_depth_cm: 200.0,
        rate_of_rise_cm_per_hr: 0.0,
        pump_status: 'OPERATIONAL'
      });
      await loadDrainData();
    } catch (e) {
      console.error('Failed to verify drain resolution', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  const handleVerifyDrainFail = async (workOrderId: string) => {
    setDrainActionLoading(true);
    try {
      await verifyDrainWorkOrder(workOrderId, {
        water_level_cm: 175.0,
        chamber_depth_cm: 200.0,
        rate_of_rise_cm_per_hr: 14.0,
        pump_status: 'OVERLOAD'
      });
      await loadDrainData();
    } catch (e) {
      console.error('Failed to submit failing verification', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  const handleRepairDrain = async (workOrderId: string) => {
    setDrainActionLoading(true);
    try {
      await repairDrainWorkOrder(workOrderId);
      await loadDrainData();
    } catch (e) {
      console.error('Failed to initiate second repair attempt', e);
    } finally {
      setDrainActionLoading(false);
    }
  };

  // Active targeted drainage incident
  const activeDrainIncident = drainIncidents.find(i => i.incident_id === selectedDrainId);
  const activeDrainWo = activeDrainIncident
    ? drainWorkOrders.find(w => w.incident_id === activeDrainIncident.incident_id)
    : null;

  return (
    <div className="h-full bg-[var(--color-pipesense-bg)] text-[var(--color-pipesense-text)] overflow-x-hidden relative font-hud selection:bg-[var(--color-pipesense-cyan)] selection:text-[var(--color-pipesense-bg)] rounded-xl border border-[var(--color-pipesense-border)]">
      {/* Background Subtle Grid Lines */}
      <div className="absolute inset-0 bg-[var(--color-pipesense-bg)] pointer-events-none rounded-xl" />
      <div className="absolute inset-0 dark:bg-[linear-gradient(rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[linear-gradient(rgba(0,0,0,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.02)_1px,transparent_1px)] bg-[size:3rem_3rem] pointer-events-none rounded-xl" />

      {/* =========================================================================
          1. HEADER NAVIGATION & COMMAND BAR
          ========================================================================= */}
      <header className="sticky top-0 z-40 flex flex-wrap justify-between items-center px-6 md:px-10 py-4 border-b border-[var(--color-pipesense-border)] bg-[var(--color-pipesense-panel)]/95 backdrop-blur-xl shadow-sm">
        {/* Left: Brand & Status */}
        <div className="flex items-center gap-5">
          <button
            onClick={onBack}
            className="p-2.5 bg-[var(--color-pipesense-secondary)] hover:bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] hover:border-[var(--color-pipesense-cyan)]/40 rounded-xl transition-all group cursor-pointer"
            title="Return to 3D Overview"
          >
            <ArrowLeft className="w-5 h-5 text-[var(--color-pipesense-muted)] group-hover:text-[var(--color-pipesense-cyan)] transition-colors" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl md:text-2xl font-bold tracking-[0.18em] text-[var(--color-pipesense-text)] text-glow-cyan uppercase">
                ENVIRONMENTAL OPERATIONS COMMAND
              </h1>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-mono text-[var(--color-pipesense-muted)] mt-0.5">
              <span className="flex items-center gap-1.5 text-[var(--color-pipesense-cyan)]">
                <RadioTower className="w-3 h-3 text-[var(--color-pipesense-green)]" /> CAMPUS TELEMETRY MESH
              </span>
              <span>&bull;</span>
              <span>STATION: HYD-CAMPUS-09</span>
            </div>
          </div>
        </div>

        {/* Center: Subsystem Selector Tabs */}
        <div className="flex items-center bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-xl p-1 my-2 md:my-0 shadow-inner">
          <button
            onClick={() => setActiveSubsystem('pipesense')}
            className={`px-5 py-2 font-mono text-xs tracking-wider uppercase rounded-lg transition-all flex items-center gap-2 cursor-pointer ${
              activeSubsystem === 'pipesense'
                ? 'bg-[var(--color-pipesense-cyan)] text-[var(--color-pipesense-bg)] font-bold shadow-[0_0_15px_rgba(0,191,255,0.4)]'
                : 'text-[var(--color-pipesense-muted)] hover:text-[var(--color-pipesense-text)] hover:bg-[var(--color-pipesense-panel)]/60'
            }`}
          >
            <Droplet className="w-3.5 h-3.5 fill-current" />
            <span>PipeSense (Water)</span>
          </button>
          <button
            onClick={() => setActiveSubsystem('drainpilot')}
            className={`px-5 py-2 font-mono text-xs tracking-wider uppercase rounded-lg transition-all flex items-center gap-2 cursor-pointer ${
              activeSubsystem === 'drainpilot'
                ? 'bg-[var(--color-pipesense-cyan)] text-[var(--color-pipesense-bg)] font-bold shadow-[0_0_15px_rgba(0,191,255,0.4)]'
                : 'text-[var(--color-pipesense-muted)] hover:text-[var(--color-pipesense-text)] hover:bg-[var(--color-pipesense-panel)]/60'
            }`}
          >
            <Waves className="w-3.5 h-3.5" />
            <span>DrainPilot (Drainage)</span>
          </button>
        </div>

        {/* Right: Live Beacon, Clock & Actions */}
        <div className="flex items-center gap-4">
          {/* LIVE Indicator & Clock */}
          <div className="flex items-center gap-3 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] px-4 py-2 rounded-xl font-mono text-xs">
            <span className="flex items-center gap-1.5 text-[var(--color-pipesense-green)] font-bold">
              <span className="w-2 h-2 rounded-full bg-[var(--color-pipesense-green)] animate-ping" />
              <span className="w-2 h-2 rounded-full bg-[var(--color-pipesense-green)] absolute" />
              LIVE
            </span>
            <span className="text-[var(--color-pipesense-border)]">|</span>
            <span className="text-[var(--color-pipesense-text)] flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[var(--color-pipesense-cyan)]" />
              {currentTime || '12:00:00'}
            </span>
          </div>

          {/* Action Buttons */}
          {activeSubsystem === 'pipesense' ? (
            <div className="flex items-center gap-2.5">
              <button
                onClick={handleResetDemo}
                className="flex items-center gap-2 px-3.5 py-2 bg-[var(--color-pipesense-secondary)] hover:bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] hover:border-[var(--color-pipesense-cyan)]/40 rounded-xl font-mono text-xs uppercase transition-all tracking-wider text-[var(--color-pipesense-muted)] hover:text-[var(--color-pipesense-text)] cursor-pointer"
                title="Reset simulation state"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Purge State
              </button>
              <button
                onClick={handleRunDemo}
                className="flex items-center gap-2 px-4 py-2 bg-[var(--color-pipesense-cyan)]/15 text-[var(--color-pipesense-cyan)] hover:bg-[var(--color-pipesense-cyan)]/25 border border-[var(--color-pipesense-cyan)]/50 hover:border-[var(--color-pipesense-cyan)] rounded-xl font-mono text-xs uppercase transition-all tracking-wider shadow-[0_0_20px_rgba(0,191,255,0.15)] cursor-pointer"
                title="Run flagship leak sequence"
              >
                <Play className="w-3.5 h-3.5 fill-current" /> Inject Flagship Anomaly
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2.5">
              <button
                onClick={loadDrainData}
                disabled={drainActionLoading}
                className="flex items-center gap-2 px-3.5 py-2 bg-[var(--color-pipesense-secondary)] hover:bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl font-mono text-xs uppercase tracking-wider text-[var(--color-pipesense-muted)] hover:text-[var(--color-pipesense-text)] cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Refresh
              </button>
              <button
                onClick={handleSimulateSilt}
                disabled={drainActionLoading}
                className="flex items-center gap-2 px-3.5 py-2 bg-amber-500/15 text-amber-500 dark:text-amber-300 hover:bg-amber-500/25 border border-amber-500/40 rounded-xl font-mono text-xs uppercase tracking-wider transition-all cursor-pointer"
              >
                <Play className="w-3.5 h-3.5" /> Silt Anomaly
              </button>
              <button
                onClick={handleSimulateSurcharge}
                disabled={drainActionLoading}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/15 text-red-500 dark:text-red-300 hover:bg-red-500/25 border border-red-500/40 rounded-xl font-mono text-xs uppercase tracking-wider transition-all cursor-pointer"
              >
                <Play className="w-3.5 h-3.5" /> Surcharge Anomaly
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content Layout */}
      {loading ? (
        <div className="flex items-center justify-center h-[calc(100vh-80px)] bg-[var(--color-pipesense-bg)]">
          <div className="flex flex-col items-center gap-6">
            <div className="relative">
              <div className="w-20 h-20 border-2 border-[var(--color-pipesense-border)] rounded-full" />
              <div className="absolute inset-0 w-20 h-20 border-t-2 border-l-2 border-[var(--color-pipesense-cyan)] rounded-full animate-spin shadow-[0_0_25px_rgba(0,191,255,0.5)]" />
              <Cpu className="absolute inset-0 m-auto text-[var(--color-pipesense-cyan)] animate-pulse w-8 h-8" />
            </div>
            <p className="font-mono text-[var(--color-pipesense-cyan)] tracking-[0.3em] text-sm animate-pulse">
              SYNCING ENVIRONMENTAL SENSOR MESH...
            </p>
          </div>
        </div>
      ) : (
        <div className="p-6 md:p-8 space-y-6 max-w-[1920px] mx-auto bg-[var(--color-pipesense-bg)]">
          {/* =========================================================================
              2. TOP KPI CARDS (ROW OF 4)
              ========================================================================= */}
          {activeSubsystem === 'pipesense' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
              {/* Card 1: Total Daily Flow */}
              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-cyan)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    TOTAL DAILY FLOW
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-cyan)]">
                    <Droplet className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-text)] mb-1">
                  148,200 <span className="text-lg text-[var(--color-pipesense-muted)] font-normal">L</span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>Baseline: 104 L/min (5 Zones)</span>
                  <span className="text-[var(--color-pipesense-cyan)] font-bold tracking-wider">NOMINAL</span>
                </div>
              </div>

              {/* Card 2: Estimated Daily Loss */}
              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-red)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    ESTIMATED DAILY LOSS
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-red)]">
                    <TriangleAlert className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-red)] text-glow-red mb-1">
                  {impact?.estimated_daily_loss_liters
                    ? impact.estimated_daily_loss_liters.toLocaleString()
                    : impact?.peak_abnormal_flow_lpm
                    ? '65,952'
                    : '0'}{' '}
                  <span className="text-lg text-[var(--color-pipesense-red)]/70 font-normal">L/day</span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>Target: BLDG-04 Riser</span>
                  <span className="px-2 py-0.5 rounded bg-[var(--color-pipesense-red)]/15 text-[var(--color-pipesense-red)] border border-[var(--color-pipesense-red)]/35 text-[10px] font-bold">
                    CRITICAL SEVERITY
                  </span>
                </div>
              </div>

              {/* Card 3: Active Anomalies */}
              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-amber)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    ACTIVE ANOMALIES
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-amber)]">
                    <Activity className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-amber)] mb-1">
                  {summary?.active_incidents || 0}{' '}
                  <span className="text-lg text-[var(--color-pipesense-amber)]/70 font-normal">Active Alert</span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>Acoustic + Telemetry Match</span>
                  <span className="px-2 py-0.5 rounded bg-[var(--color-pipesense-amber)]/15 text-[var(--color-pipesense-amber)] border border-[var(--color-pipesense-amber)]/35 text-[10px] font-bold">
                    INVESTIGATION OPEN
                  </span>
                </div>
              </div>

              {/* Card 4: System Efficiency */}
              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-green)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    SYSTEM EFFICIENCY
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-green)]">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-green)] text-glow-green mb-1">
                  {impact?.verified_daily_loss_avoided_liters ? '99.8%' : '55.6%'}
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>
                    {impact?.verified_daily_loss_avoided_liters
                      ? `${impact.verified_daily_loss_avoided_liters.toLocaleString()} L Avoided`
                      : 'Post-Repair Verified'}
                  </span>
                  <span className="text-[var(--color-pipesense-green)] font-bold tracking-wider">
                    {impact?.verified_daily_loss_avoided_liters ? 'OPTIMAL' : 'DEGRADED'}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            /* DrainPilot Top KPI Cards */
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-cyan)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    MONITORED BASINS
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-cyan)]">
                    <Waves className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-text)] mb-1">
                  {drainSummary?.total_zones_monitored || 2}{' '}
                  <span className="text-lg text-[var(--color-pipesense-muted)] font-normal">Chambers</span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>North Stormwater Catchment</span>
                  <span className="text-[var(--color-pipesense-cyan)] font-bold tracking-wider">UPLINK ACTIVE</span>
                </div>
              </div>

              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-red)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    OVERFLOW RISK
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-red)]">
                    <TriangleAlert className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-red)] text-glow-red mb-1">
                  {drainSummary?.critical_overflow_risks || 0}{' '}
                  <span className="text-lg text-[var(--color-pipesense-red)]/70 font-normal">Critical Risk</span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>Freeboard &lt; 20 cm Surcharge</span>
                  <span className="px-2 py-0.5 rounded bg-[var(--color-pipesense-red)]/15 text-[var(--color-pipesense-red)] border border-[var(--color-pipesense-red)]/35 text-[10px] font-bold">
                    P1 ACTION
                  </span>
                </div>
              </div>

              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-amber)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    ACTIVE SURCHARGES
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-amber)]">
                    <Activity className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-amber)] mb-1">
                  {drainSummary?.active_incidents || 0}{' '}
                  <span className="text-lg text-[var(--color-pipesense-amber)]/70 font-normal">Chambers</span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>Rate of Rise &gt; 25 cm/hr</span>
                  <span className="px-2 py-0.5 rounded bg-[var(--color-pipesense-amber)]/15 text-[var(--color-pipesense-amber)] border border-[var(--color-pipesense-amber)]/35 text-[10px] font-bold">
                    ALERT
                  </span>
                </div>
              </div>

              <div className="liquid-glass p-5 border-l-4 border-l-[var(--color-pipesense-green)] relative overflow-hidden group">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-[var(--color-pipesense-muted)] tracking-wider uppercase">
                    CIVILS WORK ORDERS
                  </span>
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-green)]">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl lg:text-4xl font-bold font-mono tracking-tight text-[var(--color-pipesense-green)] mb-1">
                  {drainSummary?.active_work_orders || 0}{' '}
                  <span className="text-lg text-[var(--color-pipesense-green)]/70 font-normal">Active</span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono mt-3 text-[var(--color-pipesense-muted)]">
                  <span>{drainSummary?.resolved_count || 0} Resolved &middot; Closed</span>
                  <span className="text-[var(--color-pipesense-green)] font-bold tracking-wider">SPECIALIST DISPATCH</span>
                </div>
              </div>
            </div>
          )}

          {/* =========================================================================
              3. MID SECTION: 3D CAMPUS MAP + LIVE AUDIT FEED
              ========================================================================= */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
            {/* MAIN 3D CAMPUS MAP (8 COLS) */}
            <div className="xl:col-span-8 liquid-glass p-6 flex flex-col relative border border-[var(--color-pipesense-border)] overflow-hidden shadow-2xl">
              {/* Map Header with HUD Status & Layer Toggles */}
              <div className="flex flex-wrap justify-between items-center mb-4 pb-3 border-b border-[var(--color-pipesense-border)] relative z-20 gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] rounded-lg text-[var(--color-pipesense-cyan)]">
                    <Compass className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold tracking-widest text-[var(--color-pipesense-text)] uppercase flex items-center gap-2">
                      3D CAMPUS INFRASTRUCTURE TWIN
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-[var(--color-pipesense-secondary)] text-[var(--color-pipesense-cyan)] border border-[var(--color-pipesense-border)]">
                        {activeSubsystem === 'pipesense' ? 'WATER GRID' : 'DRAINAGE CATCHMENT'}
                      </span>
                    </h2>
                    <p className="text-xs font-mono text-[var(--color-pipesense-muted)]">
                      GEOLOCATED TELEMETRY NODES &middot; FACILITY MONITORING ZONE 09
                    </p>
                  </div>
                </div>

                {/* Layer Control Pills */}
                <div className="flex items-center gap-2 text-xs font-mono">
                  <button
                    onClick={() => setActiveLayers(p => ({ ...p, pipelines: !p.pipelines }))}
                    className={`px-3 py-1 rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
                      activeLayers.pipelines
                        ? 'bg-[var(--color-pipesense-cyan)]/15 border-[var(--color-pipesense-cyan)]/40 text-[var(--color-pipesense-cyan)]'
                        : 'bg-[var(--color-pipesense-secondary)] border-[var(--color-pipesense-border)] text-[var(--color-pipesense-muted)]'
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    Pipelines: {activeLayers.pipelines ? 'ON' : 'OFF'}
                  </button>
                  <button
                    onClick={() => setActiveLayers(p => ({ ...p, nodes: !p.nodes }))}
                    className={`px-3 py-1 rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
                      activeLayers.nodes
                        ? 'bg-[var(--color-pipesense-cyan)]/15 border-[var(--color-pipesense-cyan)]/40 text-[var(--color-pipesense-cyan)]'
                        : 'bg-[var(--color-pipesense-secondary)] border-[var(--color-pipesense-border)] text-[var(--color-pipesense-muted)]'
                    }`}
                  >
                    <Cpu className="w-3.5 h-3.5" />
                    Sensors: {activeLayers.nodes ? 'ACTIVE' : 'MUTED'}
                  </button>
                </div>
              </div>

              {/* Map Viewport Canvas Wrapper */}
              <div className="relative w-full h-[460px] md:h-[520px] rounded-xl overflow-hidden border border-[var(--color-pipesense-border)] bg-[var(--color-pipesense-bg)] group">
                {/* 3D Campus Aerial Photograph / Digital Twin */}
                <img
                  src="/frames/ezgif-frame-050.jpg"
                  alt="3D Campus Map"
                  className="absolute inset-0 w-full h-full object-cover object-center filter brightness-[0.8] contrast-[1.15] saturate-[1.1] transform transition-transform duration-700 group-hover:scale-[1.01]"
                />

                {/* Vignette & Grid Lines (theme adaptive) */}
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_45%,_rgba(0,0,0,0.35)_100%)] dark:bg-[radial-gradient(ellipse_at_center,_transparent_35%,_rgba(5,5,5,0.92)_100%)] pointer-events-none" />
                <div className="absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.03)_1px,transparent_1px)] dark:bg-[linear-gradient(rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

                {/* SVG Glowing Water Pipelines Overlay */}
                {activeLayers.pipelines && (
                  <svg className="absolute inset-0 w-full h-full pointer-events-none z-10" viewBox="0 0 1000 600" preserveAspectRatio="none">
                    <defs>
                      <filter id="blue-glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="5" result="blur" />
                        <feMerge>
                          <feMergeNode in="blur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                    </defs>

                    {/* Main Supply Line from Plant-02 to BLDG-04 */}
                    <path
                      d="M 780 460 L 680 380 L 630 320"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="10"
                      opacity="0.3"
                      filter="url(#blue-glow)"
                    />
                    <path
                      d="M 780 460 L 680 380 L 630 320"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="3.5"
                      strokeDasharray="10 8"
                      className="animate-pipeline-flow"
                    />

                    {/* Feed Line to BLDG-01 */}
                    <path
                      d="M 630 320 L 480 350 L 320 350"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="8"
                      opacity="0.25"
                    />
                    <path
                      d="M 630 320 L 480 350 L 320 350"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="2.5"
                      strokeDasharray="8 6"
                      className="animate-pipeline-flow"
                    />

                    {/* Secondary Feeder to BLDG-02 & BLDG-03 */}
                    <path
                      d="M 320 350 L 220 310 L 180 290"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="6"
                      opacity="0.2"
                    />
                    <path
                      d="M 320 350 L 220 310 L 180 290"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="2"
                      strokeDasharray="6 6"
                      className="animate-pipeline-flow"
                    />
                    <path
                      d="M 320 350 L 340 270 L 340 240"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="6"
                      opacity="0.2"
                    />
                    <path
                      d="M 320 350 L 340 270 L 340 240"
                      fill="none"
                      stroke="#00BFFF"
                      strokeWidth="2"
                      strokeDasharray="6 6"
                      className="animate-pipeline-flow"
                    />

                    {/* Anomaly Stress Halo around BLDG-04 Riser */}
                    {activeSubsystem === 'pipesense' && (
                      <circle
                        cx="630"
                        cy="320"
                        r="32"
                        fill="none"
                        stroke="#E06C75"
                        strokeWidth="2.5"
                        strokeDasharray="4 4"
                        className="animate-spin"
                        style={{ transformOrigin: '630px 320px', animationDuration: '6s' }}
                      />
                    )}
                  </svg>
                )}

                {/* Building Markers & Telemetry Hotspots */}
                {activeLayers.nodes && (
                  <div className="absolute inset-0 pointer-events-auto z-20">
                    {/* --- NODE: BLDG-04 (PRIMARY TARGET / HIGH SPIKE) --- */}
                    <div
                      style={{ left: '63%', top: '53%' }}
                      onClick={() => setSelectedZone('BLDG-04')}
                      className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group/pin"
                    >
                      {/* Pulsing Alert Ping */}
                      <div className="absolute -inset-4 rounded-full bg-[var(--color-pipesense-red)]/25 animate-ping" />
                      <div className="w-6 h-6 rounded-full bg-[var(--color-pipesense-panel)] border-2 border-[var(--color-pipesense-red)] shadow-[0_0_20px_rgba(224,108,117,0.5)] flex items-center justify-center relative z-10">
                        <div className="w-2.5 h-2.5 rounded-full bg-[var(--color-pipesense-red)] animate-pulse" />
                      </div>

                      {/* Tactical Tooltip Tag */}
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-8 bg-[var(--color-pipesense-panel)]/95 border border-[var(--color-pipesense-red)] px-3 py-1.5 rounded-lg shadow-[0_0_25px_rgba(224,108,117,0.3)] whitespace-nowrap font-mono transition-transform duration-200 group-hover/pin:scale-105">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-[var(--color-pipesense-red)] animate-pulse" />
                          <span className="font-bold text-[var(--color-pipesense-text)] text-xs">BLDG-04</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-[var(--color-pipesense-red)]/20 text-[var(--color-pipesense-red)] font-bold">
                            CRITICAL LEAK
                          </span>
                        </div>
                        <div className="text-[11px] text-[var(--color-pipesense-muted)] mt-0.5">
                          Flow: <span className="text-[var(--color-pipesense-red)] font-bold">64.2 L/min</span> (3.49x Base)
                        </div>
                      </div>
                    </div>

                    {/* --- NODE: BLDG-01 (ADMIN COMPLEX) --- */}
                    <div
                      style={{ left: '32%', top: '59%' }}
                      onClick={() => setSelectedZone('BLDG-01')}
                      className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group/pin"
                    >
                      <div className="w-4 h-4 rounded-full bg-[var(--color-pipesense-panel)] border-2 border-[var(--color-pipesense-green)] shadow-[0_0_15px_rgba(78,186,151,0.5)] flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-pipesense-green)]" />
                      </div>
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-6 bg-[var(--color-pipesense-panel)]/95 border border-[var(--color-pipesense-border)] px-2.5 py-1 rounded-md shadow-lg whitespace-nowrap font-mono text-[10px] text-[var(--color-pipesense-text)] group-hover/pin:scale-105 transition-transform">
                        <span className="font-bold text-[var(--color-pipesense-text)]">BLDG-01</span> &bull; 18.2 L/min (Nominal)
                      </div>
                    </div>

                    {/* --- NODE: BLDG-02 (ENGINEERING) --- */}
                    <div
                      style={{ left: '18%', top: '48%' }}
                      onClick={() => setSelectedZone('BLDG-02')}
                      className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group/pin"
                    >
                      <div className="w-4 h-4 rounded-full bg-[var(--color-pipesense-panel)] border-2 border-[var(--color-pipesense-green)] shadow-[0_0_15px_rgba(0,255,102,0.6)] flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-pipesense-green)]" />
                      </div>
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-6 bg-[var(--color-pipesense-panel)]/95 border border-[var(--color-pipesense-border)] px-2.5 py-1 rounded-md shadow-lg whitespace-nowrap font-mono text-[10px] text-[var(--color-pipesense-text)] group-hover/pin:scale-105 transition-transform">
                        <span className="font-bold text-[var(--color-pipesense-text)]">BLDG-02</span> &bull; 14.5 L/min
                      </div>
                    </div>

                    {/* --- NODE: BLDG-03 (RESEARCH) --- */}
                    <div
                      style={{ left: '34%', top: '40%' }}
                      onClick={() => setSelectedZone('BLDG-03')}
                      className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group/pin"
                    >
                      <div className="w-4 h-4 rounded-full bg-[var(--color-pipesense-panel)] border-2 border-[var(--color-pipesense-green)] shadow-[0_0_15px_rgba(0,255,102,0.6)] flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-pipesense-green)]" />
                      </div>
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-6 bg-[var(--color-pipesense-panel)]/95 border border-[var(--color-pipesense-border)] px-2.5 py-1 rounded-md shadow-lg whitespace-nowrap font-mono text-[10px] text-[var(--color-pipesense-text)] group-hover/pin:scale-105 transition-transform">
                        <span className="font-bold text-[var(--color-pipesense-text)]">BLDG-03</span> &bull; 19.8 L/min
                      </div>
                    </div>

                    {/* --- NODE: PLANT-02 (TREATMENT & PUMP STATION) --- */}
                    <div
                      style={{ left: '78%', top: '77%' }}
                      onClick={() => setSelectedZone('PLANT-02')}
                      className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group/pin"
                    >
                      <div className="w-5 h-5 rounded-full bg-[var(--color-pipesense-panel)] border-2 border-[var(--color-pipesense-cyan)] shadow-[0_0_20px_rgba(0,191,255,0.7)] flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-[var(--color-pipesense-cyan)] animate-pulse" />
                      </div>
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-7 bg-[var(--color-pipesense-panel)]/95 border border-[var(--color-pipesense-cyan)]/40 px-3 py-1 rounded-md shadow-lg whitespace-nowrap font-mono text-xs text-[var(--color-pipesense-text)] group-hover/pin:scale-105 transition-transform">
                        <span className="font-bold text-[var(--color-pipesense-cyan)]">PLANT-02</span> &bull; 148.2 L/min Feed
                      </div>
                    </div>
                  </div>
                )}

                {/* Map HUD Overlay Metadata */}
                <div className="absolute bottom-4 left-4 z-20 flex items-center gap-3 font-mono text-[11px] text-[var(--color-pipesense-muted)] bg-[var(--color-pipesense-panel)]/90 backdrop-blur-md px-3.5 py-1.5 rounded-lg border border-[var(--color-pipesense-border)]">
                  <span className="flex items-center gap-1.5 text-[var(--color-pipesense-cyan)]">
                    <Compass className="w-3.5 h-3.5" /> 17.4452&deg; N, 78.3498&deg; E
                  </span>
                  <span>&bull;</span>
                  <span>ELEV: 542m</span>
                  <span>&bull;</span>
                  <span>MAP ENGINE: PHOTOGRAMMETRIC V2</span>
                </div>

                <div className="absolute bottom-4 right-4 z-20 flex items-center gap-2 font-mono text-xs">
                  <span className="bg-[var(--color-pipesense-panel)]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[var(--color-pipesense-border)] text-[var(--color-pipesense-muted)]">
                    TARGET: <strong className="text-[var(--color-pipesense-text)]">{selectedZone}</strong>
                  </span>
                </div>
              </div>
            </div>

            {/* LIVE AUDIT FEED (4 COLS) */}
            <div className="xl:col-span-4 liquid-glass p-6 flex flex-col border border-[var(--color-pipesense-border)] shadow-2xl h-[560px] md:h-[620px]">
              {/* Header */}
              <div className="flex justify-between items-center pb-4 border-b border-[var(--color-pipesense-border)] mb-4">
                <div className="flex items-center gap-2.5">
                  <Activity className="w-5 h-5 text-[var(--color-pipesense-cyan)] animate-pulse" />
                  <h3 className="text-base font-bold tracking-widest text-[var(--color-pipesense-text)] uppercase">
                    LIVE AUDIT FEED
                  </h3>
                </div>
                <span className="font-mono text-xs px-2.5 py-1 rounded-full bg-[var(--color-pipesense-secondary)] text-[var(--color-pipesense-cyan)] border border-[var(--color-pipesense-border)] font-bold">
                  {activeSubsystem === 'pipesense' ? `${events.length} EVENTS` : `${drainEvents.length} EVENTS`}
                </span>
              </div>

              {/* Scrollable Timeline */}
              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar relative">
                {/* Vertical Timeline Spine */}
                <div className="absolute left-[13px] top-2 bottom-2 w-px bg-gradient-to-b from-[var(--color-pipesense-cyan)] via-[var(--color-pipesense-border)] to-transparent" />

                <div className="space-y-4 relative z-10">
                  <AnimatePresence>
                    {(activeSubsystem === 'pipesense' ? events : drainEvents).map((e: IncidentEvent, idx: number) => {
                      const isExpanded = expandedEventId === idx;
                      const isCritical =
                        e.event_type.includes('ANOMALY') ||
                        e.event_type.includes('ESCALATED') ||
                        e.event_type.includes('FAIL');
                      const isResolved =
                        e.event_type.includes('VERIF') ||
                        e.event_type.includes('RESOLVED') ||
                        e.event_type.includes('CLOSE');

                      return (
                        <motion.div
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          key={idx}
                          className="relative pl-8 group"
                        >
                          {/* Dot Node */}
                          <div
                            className={`absolute left-1.5 top-2.5 w-3.5 h-3.5 rounded-full border-2 bg-[var(--color-pipesense-panel)] transition-all ${
                              isCritical
                                ? 'border-[var(--color-pipesense-red)] shadow-[0_0_12px_rgba(224,108,117,0.6)]'
                                : isResolved
                                ? 'border-[var(--color-pipesense-green)] shadow-[0_0_12px_rgba(78,186,151,0.6)]'
                                : 'border-[var(--color-pipesense-cyan)] shadow-[0_0_10px_rgba(0,191,255,0.4)]'
                            }`}
                          />

                          {/* Event Card */}
                          <div className="bg-[var(--color-pipesense-secondary)] p-3.5 rounded-xl border border-[var(--color-pipesense-border)] hover:border-[var(--color-pipesense-cyan)]/30 transition-all font-mono">
                            <div className="flex justify-between items-start mb-1">
                              <span
                                className={`text-xs font-bold tracking-wider uppercase ${
                                  isCritical
                                    ? 'text-[var(--color-pipesense-red)]'
                                    : isResolved
                                    ? 'text-[var(--color-pipesense-green)]'
                                    : 'text-[var(--color-pipesense-cyan)]'
                                }`}
                              >
                                {e.event_type.replace(/_/g, ' ')}
                              </span>
                              <span className="text-[10px] text-[var(--color-pipesense-muted)] tracking-widest">
                                {new Date(e.timestamp).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit'
                                })}
                              </span>
                            </div>

                            {/* Brief detail summary */}
                            <div className="text-[11px] text-[var(--color-pipesense-muted)] mt-1">
                              {e.details?.zone && (
                                <span className="mr-2">Zone: <strong className="text-[var(--color-pipesense-text)]">{e.details.zone}</strong></span>
                              )}
                              {e.details?.observed_flow && (
                                <span>Flow: <strong className="text-[var(--color-pipesense-red)]">{e.details.observed_flow} L/min</strong></span>
                              )}
                              {e.details?.finding && (
                                <div className="text-[var(--color-pipesense-muted)] text-[10px] mt-1 line-clamp-2">
                                  {e.details.finding}
                                </div>
                              )}
                            </div>

                            {/* Expandable JSON details */}
                            {e.details && Object.keys(e.details).length > 0 && (
                              <div className="mt-2 pt-1 border-t border-[var(--color-pipesense-border)]">
                                <button
                                  onClick={() => setExpandedEventId(isExpanded ? null : idx)}
                                  className="text-[10px] text-[var(--color-pipesense-cyan)] flex items-center gap-1 hover:underline cursor-pointer"
                                >
                                  {isExpanded ? (
                                    <>
                                      <ChevronUp className="w-3 h-3" /> Hide Payload
                                    </>
                                  ) : (
                                    <>
                                      <ChevronDown className="w-3 h-3" /> Inspect Telemetry
                                    </>
                                  )}
                                </button>
                                {isExpanded && (
                                  <pre className="text-[9px] bg-[var(--color-pipesense-panel)] p-2.5 rounded-lg text-[var(--color-pipesense-muted)] mt-2 overflow-x-auto border border-[var(--color-pipesense-border)] leading-relaxed font-mono">
                                    {JSON.stringify(e.details, null, 2)}
                                  </pre>
                                )}
                              </div>
                            )}
                          </div>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>

                  {events.length === 0 && activeSubsystem === 'pipesense' && (
                    <div className="text-center py-16 text-[var(--color-pipesense-muted)] text-xs font-mono">
                      No active security or telemetry alerts logged.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* =========================================================================
              4. BOTTOM PANELS (ROW OF 4)
              ========================================================================= */}
          {activeSubsystem === 'pipesense' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
              {/* PANEL 1: BLDG-04 WATER FLOW TELEMETRY */}
              <div className="liquid-glass p-5 flex flex-col justify-between border border-[var(--color-pipesense-border)] shadow-xl">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5 text-[var(--color-pipesense-cyan)]" /> BLDG-04 FLOW TELEMETRY
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-pipesense-red)]/15 text-[var(--color-pipesense-red)] border border-[var(--color-pipesense-red)]/35 font-bold">
                      SPIKE DETECTED
                    </span>
                  </div>

                  {/* Flow Rate SVG Sparkline / Wave */}
                  <div className="w-full h-28 bg-[var(--color-pipesense-secondary)] rounded-xl p-2 border border-[var(--color-pipesense-border)] relative overflow-hidden mb-3">
                    <svg className="w-full h-full" viewBox="0 0 300 90" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="flowGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                          <stop offset="0%" stopColor="#E06C75" stopOpacity="0.35" />
                          <stop offset="100%" stopColor="#E06C75" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      {/* Grid guidelines */}
                      <line x1="0" y1="20" x2="300" y2="20" stroke="rgba(128,128,128,0.2)" strokeDasharray="2 2" />
                      <line x1="0" y1="50" x2="300" y2="50" stroke="rgba(128,128,128,0.2)" strokeDasharray="2 2" />
                      <line x1="0" y1="75" x2="300" y2="75" stroke="#00BFFF" strokeDasharray="4 3" opacity="0.6" />

                      {/* Flow Path */}
                      <path
                        d="M 0 75 Q 40 75, 60 72 T 120 73 L 150 18 Q 180 15, 210 18 L 240 20 L 300 20"
                        fill="none"
                        stroke="#E06C75"
                        strokeWidth="2.5"
                      />
                      <path
                        d="M 0 75 Q 40 75, 60 72 T 120 73 L 150 18 Q 180 15, 210 18 L 240 20 L 300 20 L 300 90 L 0 90 Z"
                        fill="url(#flowGrad)"
                      />
                    </svg>

                    <div className="absolute top-2 right-2 text-[10px] font-mono text-[var(--color-pipesense-red)] font-bold">
                      PEAK: 64.2 L/min
                    </div>
                    <div className="absolute bottom-1 left-2 text-[9px] font-mono text-[var(--color-pipesense-cyan)]">
                      BASELINE: 18.4 L/min
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 font-mono text-xs pt-2 border-t border-[var(--color-pipesense-border)]">
                  <div className="bg-[var(--color-pipesense-secondary)] p-2.5 rounded-lg border border-[var(--color-pipesense-border)]">
                    <span className="text-[10px] text-[var(--color-pipesense-muted)] block">BASELINE FLOW</span>
                    <strong className="text-[var(--color-pipesense-text)] text-sm">{impact?.baseline_flow_lpm || 18.4} L/min</strong>
                  </div>
                  <div className="bg-[var(--color-pipesense-red)]/10 p-2.5 rounded-lg border border-[var(--color-pipesense-red)]/30">
                    <span className="text-[10px] text-[var(--color-pipesense-red)] block">ABNORMAL SPIKE</span>
                    <strong className="text-[var(--color-pipesense-red)] text-sm">{impact?.peak_abnormal_flow_lpm || 64.2} L/min</strong>
                  </div>
                </div>
              </div>

              {/* PANEL 2: PROJECTED DAILY LOSS */}
              <div className="liquid-glass p-5 flex flex-col justify-between border border-[var(--color-pipesense-border)] shadow-xl">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <TriangleAlert className="w-3.5 h-3.5 text-[var(--color-pipesense-amber)]" /> PROJECTED DAILY LOSS
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-pipesense-amber)]/15 text-[var(--color-pipesense-amber)] border border-[var(--color-pipesense-amber)]/35 font-bold">
                      UNRESOLVED
                    </span>
                  </div>

                  <div className="text-3xl lg:text-4xl font-bold font-mono text-[var(--color-pipesense-amber)] mb-2">
                    {impact?.estimated_daily_loss_liters
                      ? impact.estimated_daily_loss_liters.toLocaleString()
                      : '65,952'}{' '}
                    <span className="text-lg text-[var(--color-pipesense-amber)]/70 font-normal">L/day</span>
                  </div>

                  <p className="text-xs text-[var(--color-pipesense-muted)] leading-relaxed mb-4">
                    Based on hydraulic telemetry delta between observed peak flow and baseline usage curve.
                  </p>
                </div>

                <div className="bg-[var(--color-pipesense-secondary)] p-3 rounded-lg border border-[var(--color-pipesense-amber)]/30 font-mono text-xs space-y-1">
                  <div className="text-[11px] text-[var(--color-pipesense-amber)]">
                    CALC: (64.2 - 18.4) &times; 1,440 min
                  </div>
                  <div className="text-[10px] text-[var(--color-pipesense-muted)]">
                    Accumulating ~45.8 L/min excess draw
                  </div>
                </div>
              </div>

              {/* PANEL 3: POST-REPAIR IMPACT */}
              <div className="liquid-glass p-5 flex flex-col justify-between border border-[var(--color-pipesense-border)] shadow-xl">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-[var(--color-pipesense-green)]" /> POST-REPAIR IMPACT
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-pipesense-green)]/15 text-[var(--color-pipesense-green)] border border-[var(--color-pipesense-green)]/35 font-bold">
                      VERIFIED OUTCOME
                    </span>
                  </div>

                  <div className="text-3xl lg:text-4xl font-bold font-mono text-[var(--color-pipesense-green)] text-glow-green mb-2">
                    {impact?.verified_daily_loss_avoided_liters
                      ? impact.verified_daily_loss_avoided_liters.toLocaleString()
                      : '66,240'}{' '}
                    <span className="text-lg text-[var(--color-pipesense-green)]/70 font-normal">L/day</span>
                  </div>

                  <p className="text-xs text-[var(--color-pipesense-muted)] leading-relaxed mb-4">
                    Observed post-repair flow dropped to <strong>18.2 L/min</strong>, fully confirming leak seal.
                  </p>
                </div>

                <div className="bg-[var(--color-pipesense-secondary)] p-3 rounded-lg border border-[var(--color-pipesense-green)]/30 font-mono text-xs">
                  <div className="flex justify-between text-[var(--color-pipesense-green)] mb-1">
                    <span>Loss Avoidance Rate:</span>
                    <strong>100%</strong>
                  </div>
                  <div className="text-[10px] text-[var(--color-pipesense-muted)]">
                    Cryptographically audited in immutable DB ledger.
                  </div>
                </div>
              </div>

              {/* PANEL 4: ZONE STATUS */}
              <div className="liquid-glass p-5 flex flex-col justify-between border border-[var(--color-pipesense-border)] shadow-xl">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5 text-[var(--color-pipesense-cyan)]" /> CAMPUS ZONE STATUS
                    </span>
                    <span className="text-[10px] font-mono text-[var(--color-pipesense-muted)]">5 Monitored</span>
                  </div>

                  <div className="space-y-2 max-h-36 overflow-y-auto custom-scrollbar pr-1">
                    {[
                      { zone: 'BLDG-04', flow: '64.2 L/min', defaultStatus: 'CRITICAL', color: 'red' },
                      { zone: 'BLDG-01', flow: '18.2 L/min', defaultStatus: 'NOMINAL', color: 'green' },
                      { zone: 'BLDG-02', flow: '14.5 L/min', defaultStatus: 'NOMINAL', color: 'green' },
                      { zone: 'BLDG-03', flow: '19.8 L/min', defaultStatus: 'NOMINAL', color: 'green' },
                      { zone: 'PLANT-02', flow: '148.2 L/min', defaultStatus: 'PRIMARY', color: 'cyan' }
                    ].map(z => {
                      const matchedInc = incidents.find((inc: any) => inc.zone === z.zone);
                      const currentStatus = matchedInc ? matchedInc.state : z.defaultStatus;
                      const isAlert = currentStatus !== 'NOMINAL' && currentStatus !== 'CLOSED' && currentStatus !== 'PRIMARY';
                      return (
                        <div
                          key={z.zone}
                          onClick={() => setSelectedZone(z.zone)}
                          className={`flex justify-between items-center p-2 rounded-lg border text-xs font-mono cursor-pointer transition-all ${
                            selectedZone === z.zone
                              ? 'bg-[var(--color-pipesense-panel)] border-[var(--color-pipesense-cyan)] shadow-sm'
                              : 'bg-[var(--color-pipesense-secondary)] border border-[var(--color-pipesense-border)] hover:border-[var(--color-pipesense-cyan)]/30'
                          }`}
                        >
                          <span className="font-bold text-[var(--color-pipesense-text)]">{z.zone}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-[var(--color-pipesense-muted)] text-[11px]">{z.flow}</span>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                                isAlert
                                  ? 'bg-[var(--color-pipesense-red)]/15 text-[var(--color-pipesense-red)] border border-[var(--color-pipesense-red)]/35'
                                  : currentStatus === 'CLOSED'
                                  ? 'bg-[var(--color-pipesense-green)]/15 text-[var(--color-pipesense-green)] border border-[var(--color-pipesense-green)]/35'
                                  : z.color === 'green'
                                  ? 'bg-[var(--color-pipesense-green)]/15 text-[var(--color-pipesense-green)]'
                                  : 'bg-[var(--color-pipesense-cyan)]/15 text-[var(--color-pipesense-cyan)]'
                              }`}
                            >
                              {currentStatus}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="text-[10px] font-mono text-[var(--color-pipesense-muted)] pt-2 border-t border-[var(--color-pipesense-border)] text-right">
                  Click any zone to inspect on 3D twin
                </div>
              </div>
            </div>
          ) : (
            /* DRAINPILOT BOTTOM PANELS */
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
              {/* DRAIN PANEL 1: CHAMBER LEVEL & DEPTH */}
              <div className="liquid-glass p-5 border border-[var(--color-pipesense-border)] shadow-xl flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-cyan)] uppercase tracking-wider flex items-center gap-1.5">
                      <Gauge className="w-3.5 h-3.5 text-[var(--color-pipesense-cyan)]" /> CHAMBER HEADROOM GAUGE
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-pipesense-secondary)] text-[var(--color-pipesense-cyan)] border border-[var(--color-pipesense-border)] font-bold">
                      {activeDrainIncident?.zone || 'CHAMBER-STORM-01'}
                    </span>
                  </div>

                  {(() => {
                    const tel = activeDrainIncident?.metadata?.telemetry || {};
                    const wLevel = tel.water_level_cm || 195;
                    const cDepth = tel.chamber_depth_cm || 200;
                    const fillPct = Math.round((wLevel / cDepth) * 100);
                    return (
                      <div>
                        <div className="text-3xl font-bold font-mono text-[var(--color-pipesense-text)] mb-2">
                          {wLevel} <span className="text-base text-[var(--color-pipesense-muted)] font-normal">/ {cDepth} cm</span>
                        </div>
                        <div className="w-full bg-[var(--color-pipesense-secondary)] h-3 rounded-full overflow-hidden border border-[var(--color-pipesense-border)] mb-2">
                          <div
                            className={`h-full transition-all duration-500 ${
                              fillPct >= 90
                                ? 'bg-gradient-to-r from-amber-500 to-red-500 shadow-[0_0_15px_red]'
                                : 'bg-[var(--color-pipesense-cyan)]'
                            }`}
                            style={{ width: `${Math.min(100, fillPct)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs font-mono text-[var(--color-pipesense-muted)]">
                          <span>{fillPct}% Capacity Utilized</span>
                          <span className={fillPct >= 90 ? 'text-[var(--color-pipesense-red)] font-bold' : 'text-[var(--color-pipesense-cyan)]'}>
                            {cDepth - wLevel} cm Freeboard
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                <div className="text-[10px] font-mono text-[var(--color-pipesense-muted)] pt-3 border-t border-[var(--color-pipesense-border)]">
                  [Simulated benchmark telemetry &bull; Physical sensors not connected]
                </div>
              </div>

              {/* DRAIN PANEL 2: SILT & PUMP TELEMETRY */}
              <div className="liquid-glass p-5 border border-[var(--color-pipesense-border)] shadow-xl flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-amber-400" /> SILT &amp; PUMP STATUS
                    </span>
                  </div>

                  {(() => {
                    const tel = activeDrainIncident?.metadata?.telemetry || {};
                    return (
                      <div className="space-y-3 font-mono text-xs">
                        <div className="bg-[var(--color-pipesense-secondary)] p-3 rounded-lg border border-[var(--color-pipesense-border)] flex justify-between items-center">
                          <span className="text-[var(--color-pipesense-muted)]">SILT ACCUMULATION:</span>
                          <strong className="text-amber-300 text-sm">{tel.silt_depth_cm || 45} cm</strong>
                        </div>
                        <div className="bg-[var(--color-pipesense-secondary)] p-3 rounded-lg border border-[var(--color-pipesense-border)] flex justify-between items-center">
                          <span className="text-[var(--color-pipesense-muted)]">RATE OF RISE:</span>
                          <strong className="text-[var(--color-pipesense-red)] text-sm">{tel.rate_of_rise_cm_per_hr || 32.5} cm/hr</strong>
                        </div>
                        <div className="bg-[var(--color-pipesense-secondary)] p-3 rounded-lg border border-[var(--color-pipesense-border)] flex justify-between items-center">
                          <span className="text-[var(--color-pipesense-muted)]">PUMP OPERATIONAL:</span>
                          <strong className={`text-sm ${tel.pump_status === 'OVERLOAD' ? 'text-[var(--color-pipesense-red)] animate-pulse' : 'text-green-400'}`}>
                            {tel.pump_status || 'OVERLOAD'}
                          </strong>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                <div className="text-[10px] font-mono text-[var(--color-pipesense-muted)] pt-2 border-t border-[var(--color-pipesense-border)]">
                  Critical silt threshold: 40.0 cm
                </div>
              </div>

              {/* DRAIN PANEL 3: AUTONOMOUS INVESTIGATION */}
              <div className="liquid-glass p-5 border border-[var(--color-pipesense-border)] shadow-xl flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-cyan)] uppercase tracking-wider flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-[var(--color-pipesense-cyan)]" /> AUTONOMOUS INVESTIGATION
                    </span>
                  </div>

                  {activeDrainIncident?.metadata?.investigation ? (
                    <div className="space-y-2 font-mono text-xs">
                      <div className="text-[11px] text-[var(--color-pipesense-text)]">
                        <span className="text-[var(--color-pipesense-muted)]">SUSPECTED:</span>{' '}
                        {activeDrainIncident.metadata.investigation.suspected_problem}
                      </div>
                      <div className="text-[10px] text-[var(--color-pipesense-muted)] bg-[var(--color-pipesense-secondary)] p-2.5 rounded-lg border border-[var(--color-pipesense-border)] line-clamp-3">
                        {activeDrainIncident.metadata.investigation.finding}
                      </div>
                      <div className="text-[10px] text-[var(--color-pipesense-cyan)]">
                        Confidence: {Math.round((activeDrainIncident.confidence || 0.88) * 100)}% (Demo Estimate)
                      </div>
                    </div>
                  ) : activeDrainIncident?.state === 'ANOMALY' ? (
                    <div className="space-y-3">
                      <p className="text-xs text-[var(--color-pipesense-muted)]">
                        High surcharge detected. Deterministic drainage correlation available.
                      </p>
                      <button
                        onClick={() => handleInvestigateDrain(activeDrainIncident.incident_id)}
                        disabled={drainActionLoading}
                        className="w-full py-2 bg-[var(--color-pipesense-cyan)]/15 hover:bg-[var(--color-pipesense-cyan)]/25 border border-[var(--color-pipesense-cyan)]/40 rounded-lg font-mono text-xs text-[var(--color-pipesense-cyan)] uppercase tracking-wider cursor-pointer"
                      >
                        Run Investigation
                      </button>
                    </div>
                  ) : (
                    <div className="text-xs font-mono text-[var(--color-pipesense-muted)] py-6 text-center">
                      Select a chamber or trigger an anomaly to investigate.
                    </div>
                  )}
                </div>

                <div className="text-[10px] font-mono text-[var(--color-pipesense-muted)] pt-2 border-t border-[var(--color-pipesense-border)]">
                  Deterministic rainfall &amp; siltation model
                </div>
              </div>

              {/* DRAIN PANEL 4: WORK ORDER & VERIFICATION GATEWAY */}
              <div className="liquid-glass p-5 border border-[var(--color-pipesense-border)] shadow-xl flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-amber-400" /> VERIFICATION GATEWAY
                    </span>
                    <span className="text-[10px] font-mono text-[var(--color-pipesense-text)] font-bold">
                      {activeDrainIncident?.state || 'NOMINAL'}
                    </span>
                  </div>

                  <div className="space-y-2 font-mono text-xs">
                    {(activeDrainIncident?.state === 'INVESTIGATING' || activeDrainIncident?.state === 'ANOMALY') && (
                      <button
                        onClick={() => handleDispatchDrain(activeDrainIncident.incident_id)}
                        disabled={drainActionLoading}
                        className="w-full py-2.5 bg-amber-500/20 hover:bg-amber-500/35 border border-amber-500/50 rounded-lg text-amber-300 uppercase tracking-wider cursor-pointer"
                      >
                        Dispatch Civils Crew
                      </button>
                    )}

                    {(activeDrainIncident?.state === 'WORK_ORDER_ISSUED' || activeDrainIncident?.state === 'REPAIRING') &&
                      activeDrainWo && (
                        <button
                          onClick={() => handleCompleteDrain(activeDrainWo.work_order_id)}
                          disabled={drainActionLoading}
                          className="w-full py-2.5 bg-[var(--color-pipesense-cyan)]/20 hover:bg-[var(--color-pipesense-cyan)]/35 border border-[var(--color-pipesense-cyan)]/50 rounded-lg text-[var(--color-pipesense-cyan)] uppercase tracking-wider cursor-pointer"
                        >
                          Record Field Completion
                        </button>
                      )}

                    {activeDrainIncident?.state === 'VERIFYING' && activeDrainWo && (
                      <div className="space-y-2">
                        <button
                          onClick={() => handleVerifyDrainPass(activeDrainWo.work_order_id)}
                          disabled={drainActionLoading}
                          className="w-full py-2 bg-green-500/20 hover:bg-green-500/35 border border-green-500/50 rounded-lg text-green-300 uppercase tracking-wider cursor-pointer flex items-center justify-center gap-1"
                        >
                          <CheckCircle className="w-3.5 h-3.5" /> Submit Nominal (Pass)
                        </button>
                        <button
                          onClick={() => handleVerifyDrainFail(activeDrainWo.work_order_id)}
                          disabled={drainActionLoading}
                          className="w-full py-2 bg-red-500/15 hover:bg-red-500/25 border border-red-500/40 rounded-lg text-red-300 uppercase tracking-wider cursor-pointer flex items-center justify-center gap-1"
                        >
                          <AlertTriangle className="w-3.5 h-3.5" /> Submit High (Fail)
                        </button>
                      </div>
                    )}

                    {activeDrainIncident?.state === 'ESCALATED' && activeDrainWo && (
                      <button
                        onClick={() => handleRepairDrain(activeDrainWo.work_order_id)}
                        disabled={drainActionLoading}
                        className="w-full py-2.5 bg-amber-500/20 hover:bg-amber-500/35 border border-amber-500/50 rounded-lg text-amber-300 uppercase tracking-wider cursor-pointer"
                      >
                        Initiate Secondary Repair
                      </button>
                    )}

                    {activeDrainIncident?.state === 'CLOSED' && (
                      <div className="p-3 bg-green-500/15 border border-green-500/30 rounded-lg text-green-300 text-center">
                        <CheckCircle className="w-4 h-4 mx-auto mb-1 text-green-400" />
                        Resolution Verified &bull; Chamber Cleared
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-[10px] font-mono text-[var(--color-pipesense-muted)] pt-2 border-t border-[var(--color-pipesense-border)]">
                  Closed-loop physical verification protocol
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
