# Integrated Water & Grid Resilience Agent
**Team:** Optimus (YE2E45)
**Track:** 02 (Heat and Water) - WeMakeDevs × AWS Bharat Builds Tour 2026

## 1. The Core Problem
Campus and urban infrastructure fails in silos, but the impact is compound. Traditional building management systems (BMS) are passive—they merely send alerts when water flow spikes, relying entirely on human operators to investigate, dispatch, and confirm the fix. Often, technicians close tickets prematurely, leading to massive, undetected water loss.

## 2. Our Solution
We built an **autonomous, closed-loop operational agent** named **PipeSense**. It doesn't just alert; it investigates the context, dispatches crews, and—crucially—uses physical sensor data to mathematically prove whether the repair actually worked before closing the ticket.

---

## 3. The Full Working Flow (Step-by-Step)

### Phase 1: Anomaly Detection
*   **Trigger:** The system continuously monitors the night-flow water baseline for campus buildings.
*   **Event:** At 02:45 AM, the telemetry at *Satish Dhawan Hostel (BLDG-04)* spikes from a normal baseline of **18.4 L/min** to an anomalous **64.2 L/min**.
*   **Action:** The system flags the 3.49x surge as a critical anomaly, generates an Incident ID (`INC-XXXX`), and wakes up the AI Agent.

### Phase 2: Autonomous Investigation (Context Gathering)
Instead of immediately waking up a human manager, the local deterministic resilience agent uses 4 distinct tools to gather context and rule out false positives:
1.  **`check_weather()`:** Confirms there is no rain and automated irrigation is OFF. (Rules out environmental causes).
2.  **`check_peer_baselines()`:** Checks neighboring buildings and sees they are operating at normal 1.0x flow. (Rules out municipal pressure spikes).
3.  **`check_maintenance_history()`:** Discovers a previously flagged "minor fissure" on the Basement Secondary Riser. (Identifies probable structural vulnerability).
4.  **`check_occupancy()`:** Confirms standard resting hours with no approved late-night lab events. (Rules out human usage).
*   **Verdict:** The Agent synthesizes this data with 98% confidence, diagnosing a **Confirmed Major Leak** at the Basement Secondary Riser, wasting an estimated 65,000+ Liters/day.

### Phase 3: Smart Dispatch
*   **Action:** The agent autonomously drafts a Priority 1 (P1) Work Order.
*   **Routing:** It assigns the ticket to the on-call Senior Plumber and dispatches an SMS notification detailing the exact location and severity of the leak.

### Phase 4: The Verification Loop (The Killer Differentiator)
This is where our agent separates itself from standard ticketing systems. It operates on a **"Trust, but Verify"** model.
*   **The Human Action:** The plumber marks the work order as "COMPLETE" in the app, claiming they replaced a rubber washer.
*   **The Agent's Action:** The agent does *not* close the incident. Instead, it queries the live water meter telemetry again.
*   **The Result:** The telemetry still reads **61.8 L/min**. The leak is still active.
*   **Escalation:** The agent **rejects** the completion claim, flags the work order as FAILED VERIFICATION, and automatically escalates the issue to a Senior Supervisor.

### Phase 5: Successful Resolution & Impact Measurement
*   **The Human Action:** The Senior Supervisor arrives, finds the cracked 2-inch pipe, replaces it, and marks the task complete.
*   **The Agent's Action:** The agent checks the telemetry one final time.
*   **The Result:** The flow rate has returned to the safe baseline of **18.2 L/min**.
*   **Closure:** The agent officially closes the incident. It then calculates the exact environmental impact: **66,240 Liters of water saved per day**, converting it to a tangible metric for sustainability reports.

---

## 4. Technical Architecture & Agent Execution
*   **Deployment Method:** Local deterministic operational pipeline.
*   **Frontend:** Interactive React Dashboard (Tailwind CSS, Lucide icons, Vite) with dynamic REST API integration.
*   **Backend Engine:** Python Flask backend with SQLAlchemy SQLite topology database (`topology.db`).
*   **Agent Execution:** Powered by a local deterministic rule-based resilience engine. Live Amazon Bedrock / Strands SDK integrations are currently unimplemented in this build; no AWS Bedrock calls or cloud charges are incurred.
