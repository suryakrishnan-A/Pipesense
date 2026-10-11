# PipeSense Backend v2

An autonomous, agentic water-loss response system that strictly requires telemetry verification to close incidents.

## Architecture
- **API**: Flask application exposing PipeSense, DrainPilot, and Topology endpoints on port 5001.
- **Service**: `PipeSenseServiceSQL` (persisted SQLite) and `PipeSenseService` (in-memory test engine).
- **Domain**: SQLAlchemy models for `Incident`, `WorkOrder`, `AuditLog`, `VerificationRecord`, and network topology (`Site`, `PipelineNode`, `PipeSegment`, `Meter`).
- **Agent**: `StrandsAgent` evaluating telemetry and context tools using the **Strands Agents SDK** (`strands-agents`) powered by Amazon Bedrock (`BedrockModel` / Converse tool calling), registering PipeSense's 4 investigation tools (`check_weather`, `check_peer_baselines`, `check_maintenance_history`, and `check_occupancy`). Features deterministic local rule fallback when Bedrock is unconfigured or unreachable.
- **Repository**: SQLite database (`topology.db`) and in-memory test store.

## State Machine
`NOMINAL` -> `ANOMALY` -> `INVESTIGATING` -> `LEAK_CONFIRMED` -> `WORK_ORDER_ISSUED` -> `VERIFYING` -> `FAILED_VERIFICATION` -> `ESCALATED` -> `REPAIRING` -> `VERIFYING` -> `RESOLVED` -> `CLOSED`

**CRITICAL RULE**: *"Repair completion is not accepted without telemetry verification."* A human completion claim MUST NOT resolve an incident directly.

---

## Agent Runtime & AWS Bedrock Integration

PipeSense features an Amazon Bedrock agent integration built with the **Strands Agents SDK** (`strands-agents`) and `boto3`.

> **Live Verification Disclosure**: The Bedrock code path is implemented in the codebase, but it has **not been live-verified** unless a real Bedrock invocation has succeeded. Local testing and development run strictly against offline mocks without making live AWS calls. The app remains in **Local Demo Mode** by default. Bedrock is never reported as active or connected based only on environment configuration or mock test runs.

### Operational States
The agent status API (`/pipesense/agent-status`) and frontend dynamically reflect four distinct operational states:
1. **Local Demo Mode (`local_demo`)** *(Default)*:
   - Operates completely offline using deterministic domain rules and context tools.
   - Requires zero AWS credentials and incurs zero cloud charges.
2. **Bedrock Configured - Pending Verification (`bedrock_configured_unverified`)**:
   - `USE_AWS_BEDROCK=true` is set server-side with region and model ID.
   - Waiting for the first real live invocation to verify connectivity before claiming active status.
3. **Bedrock Agent Active (`bedrock_active`)**:
   - Live Amazon Bedrock invocation succeeded and returned valid structured diagnosis.
   - The status is ONLY reported as active after a real, verified successful model response.
4. **Bedrock Unavailable / Local Fallback (`bedrock_unavailable`)**:
   - If an AWS credential error, model quota, network timeout, or service error occurs, the agent catches it safely, sanitizes all error details (never exposing keys), and falls back seamlessly to local investigation.

### Enabling Amazon Bedrock (Server-Side Configuration)
To run with live Amazon Bedrock:
1. Configure AWS credentials on your host machine (e.g., via `aws configure` or IAM roles). Never check credentials into git or frontend code.
2. Set the following environment variables in your server environment:
   ```powershell
   $env:USE_AWS_BEDROCK="true"
   $env:AWS_REGION="us-east-1"
   $env:BEDROCK_MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
   ```
3. Start the backend as usual. The agent will invoke Bedrock with Strands tool-calling across the 4 context tools and validate structured output schemas.

---

## Setup & Running the Backend

### Prerequisites
- Python 3.12 (or virtual environment manager like `uv` or `venv`)

### 1. Create and Activate Virtual Environment
```powershell
# Using uv:
uv venv .venv --python 3.12
.venv\Scripts\activate

# Or standard Python:
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run the Backend API (Port 5001)
```powershell
# PowerShell (portable):
$env:PYTHONPATH="."
python backend_v2/api/main.py
```

---

## Running Tests
All test suites run completely offline and do not contact AWS:
```powershell
$env:PYTHONPATH="."
pytest tests_v2/
```
To run the full closed-loop hackathon demonstration script:
```powershell
$env:PYTHONPATH="."
python tests/test_full_loop.py
```

---

## Running the Frontend

```powershell
cd frontend
npm install
npm run build
npm run dev
```
The frontend Vite server opens on `http://localhost:5173` and proxies/connects to the backend at `http://127.0.0.1:5001`.

---

## Primary API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/pipesense/detect` | Ingests telemetry and detects water flow anomalies |
| `GET` | `/pipesense/incidents` | Lists active and historical incidents |
| `POST` | `/pipesense/incidents/<id>/investigate` | Triggers agent investigation across context tools |
| `POST` | `/pipesense/incidents/<id>/dispatch` | Issues P1 work order for confirmed leak |
| `GET` | `/work-orders` | Lists maintenance work orders |
| `POST` | `/work-orders/<id>/complete` | Technician reports repair complete (triggers VERIFYING) |
| `POST` | `/work-orders/<id>/verify` | Submits post-repair telemetry for physical verification |
| `POST` | `/work-orders/<id>/repair` | Initiates secondary repair if verification was rejected |
| `GET` | `/pipesense/summary` | High-level KPI metrics (active, resolved, avoided loss) |
| `GET` | `/pipesense/impact` | Environmental impact and daily water savings |
| `GET` | `/pipesense/agent-status` | Truthful status of the agent (local demo vs live Bedrock) |
| `GET` | `/pipesense/thresholds` | System threshold configurations and mode disclosure |
| `GET` | `/audit-logs` | Immutable audit trail across all actions |
| `GET` | `/topology/sites` | Configured sites in pipeline topology |
| `GET` | `/topology/meters` | Meter inventory with attached nodes |
| `POST` | `/demo/pipesense/run` | Executes complete closed-loop demo scenario |
| `POST` | `/demo/pipesense/reset` | Resets demo data and restore initial state |

