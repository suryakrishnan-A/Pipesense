import { useState, useEffect } from 'react';
import { fetchIncidents, fetchSites, fetchTopologyNetwork, type TopologyNetwork } from '../lib/api';
import { 
  GitBranch, 
  Map, 
  Settings2, 
  AlertTriangle, 
  CheckCircle2, 
  Info,
  Activity,
  Server,
  Maximize2
} from 'lucide-react';

export default function TopologyView() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [network, setNetwork] = useState<TopologyNetwork | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const incRes = await fetchIncidents();
        setIncidents(incRes);
        
        const sites = await fetchSites();
        if (sites.length > 0) {
          const netRes = await fetchTopologyNetwork(sites[0].id);
          setNetwork(netRes);
        } else {
          setError("No sites configured in database.");
        }
      } catch (e) {
        console.error(e);
        setError("Failed to connect to backend topology API. Showing read-only mode.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const getNodeStatusColor = (nodeName: string, defaultStatus: string) => {
    const building = network?.buildings.find(b => network.nodes.find(n => n.name === nodeName)?.building_id === b.id);
    const incident = building ? incidents.find(i => i.zone === building.zone_id) : incidents.find(i => i.zone === nodeName);
    
    if (incident) {
      if (incident.state === 'RESOLVED' || incident.state === 'CLOSED') return 'text-[var(--color-pipesense-green)] border-[var(--color-pipesense-green)]';
      if (incident.severity === 'HIGH') return 'text-[var(--color-pipesense-red)] border-[var(--color-pipesense-red)] shadow-[0_0_15px_rgba(224,108,117,0.3)]';
      return 'text-[var(--color-pipesense-amber)] border-[var(--color-pipesense-amber)]';
    }
    
    if (defaultStatus === 'unknown') return 'text-[var(--color-pipesense-muted)] border-[var(--color-pipesense-border)] border-dashed';
    if (defaultStatus === 'anomaly') return 'text-[var(--color-pipesense-red)] border-[var(--color-pipesense-red)] shadow-[0_0_15px_rgba(224,108,117,0.3)]';
    return 'text-[var(--color-pipesense-cyan)] border-[var(--color-pipesense-cyan)]';
  };

  const getNodeBg = (nodeName: string) => {
    const building = network?.buildings.find(b => network.nodes.find(n => n.name === nodeName)?.building_id === b.id);
    const incident = building ? incidents.find(i => i.zone === building.zone_id) : incidents.find(i => i.zone === nodeName);

    if (incident && incident.severity === 'HIGH') return 'bg-[var(--color-pipesense-red)]/10';
    if (incident) return 'bg-[var(--color-pipesense-amber)]/10';
    if (selectedNode?.name === nodeName) return 'bg-[var(--color-pipesense-cyan)]/10';
    return 'bg-[var(--color-pipesense-panel)]';
  };

  const handleNodeClick = (nodeName: string) => {
    const node = network?.nodes.find(n => n.name === nodeName);
    if (!node) return;
    
    const meter = network?.meters.find(m => m.node_id === node.id);
    const building = network?.buildings.find(b => b.id === node.building_id);
    const incident = building ? incidents.find(i => i.zone === building.zone_id) : incidents.find(i => i.zone === nodeName);
    
    let status = 'nominal';
    let reading = meter ? (incident ? `${incident.current_flow_lpm} ${meter.unit}` : `Live Data Available`) : 'N/A';
    
    if (incident) {
      status = incident.severity === 'HIGH' ? 'anomaly' : 'warning';
    }

    setSelectedNode({
      id: node.id,
      name: node.name,
      type: node.type,
      monitored: !!meter,
      status,
      reading
    });
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold font-hud tracking-wider">PIPELINE TOPOLOGY</h1>
          <p className="text-[var(--color-pipesense-muted)] mt-1">Configure and monitor the physical pipe network</p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 text-sm border border-[var(--color-pipesense-border)] rounded-md hover:bg-[var(--color-pipesense-secondary)] transition-colors flex items-center">
            <Settings2 className="w-4 h-4 mr-2" /> View Settings
          </button>
          <button 
            onClick={() => alert('Save configuration is currently unavailable. Topology CRUD APIs are pending in backend Phase 2.')}
            className="px-4 py-2 text-sm bg-[var(--color-pipesense-cyan)] text-[var(--color-pipesense-bg)] rounded-md hover:opacity-90 transition-opacity font-medium"
          >
            Save Topology
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        
        {/* Graph Canvas area */}
        <div className="lg:col-span-2 border border-[var(--color-pipesense-border)] rounded-xl bg-[var(--color-pipesense-panel)] overflow-hidden flex flex-col relative">
          
          <div className="p-4 border-b border-[var(--color-pipesense-border)] bg-[var(--color-pipesense-panel)]/50 backdrop-blur flex justify-between items-center z-10">
            <div className="flex items-center gap-2">
              <Map className="w-4 h-4 text-[var(--color-pipesense-cyan)]" />
              <span className="font-hud font-bold">NORTH CAMPUS NETWORK</span>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono text-[var(--color-pipesense-muted)]">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--color-pipesense-cyan)]"></span> Monitored</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--color-pipesense-border)]"></span> Unmonitored</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--color-pipesense-red)]"></span> Anomaly</span>
            </div>
          </div>

          <div className="flex-1 relative bg-[var(--color-pipesense-bg)] p-8 overflow-auto">
            {/* Visual Warning for missing API or errors */}
            {error ? (
              <div className="absolute top-4 left-4 bg-[var(--color-pipesense-red)]/10 border border-[var(--color-pipesense-red)]/50 text-[var(--color-pipesense-red)] text-xs px-3 py-2 rounded-md flex items-start gap-2 max-w-sm z-20">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            ) : (
              <div className="absolute top-4 left-4 bg-[var(--color-pipesense-cyan)]/10 border border-[var(--color-pipesense-cyan)]/50 text-[var(--color-pipesense-cyan)] text-xs px-3 py-2 rounded-md flex items-start gap-2 max-w-sm z-20">
                <Info className="w-4 h-4 mt-0.5 shrink-0" />
                <p>Live topology configured. Editing is currently locked.</p>
              </div>
            )}

            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <Activity className="w-8 h-8 text-[var(--color-pipesense-cyan)] animate-spin" />
              </div>
            ) : (
              <div className="relative w-full h-full min-w-[600px] min-h-[400px]">
                {/* SVG Lines for Edges */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
                  <path d="M 100 200 L 250 200" stroke="var(--color-pipesense-cyan)" strokeWidth="3" strokeDasharray="5,5" fill="none" />
                  <path d="M 250 200 L 450 100" stroke="var(--color-pipesense-cyan)" strokeWidth="3" fill="none" />
                  <path d="M 250 200 L 450 200" stroke="var(--color-pipesense-red)" strokeWidth="3" fill="none" className="animate-pulse" />
                  <path d="M 250 200 L 450 300" stroke="var(--color-pipesense-cyan)" strokeWidth="3" fill="none" />
                </svg>

                {/* Nodes rendering - Hardcoded absolute positioning for the demo visual */}
                <div 
                  className={`absolute left-[50px] top-[170px] w-24 p-2 text-center rounded-lg border-2 cursor-pointer transition-all z-10 ${getNodeStatusColor('SRC-01', 'nominal')} ${getNodeBg('SRC-01')}`}
                  onClick={() => handleNodeClick('SRC-01')}
                >
                  <Server className="w-6 h-6 mx-auto mb-1" />
                  <div className="text-xs font-bold font-mono">SRC-01</div>
                </div>

                <div 
                  className={`absolute left-[220px] top-[185px] w-16 p-1 text-center rounded-full border-2 cursor-pointer transition-all z-10 ${getNodeStatusColor('JCT-A', 'unknown')} ${getNodeBg('JCT-A')}`}
                  onClick={() => handleNodeClick('JCT-A')}
                >
                  <GitBranch className="w-5 h-5 mx-auto" />
                </div>

                <div 
                  className={`absolute left-[450px] top-[70px] w-32 p-3 text-center rounded-lg border-2 cursor-pointer transition-all z-10 ${getNodeStatusColor('INLET-BLDG-01', 'nominal')} ${getNodeBg('INLET-BLDG-01')}`}
                  onClick={() => handleNodeClick('INLET-BLDG-01')}
                >
                  <Activity className="w-5 h-5 mx-auto mb-1" />
                  <div className="text-xs font-bold font-mono">BLDG-01</div>
                </div>

                <div 
                  className={`absolute left-[450px] top-[170px] w-32 p-3 text-center rounded-lg border-2 cursor-pointer transition-all z-10 ${getNodeStatusColor('INLET-BLDG-04', 'anomaly')} ${getNodeBg('INLET-BLDG-04')}`}
                  onClick={() => handleNodeClick('INLET-BLDG-04')}
                >
                  <AlertTriangle className="w-5 h-5 mx-auto mb-1" />
                  <div className="text-xs font-bold font-mono">BLDG-04</div>
                </div>

                <div 
                  className={`absolute left-[450px] top-[270px] w-32 p-3 text-center rounded-lg border-2 cursor-pointer transition-all z-10 ${getNodeStatusColor('INLET-HOSTEL-B', 'nominal')} ${getNodeBg('INLET-HOSTEL-B')}`}
                  onClick={() => handleNodeClick('INLET-HOSTEL-B')}
                >
                  <CheckCircle2 className="w-5 h-5 mx-auto mb-1" />
                  <div className="text-xs font-bold font-mono">HOSTEL-B</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Node Details Inspector */}
        <div className="border border-[var(--color-pipesense-border)] rounded-xl bg-[var(--color-pipesense-panel)] p-6 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-hud font-bold text-lg">INSPECTOR</h2>
            <Maximize2 className="w-4 h-4 text-[var(--color-pipesense-muted)]" />
          </div>

          {selectedNode ? (
            <div className="space-y-6">
              <div>
                <div className="text-xs text-[var(--color-pipesense-muted)] uppercase tracking-wider mb-1 font-mono">ASSET ID</div>
                <div className="text-xl font-bold font-mono text-[var(--color-pipesense-cyan)]">{selectedNode.id}</div>
                <div className="text-sm mt-1">{selectedNode.name}</div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[var(--color-pipesense-bg)] p-3 rounded-lg border border-[var(--color-pipesense-border)]">
                  <div className="text-xs text-[var(--color-pipesense-muted)] font-mono mb-1">TYPE</div>
                  <div className="font-medium capitalize">{selectedNode.type}</div>
                </div>
                <div className="bg-[var(--color-pipesense-bg)] p-3 rounded-lg border border-[var(--color-pipesense-border)]">
                  <div className="text-xs text-[var(--color-pipesense-muted)] font-mono mb-1">SENSOR</div>
                  <div className="font-medium">
                    {selectedNode.monitored ? (
                      <span className="text-[var(--color-pipesense-green)] flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[var(--color-pipesense-green)]"></span> Active</span>
                    ) : (
                      <span className="text-[var(--color-pipesense-muted)]">Unmonitored</span>
                    )}
                  </div>
                </div>
              </div>

              {selectedNode.monitored && (
                <div className="bg-[var(--color-pipesense-bg)] p-4 rounded-lg border border-[var(--color-pipesense-border)]">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-mono text-[var(--color-pipesense-muted)]">CURRENT FLOW (MEASURED)</span>
                    <span className="text-xs font-mono bg-[var(--color-pipesense-cyan)]/20 text-[var(--color-pipesense-cyan)] px-2 py-0.5 rounded">LIVE</span>
                  </div>
                  <div className={`text-2xl font-bold font-mono ${selectedNode.status === 'anomaly' ? 'text-[var(--color-pipesense-red)]' : 'text-white'}`}>
                    {selectedNode.reading}
                  </div>
                </div>
              )}

              {selectedNode.status === 'anomaly' && (
                <div className="bg-[var(--color-pipesense-red)]/10 border border-[var(--color-pipesense-red)]/30 p-4 rounded-lg">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-[var(--color-pipesense-red)] mt-0.5 shrink-0" />
                    <div>
                      <h4 className="font-bold text-[var(--color-pipesense-red)] text-sm mb-1">High Confidence Anomaly</h4>
                      <p className="text-xs text-[var(--color-pipesense-muted)] mb-2">Agent hypothesis suggests fissure leak downstream of inlet valve.</p>
                      <button className="text-xs bg-[var(--color-pipesense-red)] text-white px-3 py-1.5 rounded font-medium hover:bg-red-600 transition-colors">
                        View Incident Details
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-[var(--color-pipesense-muted)]">
              <GitBranch className="w-12 h-12 mb-4 opacity-20" />
              <p>Select a node or pipe segment<br/>to view details.</p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
