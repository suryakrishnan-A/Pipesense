import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5001';

// -------------------------------------------------------------
// PipeSense Types & API
// -------------------------------------------------------------

export interface PipeSummary {
  active_incidents: number;
  total_incidents: number;
  verified_daily_loss_avoided_liters: number;
  average_confidence: number;
}

export interface PipeImpact {
  estimated_daily_loss_liters?: number;
  verified_daily_loss_avoided_liters?: number;
  baseline_flow_lpm?: number;
  peak_abnormal_flow_lpm?: number;
  verified_post_repair_flow_lpm?: number;
  water_loss_reduction_lpm?: number;
}

export interface IncidentEvent {
  event_type: string;
  incident_id?: string;
  work_order_id?: string;
  timestamp: string;
  details: Record<string, any>;
  actor_id?: string;
  action?: string;
}

export interface PipeIncident {
  incident_id: string;
  zone: string;
  state: string;
  severity: string;
  current_flow_lpm: number;
  baseline_flow_lpm: number;
  description?: string;
  hypothesis?: string;
  created_at?: string;
}

export interface PipeWorkOrder {
  work_order_id: string;
  incident_id: string;
  status: string;
  notes?: string;
  created_at?: string;
  completed_at?: string | null;
  repair_action?: string;
}

export interface AgentStatus {
  mode: string;
  status_key?: string;
  provider: string;
  bedrock_enabled: boolean;
  bedrock_configured?: boolean;
  region?: string | null;
  model_id?: string | null;
  status_text: string;
  error_reason?: string | null;
  description: string;
}

export interface ThresholdsConfig {
  anomaly_multiplier_threshold: number;
  night_flow_window: string;
  verification_tolerance_multiplier: number;
  critical_leak_multiplier: number;
  agent_mode: string;
  status_key?: string;
  bedrock_enabled: boolean;
  bedrock_configured?: boolean;
  is_simulated: boolean;
  mode_description: string;
}

export interface MeterInventoryItem {
  id: string;
  name: string;
  meter_type: string;
  unit: string;
  is_active: boolean;
  node_id: string;
  node_name: string;
  building_name?: string;
  zone_id?: string | null;
}

export const fetchSummary = async (): Promise<PipeSummary> => {
  const res = await axios.get(`${BASE_URL}/pipesense/summary`);
  return res.data;
};

export const fetchIncidents = async (): Promise<PipeIncident[]> => {
  const res = await axios.get(`${BASE_URL}/pipesense/incidents`);
  return res.data;
};

export const fetchIncident = async (incidentId: string): Promise<PipeIncident> => {
  const res = await axios.get(`${BASE_URL}/pipesense/incidents/${incidentId}`);
  return res.data;
};

export const fetchWorkOrders = async (): Promise<PipeWorkOrder[]> => {
  const res = await axios.get(`${BASE_URL}/work-orders`);
  return res.data;
};

export const completeWorkOrder = async (workOrderId: string): Promise<PipeIncident> => {
  const res = await axios.post(`${BASE_URL}/work-orders/${workOrderId}/complete`);
  return res.data;
};

export const verifyWorkOrder = async (workOrderId: string, telemetry: number): Promise<PipeIncident> => {
  const res = await axios.post(`${BASE_URL}/work-orders/${workOrderId}/verify`, { telemetry });
  return res.data;
};

export const repairWorkOrder = async (workOrderId: string): Promise<PipeIncident> => {
  const res = await axios.post(`${BASE_URL}/work-orders/${workOrderId}/repair`);
  return res.data;
};

export const investigateIncident = async (incidentId: string): Promise<PipeIncident> => {
  const res = await axios.post(`${BASE_URL}/pipesense/incidents/${incidentId}/investigate`);
  return res.data;
};

export const dispatchWorkOrder = async (incidentId: string): Promise<PipeWorkOrder> => {
  const res = await axios.post(`${BASE_URL}/pipesense/incidents/${incidentId}/dispatch`);
  return res.data;
};

export const fetchImpact = async (): Promise<PipeImpact> => {
  const res = await axios.get(`${BASE_URL}/pipesense/impact`);
  return res.data;
};

export const fetchEvents = async (incidentId: string): Promise<IncidentEvent[]> => {
  const res = await axios.get(`${BASE_URL}/events/${incidentId}`);
  return res.data;
};

export const fetchAuditLogs = async (): Promise<IncidentEvent[]> => {
  const res = await axios.get(`${BASE_URL}/audit-logs`);
  return res.data;
};

export const fetchAgentStatus = async (): Promise<AgentStatus> => {
  const res = await axios.get(`${BASE_URL}/pipesense/agent-status`);
  return res.data;
};

export const fetchThresholds = async (): Promise<ThresholdsConfig> => {
  const res = await axios.get(`${BASE_URL}/pipesense/thresholds`);
  return res.data;
};

export const fetchMeters = async (): Promise<MeterInventoryItem[]> => {
  const res = await axios.get(`${BASE_URL}/topology/meters`);
  return res.data;
};

export const runDemo = async () => {
  const res = await axios.post(`${BASE_URL}/demo/pipesense/run`);
  return res.data;
};

export const resetDemo = async () => {
  const res = await axios.post(`${BASE_URL}/demo/pipesense/reset`);
  return res.data;
};


// -------------------------------------------------------------
// DrainPilot Types & API
// -------------------------------------------------------------

export interface DrainTelemetryInput {
  zone?: string;
  chamber_id: string;
  water_level_cm: number;
  chamber_depth_cm: number;
  rate_of_rise_cm_per_hr?: number;
  silt_depth_cm?: number;
  pump_status?: 'OPERATIONAL' | 'OVERLOAD' | 'OFFLINE' | string;
  rainfall_mm_per_hr?: number;
  catchment_area?: string;
}

export interface DrainVerificationPayload {
  water_level_cm: number;
  chamber_depth_cm?: number;
  rate_of_rise_cm_per_hr?: number;
  pump_status?: string;
}

export interface DrainSummary {
  total_zones_monitored: number;
  monitored_zones: string[];
  total_drain_incidents: number;
  active_incidents: number;
  critical_overflow_risks: number;
  high_severity_incidents: number;
  investigating_count: number;
  resolved_count: number;
  total_work_orders: number;
  active_work_orders: number;
  escalated_work_orders: number;
  is_simulated: boolean;
  data_origin: string;
  disclaimer: string;
}

export interface DrainIncident {
  incident_id: string;
  zone: string;
  baseline_flow_lpm: number;
  current_flow_lpm: number;
  system: string;
  state: string;
  severity: string;
  priority: string;
  confidence: number;
  description: string;
  diagnosis: string;
  detected_at: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
  is_simulated?: boolean;
}

export interface DrainWorkOrder {
  work_order_id: string;
  incident_id: string;
  priority: string;
  assigned_role: string;
  assigned_person: string;
  zone: string;
  description: string;
  status: string;
  verification_status: string;
  completion_claimed_at?: string | null;
  created_at: string;
  updated_at: string;
  is_simulated?: boolean;
}

export const fetchDrainSummary = async (): Promise<DrainSummary> => {
  const res = await axios.get(`${BASE_URL}/drainpilot/summary`);
  return res.data;
};

export const fetchDrainIncidents = async (): Promise<DrainIncident[]> => {
  const res = await axios.get(`${BASE_URL}/drainpilot/incidents`);
  return res.data;
};

export const fetchDrainIncident = async (incidentId: string): Promise<DrainIncident> => {
  const res = await axios.get(`${BASE_URL}/drainpilot/incidents/${incidentId}`);
  return res.data;
};

export const detectDrainAnomaly = async (telemetry: DrainTelemetryInput): Promise<any> => {
  const res = await axios.post(`${BASE_URL}/drainpilot/detect`, telemetry);
  return res.data;
};

export const investigateDrainIncident = async (incidentId: string): Promise<DrainIncident> => {
  const res = await axios.post(`${BASE_URL}/drainpilot/incidents/${incidentId}/investigate`);
  return res.data;
};

export const dispatchDrainWorkOrder = async (incidentId: string): Promise<DrainWorkOrder> => {
  const res = await axios.post(`${BASE_URL}/drainpilot/incidents/${incidentId}/dispatch`);
  return res.data;
};

export const fetchDrainWorkOrders = async (): Promise<DrainWorkOrder[]> => {
  const res = await axios.get(`${BASE_URL}/drainpilot/work-orders`);
  return res.data;
};

export const fetchDrainWorkOrder = async (workOrderId: string): Promise<DrainWorkOrder> => {
  const res = await axios.get(`${BASE_URL}/drainpilot/work-orders/${workOrderId}`);
  return res.data;
};

export const completeDrainWorkOrder = async (workOrderId: string): Promise<DrainIncident> => {
  const res = await axios.post(`${BASE_URL}/drainpilot/work-orders/${workOrderId}/complete`);
  return res.data;
};

export const verifyDrainWorkOrder = async (
  workOrderId: string,
  telemetry: DrainVerificationPayload
): Promise<DrainIncident> => {
  const res = await axios.post(`${BASE_URL}/drainpilot/work-orders/${workOrderId}/verify`, telemetry);
  return res.data;
};

export const repairDrainWorkOrder = async (workOrderId: string): Promise<DrainIncident> => {
  const res = await axios.post(`${BASE_URL}/drainpilot/work-orders/${workOrderId}/repair`);
  return res.data;
};

// -------------------------------------------------------------
// Topology Management API
// -------------------------------------------------------------

export interface TopologyNode {
  id: string;
  name: string;
  type: string;
  building_id?: string;
}

export interface TopologySegment {
  id: string;
  source_node_id: string;
  target_node_id: string;
  name: string;
}

export interface TopologyBuilding {
  id: string;
  name: string;
  zone_id: string;
}

export interface TopologyMeter {
  id: string;
  node_id: string;
  name: string;
  type: string;
  unit: string;
}

export interface TopologyNetwork {
  site: { id: string; name: string };
  buildings: TopologyBuilding[];
  nodes: TopologyNode[];
  segments: TopologySegment[];
  meters: TopologyMeter[];
}

export const fetchSites = async (): Promise<{id: string; name: string}[]> => {
  const res = await axios.get(`${BASE_URL}/topology/sites`);
  return res.data;
};

export const fetchTopologyNetwork = async (siteId: string): Promise<TopologyNetwork> => {
  const res = await axios.get(`${BASE_URL}/topology/sites/${siteId}/network`);
  return res.data;
};
