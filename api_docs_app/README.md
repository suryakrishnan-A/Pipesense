# PipeSense & DrainPilot Swagger UI Application

This directory contains a standalone Swagger UI documentation web service running on **Port 5002** in an isolated environment. It documents the operational resilience APIs of both **PipeSense** and **DrainPilot** hosted on **Port 5001**.

> **Isolation Guarantee:**
> - Zero modifications to `backend_v2`, `backend`, `frontend`, `tests`, `tests_v2`, or existing configuration files.
> - Runs completely independently in its own virtual environment (`api_docs_app/.venv`).

---

## 1. Quick Startup

### Option A: Using the Isolated Virtual Environment (Recommended)

From the project root:
```powershell
cd api_docs_app
.\.venv\Scripts\python.exe app.py
```

Or run directly from project root:
```powershell
.\api_docs_app\.venv\Scripts\python.exe .\api_docs_app\app.py
```

### Option B: Setting Up a Fresh Environment
If recreating the virtual environment:
```powershell
cd api_docs_app
uv venv .venv
uv pip install -r requirements.txt --python .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe app.py
```

---

## 2. Access URLs

Once started, the documentation service is available at:

- **Swagger UI Interactive Dashboard:** [http://localhost:5002/docs/](http://localhost:5002/docs/) (or [http://localhost:5002/](http://localhost:5002/))
- **OpenAPI 3.0 YAML Spec:** [http://localhost:5002/openapi.yaml](http://localhost:5002/openapi.yaml)
- **OpenAPI 3.0 JSON Spec:** [http://localhost:5002/openapi.json](http://localhost:5002/openapi.json)
- **Service Health Check:** [http://localhost:5002/health](http://localhost:5002/health)

---

## 3. Documented Endpoints (Port 5001)

The Swagger UI application documents **25 live endpoints** running on the Port 5001 backend:

### PipeSense (Potable Water Resilience)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/pipesense/detect` | Ingest flow telemetry; detect leaks (>1.35x baseline) |
| `GET` | `/pipesense/incidents` | List all system incidents |
| `GET` | `/pipesense/incidents/{incident_id}` | Retrieve incident details by ID |
| `POST` | `/pipesense/incidents/{incident_id}/investigate` | Autonomous agent investigation (weather, baselines, occupancy, history) |
| `POST` | `/pipesense/incidents/{incident_id}/dispatch` | Dispatch P1 maintenance work order to Senior Plumber |
| `GET` | `/pipesense/summary` | Operational metrics & daily loss avoided |
| `GET` | `/pipesense/impact` | Verified water savings metrics (BLDG-04) |

### DrainPilot (Stormwater & Drainage Resilience)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/drainpilot/detect` | Ingest chamber telemetry; evaluate multi-threshold overflow risk |
| `GET` | `/drainpilot/incidents` | List DrainPilot-isolated incidents |
| `GET` | `/drainpilot/incidents/{incident_id}` | Retrieve specific drainage incident |
| `POST` | `/drainpilot/incidents/{incident_id}/investigate` | Autonomous multi-sensor drainage investigation |
| `POST` | `/drainpilot/incidents/{incident_id}/dispatch` | Dispatch maintenance crew to Drainage & Civils specialists |
| `GET` | `/drainpilot/work-orders` | List DrainPilot-isolated work orders |
| `GET` | `/drainpilot/work-orders/{work_order_id}` | Retrieve single drainage work order |
| `POST` | `/drainpilot/work-orders/{work_order_id}/complete` | Record maintenance completion claim (moves to VERIFYING) |
| `POST` | `/drainpilot/work-orders/{work_order_id}/verify` | Post-repair physical telemetry verification (headroom, fill ratio) |
| `POST` | `/drainpilot/work-orders/{work_order_id}/repair` | Initiate second repair cycle after escalation |
| `GET` | `/drainpilot/summary` | Drainage operational metrics & pump health status |

### Closed-Loop Work Orders & Cross-System Verification
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/work-orders` | List all system work orders |
| `POST` | `/work-orders/{work_order_id}/complete` | Technician completion claim (initiates verification loop) |
| `POST` | `/work-orders/{work_order_id}/verify` | Mathematical verification of post-repair water telemetry |
| `POST` | `/work-orders/{work_order_id}/repair` | Second repair attempt following failed verification |

### Events, Audit Trail & Demo Simulator
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/events/{incident_id}` | Chronological event log & agent tool calls |
| `POST` | `/demo/pipesense/reset` | Reset demo state |
| `POST` | `/demo/pipesense/run` | Run full end-to-end closed loop demo flow |

---

## 4. File Structure

```
api_docs_app/
├── .venv/               # Isolated Python virtual environment
├── app.py               # Flask application serving Swagger UI on port 5002
├── openapi.yaml         # Complete OpenAPI 3.0 specification (YAML)
├── openapi.json         # Complete OpenAPI 3.0 specification (JSON)
├── requirements.txt     # Python package requirements
└── README.md            # Documentation and instructions
```
