import { useState, useEffect } from 'react';
import { fetchThresholds, fetchAgentStatus, type ThresholdsConfig, type AgentStatus } from '../lib/api';
import { Settings, Cpu, Sliders, Info, Lock } from 'lucide-react';

export default function SettingsView() {
  const [thresholds, setThresholds] = useState<ThresholdsConfig | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [thresh, agent] = await Promise.all([fetchThresholds(), fetchAgentStatus()]);
        setThresholds(thresh);
        setAgentStatus(agent);
      } catch (err) {
        console.error('Failed to load settings', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="p-8 text-[var(--color-pipesense-muted)]">Loading system configuration...</div>;
  }

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-auto custom-scrollbar">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <Settings className="w-6 h-6 text-[var(--color-pipesense-cyan)]" />
          <h1 className="text-2xl font-hud font-bold text-[var(--color-pipesense-cyan)]">ADMINISTRATION & THRESHOLDS</h1>
        </div>
        <p className="text-sm text-[var(--color-pipesense-muted)] mt-1">
          Operational anomaly thresholds, verification bounds, and transparent agent runtime disclosure.
        </p>
      </div>

      {/* Grid: 2 Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column 1: Operational Anomaly Thresholds */}
        <div className="bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--color-pipesense-border)]">
            <div className="flex items-center gap-2">
              <Sliders className="w-5 h-5 text-[var(--color-pipesense-cyan)]" />
              <h2 className="font-hud font-bold text-sm tracking-wider uppercase text-white">DETECTION THRESHOLDS</h2>
            </div>
            <span className="flex items-center gap-1 text-[11px] font-mono text-[var(--color-pipesense-muted)]">
              <Lock className="w-3 h-3" /> Enforced by Service Layer
            </span>
          </div>

          <div className="space-y-4 font-mono text-xs">
            <div className="p-3 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-lg flex justify-between items-center">
              <div>
                <span className="text-white font-bold block">Night Anomaly Threshold</span>
                <span className="text-[var(--color-pipesense-muted)] text-[11px]">Flow multiplier above baseline to flag an anomaly</span>
              </div>
              <div className="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded font-bold">
                {thresholds?.anomaly_multiplier_threshold || 1.35}x
              </div>
            </div>

            <div className="p-3 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-lg flex justify-between items-center">
              <div>
                <span className="text-white font-bold block">Critical Leak Threshold</span>
                <span className="text-[var(--color-pipesense-muted)] text-[11px]">Ratio triggering immediate P1 Priority Work Order dispatch</span>
              </div>
              <div className="px-3 py-1 bg-red-500/20 text-red-300 border border-red-500/30 rounded font-bold">
                {thresholds?.critical_leak_multiplier || 3.0}x
              </div>
            </div>

            <div className="p-3 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-lg flex justify-between items-center">
              <div>
                <span className="text-white font-bold block">Repair Verification Tolerance</span>
                <span className="text-[var(--color-pipesense-muted)] text-[11px]">Maximum post-repair flow allowed to accept ticket closure</span>
              </div>
              <div className="px-3 py-1 bg-green-500/20 text-green-300 border border-green-500/30 rounded font-bold">
                &le; {thresholds?.verification_tolerance_multiplier || 1.35}x baseline
              </div>
            </div>

            <div className="p-3 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-lg flex justify-between items-center">
              <div>
                <span className="text-white font-bold block">Night Sleep Window</span>
                <span className="text-[var(--color-pipesense-muted)] text-[11px]">Campus resting period monitored for low-flow baseline</span>
              </div>
              <div className="px-3 py-1 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded font-bold">
                {thresholds?.night_flow_window || '01:00 - 05:00 IST'}
              </div>
            </div>
          </div>
        </div>

        {/* Column 2: Truthful Agent Runtime Status */}
        <div className="bg-[var(--color-pipesense-panel)] border border-[var(--color-pipesense-border)] rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--color-pipesense-border)]">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-[var(--color-pipesense-cyan)]" />
              <h2 className="font-hud font-bold text-sm tracking-wider uppercase text-white">AGENT RUNTIME & CLOUD INTEGRATION</h2>
            </div>
            <span className="px-2 py-0.5 rounded bg-[var(--color-pipesense-cyan)]/20 text-[var(--color-pipesense-cyan)] text-[10px] font-mono font-bold">
              TRUTHFUL STATUS
            </span>
          </div>

          {/* Status Banner */}
          <div className="p-4 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-xl space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center">
              <span className="text-[var(--color-pipesense-muted)]">ACTIVE AGENT MODE:</span>
              <span className={`px-2.5 py-1 rounded font-bold border ${
                agentStatus?.status_key === 'bedrock_active' || agentStatus?.bedrock_enabled ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
                agentStatus?.status_key === 'bedrock_configured_unverified' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
                agentStatus?.status_key === 'bedrock_unavailable' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
                'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
              }`}>
                {agentStatus?.status_text || 'Local Demo Mode'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--color-pipesense-muted)]">PROVIDER:</span>
              <span className="text-white font-medium">{agentStatus?.provider || 'Local Deterministic Engine'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--color-pipesense-muted)]">BEDROCK MODEL:</span>
              <span className="text-white font-medium">{agentStatus?.model_id || 'N/A (Local Engine)'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--color-pipesense-muted)]">AWS REGION:</span>
              <span className="text-white font-medium">{agentStatus?.region || 'N/A (Local Engine)'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--color-pipesense-muted)]">BEDROCK VERIFIED:</span>
              <span className={`font-bold ${agentStatus?.bedrock_enabled ? 'text-emerald-400' : 'text-[var(--color-pipesense-muted)]'}`}>
                {agentStatus?.bedrock_enabled ? 'YES (Live Cloud Verified)' : agentStatus?.bedrock_configured ? 'PENDING INVOCATION' : 'NO (Offline Local Mode)'}
              </span>
            </div>
            {agentStatus?.error_reason && (
              <div className="mt-2 p-2.5 bg-rose-500/10 border border-rose-500/30 rounded text-rose-300 text-[11px]">
                <span className="font-bold">Error Notice:</span> {agentStatus.error_reason}
              </div>
            )}
          </div>

          {/* Architecture & Verification Notice */}
          <div className="p-4 bg-cyan-500/10 border border-cyan-500/30 rounded-xl space-y-2 text-xs">
            <div className="flex items-center gap-2 font-bold text-[var(--color-pipesense-cyan)]">
              <Info className="w-4 h-4 flex-shrink-0" />
              Agent Architecture & Fallback Disclosure
            </div>
            <p className="text-[var(--color-pipesense-muted)] leading-relaxed">
              PipeSense features an autonomous resilience agent integrating the <strong>Strands Agents SDK</strong> and Amazon Bedrock with 4 registered investigation tools
              (<code className="text-white">check_weather</code>, <code className="text-white">check_peer_baselines</code>, <code className="text-white">check_maintenance_history</code>, <code className="text-white">check_occupancy</code>).
            </p>
            <p className="text-[var(--color-pipesense-muted)] leading-relaxed">
              <strong>Live Verification Status:</strong> The Bedrock code path is implemented in the codebase, but has <strong>not been live-verified</strong> against live AWS services unless a real Bedrock invocation has succeeded. The app operates in <strong>Local Demo Mode</strong> by default. Bedrock is never reported as active based only on environment variables or mock test runs. When Bedrock is enabled, it automatically falls back to local deterministic execution if cloud connectivity is unverified, misconfigured, or unavailable.
            </p>
          </div>

          {/* Cloud Configuration Reference */}
          <div className="p-4 bg-[var(--color-pipesense-bg)] border border-[var(--color-pipesense-border)] rounded-xl space-y-2 text-xs font-mono">
            <div className="text-white font-bold">Server-Side Configuration:</div>
            <p className="text-[var(--color-pipesense-muted)] text-[11px] leading-relaxed">
              AWS access is managed exclusively server-side via environment variables (<code className="text-[var(--color-pipesense-cyan)]">USE_AWS_BEDROCK</code>, <code className="text-[var(--color-pipesense-cyan)]">AWS_REGION</code>, <code className="text-[var(--color-pipesense-cyan)]">BEDROCK_MODEL_ID</code>) and IAM credentials. Cloud credentials are never exposed to the client interface or web bundles.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
