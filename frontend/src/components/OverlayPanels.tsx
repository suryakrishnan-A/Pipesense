import { motion, MotionValue, useTransform } from 'framer-motion';
import { AlertTriangle, Droplet, Search, ShieldCheck, Wrench, ArrowRight, Activity, CheckCircle2 } from 'lucide-react';

export default function OverlayPanels({
  scrollProgress,
  onInspect
}: {
  scrollProgress: MotionValue<number>;
  onInspect: () => void;
}) {
  // Safe helper to map scroll to opacity using strictly increasing offsets
  const useStageOpacity = (start: number, end: number) => {
    let p1 = Math.max(0, start - 0.05);
    let p2 = Math.max(0, start);
    let p3 = Math.min(1, end);
    let p4 = Math.min(1, end + 0.05);

    // Ensure strict monotonicity for WAAPI
    if (p2 <= p1) p2 = p1 + 0.01;
    if (p3 <= p2) p3 = p2 + 0.01;
    if (p4 <= p3) p4 = p3 + 0.01;
    if (p4 > 1) p4 = 1;
    if (p3 >= p4) p3 = p4 - 0.01;

    return useTransform(scrollProgress, [p1, p2, p3, p4], [0, 1, 1, 0]);
  };

  const o1 = useStageOpacity(0, 0.10); // Scene 1: City Aerial
  const o2 = useStageOpacity(0.12, 0.22); // Scene 2: Campus Focus
  const o3 = useStageOpacity(0.24, 0.38); // Scene 3: Building Cutaway
  const o4 = useStageOpacity(0.40, 0.53); // Scene 4: Reveal Pipe Network

  // Combined Stages 05 & 06 window (0.54 to 0.79)
  const o56 = useTransform(scrollProgress, [0.52, 0.55, 0.78, 0.81], [0, 1, 1, 0]);

  // Stage 05 prominence: high when scroll is 0.55-0.66, then fades to subdued when 0.68+
  const o5_prominence = useTransform(scrollProgress, [0.54, 0.65, 0.68], [1, 1, 0.45]);
  const o5_scale = useTransform(scrollProgress, [0.54, 0.65, 0.68], [1, 1, 0.98]);

  // Stage 06 prominence: subdued early (0.55-0.65), then becomes prominent (0.68-0.79)
  const o6_prominence = useTransform(scrollProgress, [0.65, 0.68, 0.78], [0.45, 1, 1]);
  const o6_scale = useTransform(scrollProgress, [0.65, 0.68, 0.78], [0.98, 1, 1]);

  const o7 = useStageOpacity(0.82, 0.92); // Scene 7: Verification
  const o8 = useTransform(scrollProgress, [0.92, 1], [0, 1]); // Scene 8: Dashboard

  // Reusable Liquid Glass card container class matching Apple iPhone translucent design
  const cardClass =
    'liquid-glass p-6 md:p-8 rounded-[24px] md:rounded-[28px] pointer-events-auto transition-all duration-300';

  return (
    <div className="absolute inset-0 pointer-events-none p-5 sm:p-6 md:p-12 flex flex-col justify-center">
      {/* Persistent Brand Header - Liquid Glass Pill */}
      <div className="absolute top-5 left-5 md:top-8 md:left-8 flex items-center space-x-3 pointer-events-auto bg-[#0A0A0A]/60 backdrop-blur-2xl px-4 py-2 rounded-full border border-white/10 border-t-white/20 shadow-[0_12px_30px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.15)] z-30">
        <Droplet className="w-5 h-5 md:w-6 md:h-6 text-[#00BFFF]" />
        <h1 className="text-lg md:text-xl font-bold tracking-[0.2em] text-[#F5F5F5] font-hud">
          PIPESENSE
        </h1>
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#00BFFF]/15 text-[#00BFFF] border border-[#00BFFF]/30 ml-2 hidden sm:inline-block">
          OPS COMMAND
        </span>
      </div>

      {/* SCENE 1 — CITY AERIAL (0–10%) */}
      <motion.div
        style={{ opacity: o1 }}
        className={`absolute left-[5%] md:left-[8%] top-[12%] md:top-[15%] max-w-[calc(100vw-2.5rem)] md:max-w-md ${cardClass}`}
      >
        <div className="text-[11px] font-mono text-pipesense-cyan tracking-[0.2em] uppercase mb-2 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" /> STAGE 01 // OVERVIEW
        </div>
        <h3 className="text-2xl md:text-3xl font-bold mb-3 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] leading-tight">
          Every Drop Lost Is a Problem Left Undetected.
        </h3>
        <p className="text-[#D1D5DB] text-sm md:text-base leading-relaxed drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
          Water infrastructure can develop leaks long before visible damage appears.
          Manual inspections and disconnected maintenance records delay detection and response.
        </p>
      </motion.div>

      {/* SCENE 2 — CAMPUS FOCUS (10–22%) */}
      <motion.div
        style={{ opacity: o2 }}
        className={`absolute right-[5%] md:right-[8%] bottom-[15%] md:bottom-[20%] max-w-[calc(100vw-2.5rem)] md:max-w-md ${cardClass}`}
      >
        <div className="text-[11px] font-mono text-pipesense-cyan tracking-[0.2em] uppercase mb-2 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" /> STAGE 02 // COORDINATION
        </div>
        <h3 className="text-2xl md:text-3xl font-bold mb-3 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] leading-tight">
          Finding a Leak Is Only the Beginning.
        </h3>
        <p className="text-[#D1D5DB] text-sm md:text-base leading-relaxed drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
          Detection, investigation, maintenance, and verification must work seamlessly together to resolve an incident with certainty.
        </p>
      </motion.div>

      {/* SCENE 3 — BUILDING CUTAWAY (22–38%) */}
      <motion.div
        style={{ opacity: o3 }}
        className={`absolute left-[5%] md:left-[10%] top-[25%] md:top-[30%] max-w-[calc(100vw-2.5rem)] md:max-w-md ${cardClass}`}
      >
        <div className="text-[11px] font-mono text-pipesense-cyan tracking-[0.2em] uppercase mb-2 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" /> STAGE 03 // INFRASTRUCTURE
        </div>
        <h3 className="text-2xl md:text-3xl font-bold mb-3 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] leading-tight">
          Look Beyond the Surface.
        </h3>
        <p className="text-[#D1D5DB] text-sm md:text-base leading-relaxed mb-5 drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
          Continuous telemetry tracks water delivery through every riser, joint, and distribution main in real time.
        </p>
        <div className="font-mono liquid-glass-inner p-4 text-xs space-y-2.5">
          <div className="flex justify-between items-center">
            <span className="text-[#9CA3AF]">FACILITY ZONE:</span>
            <span className="text-pipesense-cyan font-bold tracking-wider">BLDG-04</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#9CA3AF]">TELEMETRY UPLINK:</span>
            <span className="text-pipesense-green font-bold tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-pipesense-green animate-pulse" /> ACTIVE
            </span>
          </div>
        </div>
      </motion.div>

      {/* SCENE 4 — REVEAL THE PIPE NETWORK (38–53%) */}
      <motion.div
        style={{ opacity: o4 }}
        className={`absolute right-[5%] md:right-[10%] bottom-[12%] md:bottom-[15%] max-w-[calc(100vw-2.5rem)] md:max-w-md ${cardClass}`}
      >
        <div className="text-[11px] font-mono text-pipesense-red tracking-[0.2em] uppercase mb-2 flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-pipesense-red animate-pulse" /> STAGE 04 // ANOMALY DETECTED
        </div>
        <h3 className="text-2xl md:text-3xl font-bold mb-4 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] leading-tight flex items-center gap-2">
          One Unusual Reading. A Focused Investigation.
        </h3>
        <div className="font-mono liquid-glass-red p-4.5 text-xs space-y-2.5 mb-3">
          <div className="flex justify-between items-center text-slate-300">
            <span className="text-[#9CA3AF]">BASELINE FLOW:</span>
            <span className="font-bold text-white">18.4 L/min</span>
          </div>
          <div className="flex justify-between items-center text-pipesense-red text-base font-bold">
            <span className="text-[#FCA5A5]">ABNORMAL FLOW:</span>
            <span className="text-glow-red text-white">64.2 L/min</span>
          </div>
          <div className="flex justify-between items-center pt-2 border-t border-red-500/25">
            <span className="text-[#9CA3AF]">DEVIATION:</span>
            <span className="text-pipesense-amber font-bold">3.49x BASELINE (HIGH)</span>
          </div>
        </div>
        <p className="text-[11px] text-slate-400 font-mono italic">
          * Simulated telemetry anomaly detected in BLDG-04 Riser
        </p>
      </motion.div>

      {/* SCENES 05 & 06 — DUAL SIDE-BY-SIDE BALANCED LIQUID GLASS PANELS (54–79%) */}
      <motion.div
        style={{ opacity: o56 }}
        className="absolute inset-x-4 sm:inset-x-8 md:inset-x-12 lg:inset-x-16 bottom-[8%] md:bottom-[12%] flex items-end justify-center pointer-events-none z-20"
      >
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-5 md:gap-7 items-stretch">
          {/* STAGE 05 — AUTONOMOUS AGENT INVESTIGATION */}
          <motion.div
            style={{ opacity: o5_prominence, scale: o5_scale }}
            className="liquid-glass p-6 md:p-8 rounded-[24px] md:rounded-[28px] pointer-events-auto flex flex-col justify-between transition-all duration-300"
          >
            <div>
              <div className="text-[11px] font-mono text-pipesense-cyan tracking-[0.2em] uppercase mb-2 flex items-center gap-2">
                <Search className="w-3.5 h-3.5 text-pipesense-cyan" /> STAGE 05 // AUTONOMOUS AGENT
              </div>
              <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] leading-tight mb-4">
                Context Turns an Alert Into an Informed Decision.
              </h2>

              {/* Nested Dark Telemetry Data Card */}
              <div className="space-y-2.5 font-mono text-xs mb-4 liquid-glass-inner p-4.5">
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF] tracking-wider">WEATHER:</span>
                  <span className="text-white font-medium">Clear &middot; Irrigation Off</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF] tracking-wider">PEER RISERS:</span>
                  <span className="text-white font-medium">Nominal (1.0x baseline)</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF] tracking-wider">MAINTENANCE HISTORY:</span>
                  <span className="text-amber-300 font-medium flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    Fissure stress logged
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF] tracking-wider">BUILDING OCCUPANCY:</span>
                  <span className="text-white font-medium">Rest hours (0 events)</span>
                </div>
              </div>
            </div>

            {/* Subtle Divider & Agent Diagnosis with Cyan Highlight */}
            <div className="border-t border-white/10 pt-3.5 mt-auto">
              <div className="liquid-glass-cyan p-4">
                <div className="text-xs font-mono text-slate-200 leading-relaxed">
                  <span className="text-pipesense-cyan font-bold tracking-wider mr-2 uppercase">AGENT DIAGNOSIS:</span>
                  Abnormal spike confirmed with high confidence. Acoustic and telemetry correlation confirms physical pipe rupture.
                </div>
              </div>
            </div>
          </motion.div>

          {/* STAGE 06 — WORK ORDER DISPATCH & RESPONSE */}
          <motion.div
            style={{ opacity: o6_prominence, scale: o6_scale }}
            className="liquid-glass p-6 md:p-8 rounded-[24px] md:rounded-[28px] pointer-events-auto flex flex-col justify-between transition-all duration-300"
          >
            <div>
              <div className="text-[11px] font-mono text-pipesense-cyan tracking-[0.2em] uppercase mb-2 flex items-center gap-2">
                <Wrench className="w-3.5 h-3.5 text-pipesense-cyan" /> STAGE 06 // WORK ORDER DISPATCH
              </div>
              <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] leading-tight mb-4">
                From Scattered Evidence to an Actionable Response.
              </h2>

              {/* Nested Dark Work Order Details Card */}
              <div className="liquid-glass-inner p-5 space-y-3 font-mono text-xs mb-4">
                <div className="flex justify-between text-slate-400 border-b border-white/10 pb-2">
                  <span className="text-[#9CA3AF]">INCIDENT ID:</span>
                  <span className="text-white font-bold tracking-wider">INC-DEMO-04</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF]">LOCATION:</span>
                  <span className="text-white font-medium">BLDG-04 Riser</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF]">PRIORITY:</span>
                  <span className="text-pipesense-red font-bold px-2 py-0.5 rounded bg-red-500/10 border border-red-500/30">
                    P1 - HIGH
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF]">STATUS:</span>
                  <span className="text-pipesense-amber font-bold flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                    WORK ORDER ISSUED
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#9CA3AF]">ASSIGNED:</span>
                  <span className="text-white font-medium">Tech Ops (Local Plumbers)</span>
                </div>
              </div>
            </div>

            {/* Subtle Divider & Operational Directive */}
            <div className="border-t border-white/10 pt-3.5 mt-auto">
              <div className="bg-[#0A0A0A]/60 backdrop-blur-md border border-white/10 p-4 rounded-xl text-xs font-mono text-slate-300 flex items-center justify-between">
                <span className="text-[#9CA3AF]">TARGET RESPONSE:</span>
                <span className="text-pipesense-green font-bold">15 MIN SLA &middot; TICKET LOCKED</span>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* SCENE 7 — REPAIR VERIFICATION (80–92%) */}
      <motion.div
        style={{ opacity: o7 }}
        className={`absolute left-5 sm:left-8 md:left-16 lg:left-20 top-1/4 md:top-1/4 max-w-[calc(100vw-2.5rem)] md:max-w-md ${cardClass}`}
      >
        <div className="text-[11px] font-mono text-pipesense-green tracking-[0.2em] uppercase mb-2 flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-pipesense-green" /> STAGE 07 // RESOLUTION VERIFICATION
        </div>
        <h3 className="text-2xl md:text-3xl font-bold mb-4 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] leading-tight">
          Never Confuse 'Marked Complete' With 'Fixed.'
        </h3>
        <div className="space-y-3 font-mono text-xs">
          {/* Failed Verif */}
          <div className="liquid-glass-amber p-4">
            <div className="text-xs text-amber-300 font-bold mb-2 flex items-center gap-2">
              <Wrench className="w-3.5 h-3.5" /> ATTEMPT 1: FAILED VERIFICATION
            </div>
            <div className="flex justify-between mb-1 text-slate-300">
              <span className="text-[#9CA3AF]">OBSERVED FLOW:</span>
              <span className="text-pipesense-red font-bold">61.8 L/min</span>
            </div>
            <div className="text-[10px] text-slate-400 border-t border-amber-500/20 pt-1 mt-1">
              ACTION: ESCALATION ISSUED &middot; SUPERVISOR REASSIGNED
            </div>
          </div>

          {/* Success Verif */}
          <div className="liquid-glass-green p-4">
            <div className="text-xs text-green-300 font-bold mb-2 flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5" /> ATTEMPT 2: VERIFIED DRAWDOWN
            </div>
            <div className="flex justify-between mb-1 text-slate-300">
              <span className="text-[#9CA3AF]">OBSERVED FLOW:</span>
              <span className="text-pipesense-green font-bold text-sm">18.2 L/min</span>
            </div>
            <div className="flex justify-between text-slate-400 text-[10px]">
              <span>BASELINE EXPECTED:</span>
              <span>18.4 L/min</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* SCENE 8 — REASSEMBLE AND DASHBOARD (92–100%) */}
      <motion.div
        style={{ opacity: o8 }}
        className="absolute inset-0 flex flex-col items-center justify-center pointer-events-auto bg-[#050505]/75 backdrop-blur-xl px-5 sm:px-6 z-30"
      >
        <div className="max-w-2xl text-center liquid-glass p-8 sm:p-10 md:p-14">
          <div className="text-xs font-mono text-[#00BFFF] tracking-[0.25em] uppercase mb-3 flex items-center justify-center gap-2">
            <Activity className="w-4 h-4 text-[#00BFFF]" /> UNIFIED ENVIRONMENTAL OPERATIONS
          </div>
          <h2 className="text-2xl sm:text-3xl md:text-5xl font-bold mb-5 text-[#F5F5F5] tracking-wide drop-shadow-[0_2px_10px_rgba(0,0,0,0.9)] leading-tight">
            Your Campus. Your Incidents. One Operational View.
          </h2>
          <p className="text-[#D1D5DB] text-sm md:text-lg mb-8 leading-relaxed max-w-xl mx-auto">
            Monitor potable water distribution and stormwater drainage networks, investigate anomalies, coordinate maintenance, and verify outcomes from a single operations console.
          </p>
          <button
            onClick={onInspect}
            className="px-8 sm:px-10 py-4 md:py-4.5 bg-[#00BFFF] hover:bg-[#33ccff] text-[#050505] font-mono font-bold text-sm md:text-base tracking-[0.2em] uppercase rounded-2xl shadow-[0_0_30px_rgba(0,191,255,0.5)] hover:shadow-[0_0_45px_rgba(0,191,255,0.8)] hover:scale-[1.03] active:scale-[0.98] transition-all duration-200 cursor-pointer flex items-center justify-center gap-3 mx-auto"
          >
            <span>INSPECT CAMPUS</span>
            <ArrowRight className="w-5 h-5 stroke-[2.5]" />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
