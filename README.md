# WasteDash — Automated Municipal Solid Waste Segregation & AI Optimization Platform
### Greater Chennai Corporation (GCC), Tamil Nadu, India

WasteDash is a full-stack, enterprise-grade municipal solid waste segregation, monitoring, and AI optimization dashboard specifically architected for the Greater Chennai Corporation (200 wards across 15 zones). The platform combines real-time waste analytics, smart collection fleet tracking, Leaflet GIS mapping, IoT telemetry via **Adafruit IO MQTT**, a 5-layer classical computer vision AI fallback algorithm, and role-based access control supporting all 35 GCC municipal staff designations.

---

## 1. Technology Stack

- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Vanilla CSS & Tailwind CSS utility classes, Lucide Icons
- **Data Visualizations**: Recharts (composition charts, ward leaderboards, seasonal trends)
- **GIS Mapping**: Leaflet, OpenStreetMap tiles with GCC zonal boundaries and truck routes
- **Backend API**: Python 3.12+, FastAPI, Uvicorn (ASGI), Pydantic v2, Starlette
- **Databases & ORM**: SQLAlchemy with independent session engines:
  - Local Development: Three isolated SQLite database files (`users.db`, `staff.db`, `waste_management.db`)
  - Production Ready: Three isolated PostgreSQL connection endpoints
- **IoT & Telemetry**: Adafruit IO MQTT broker (`io.adafruit.com:8883` over TLS), Paho-MQTT, ESP32 HX711 scale firmware
- **Artificial Intelligence**:
  - Primary Vision: Ultralytics YOLOv8 / MobileNetV3 deep neural network classifiers
  - Mandatory Fallback: 5-layer classical computer vision & heuristic analyzer (OpenCV color histogram, contour aspect ratio, edge density, specular reflectance, and gated manual review)
- **Testing**: PyTest, HTTPX TestClient (53+ automated unit & integration test scenarios)

---

## 2. Repository Structure

```
├── README.md                      # Comprehensive project documentation
├── .gitignore                     # Git rules (excludes .env and *.db, preserves .env.example)
├── .env.example                   # Root environment variable template
├── backend/
│   ├── .env.example               # Backend configuration reference
│   ├── migrate_legacy_db.py       # Safe idempotent 3-database migration utility
│   ├── test_auth_api.py           # 12-stage authentication & RBAC test suite
│   ├── test_admin_training_flow.py # 14-stage admin, AI retraining, & webcam detection tests
│   ├── app/
│   │   ├── main.py                # FastAPI entry point, CORS, startup/shutdown lifecycles
│   │   ├── core/
│   │   │   ├── config.py          # Centralized Pydantic settings & validation
│   │   │   ├── database.py        # Independent engines for User, Staff, and Waste DBs
│   │   │   └── security.py        # Passlib bcrypt hashing, JWT issuing and verification
│   │   ├── models/
│   │   │   ├── user.py            # Database A: User, Profile, PasswordReset, AuditLog
│   │   │   ├── staff.py           # Database B: 35 Staff Roles, Duty Assignments, Wards
│   │   │   ├── waste.py           # Database C: Categories, Wards, Plants, Weighbridge
│   │   │   ├── fleet.py           # Database C: Vehicles, Routes, Trips, Telemetry
│   │   │   ├── iot.py             # Database C: IoT Devices, Sensor Telemetry
│   │   │   ├── complaints.py      # Database C: Public Complaints, Status History
│   │   │   ├── ai_model.py        # Database C: AI Models, Training Jobs, Checkpoints
│   │   │   └── simulation.py      # Database C: Simulation Runs, Events, State
│   │   ├── services/
│   │   │   ├── ai_vision_service.py   # Primary deep learning orchestrator
│   │   │   ├── ai_fallback_service.py # 5-layer classical CV heuristic fallback
│   │   │   ├── mqtt_service.py        # Adafruit IO TLS MQTT subscriber/publisher
│   │   │   ├── simulation_engine.py   # Bounded real-time synthetic data engine
│   │   │   └── training_worker.py     # Asynchronous PyTorch retraining thread
│   │   └── api/
│   │       ├── auth.py            # Authentication, registration, password reset, 38 roles
│   │       ├── public_portal.py   # 20 Public resident features & bilingual endpoints
│   │       ├── staff_portal.py    # Role-specific endpoints for all 35 municipal roles
│   │       ├── admin_portal.py    # Account provisioning, dataset review, training
│   │       ├── iot_telemetry.py   # Adafruit IO broker status & sensor ingestion
│   │       └── simulation_api.py  # Simulation controls (start, stop, step, status)
│   └── tests/
│       ├── test_ai_fallback.py    # 15 automated test cases for classical CV fallback
│       └── test_adafruit_mqtt.py  # 12 automated test cases for Adafruit IO MQTT
├── frontend/
│   ├── .env.example               # Frontend NEXT_PUBLIC environment template
│   ├── package.json               # Node.js dependencies
│   ├── app/                       # 33 Next.js pages (public portal, staff & admin dashboards)
│   ├── components/                # Reusable UI primitives, badges, charts, modal drawers
│   └── lib/                       # API clients, auth helpers, types
└── iot/
    └── esp32_hx711_scale/
        └── esp32_hx711_scale.ino  # ESP32 firmware configured for Adafruit IO TLS MQTT
```

---

## 3. Database Architecture & Separation

To eliminate monolithic data coupling, enforce strict operational boundaries, and prevent cross-domain data leaks, WasteDash is divided into **three genuinely separate logical databases**:

```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│          DATABASE A             │   │          DATABASE B             │   │          DATABASE C             │
│   User & Authentication         │   │   Municipal Staff Profiles      │   │    Waste & AI Operations        │
│                                 │   │                                 │   │                                 │
│  • Public Citizen Accounts      │   │  • 35 GCC Staff Roles           │   │  • 200 Wards & 12 Plants        │
│  • Bcrypt Password Hashes       │   │  • Employee IDs & Badges        │   │  • Fleet Tracking & Trips       │
│  • JWT Sessions & Revocations   │   │  • Department & Ward Scope      │   │  • Weighbridge Scale Tickets    │
│  • Password Reset Tokens        │   │  • Vehicle / Route Assignments  │   │  • Adafruit IO Telemetry        │
│  • User Preferences & Points    │   │  • Facility Access Boundaries   │   │  • Public Grievance Tracking    │
│  • Security Audit Logs          │   │  • Staff Audit Logs             │   │  • AI Datasets, Models, Retrain │
│                                 │   │                                 │   │  • Simulation Run Telemetry     │
│  Engine: UserSessionLocal       │   │  Engine: StaffSessionLocal      │   │  Engine: WasteSessionLocal      │
│  Default: users.db              │   │  Default: staff.db              │   │  Default: waste_management.db   │
└─────────────────────────────────┘   └─────────────────────────────────┘   └─────────────────────────────────┘
```

- **Cross-Database Referencing**: Foreign keys do not cross physical database boundaries. Referential integrity between staff/citizens and waste records is validated at the application service layer.
- **Transactions**: Atomic transactions are scoped strictly within each respective database engine.

---

## 4. Environment Variables Reference

All credentials and dynamic configs are loaded centrally via `backend/app/core/config.py`.

### Backend Configuration (`backend/.env`)

| Variable | Description | Default / Example |
|---|---|---|
| `APP_ENV` | Runtime environment (`development`, `production`, `test`) | `development` |
| `DEBUG` | Enable debug logs | `false` |
| `API_V1_PREFIX` | Base prefix for REST endpoints | `/api` |
| `JWT_SECRET_KEY` | 256-bit secret key for signing JWT tokens | *(Generate with `openssl rand -hex 32`)* |
| `JWT_ALGORITHM` | Encryption algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session validity duration | `60` |
| `USER_DATABASE_URL` | Database A connection URL | `sqlite:///./users.db` |
| `STAFF_DATABASE_URL` | Database B connection URL | `sqlite:///./staff.db` |
| `WASTE_DATABASE_URL` | Database C connection URL | `sqlite:///./waste_management.db` |
| `AI_INFERENCE_URL` | URL to optional external inference microservice | `http://localhost:8001` |
| `AI_INFERENCE_API_KEY` | Shared secret key for AI microservice | `dev_ai_api_key` |
| `AI_INFERENCE_TIMEOUT_SECONDS` | Inference request timeout | `15` |
| `AI_CONFIDENCE_THRESHOLD` | Gating threshold below which fallback triggers | `0.65` |
| `AI_FALLBACK_ENABLED` | Enable 5-layer classical computer vision fallback | `true` |
| `ADAFRUIT_IO_USERNAME` | Adafruit IO account username | *(Your Adafruit Username)* |
| `ADAFRUIT_IO_KEY` | Adafruit IO AIO Active Key | *(Your Adafruit AIO Key)* |
| `ADAFRUIT_IO_HOST` | Adafruit IO MQTT secure broker | `io.adafruit.com` |
| `ADAFRUIT_IO_PORT` | Secure TLS MQTT port | `8883` |
| `ADAFRUIT_IO_USE_TLS` | Enforce SSL/TLS certificate verification | `true` |
| `ADAFRUIT_IO_FEED_FILL` | Bin fill percentage feed name | `wastedash-bin-fill` |
| `ADAFRUIT_IO_FEED_WEIGHT` | Waste scale weight (kg) feed name | `wastedash-weight-kg` |
| `ADAFRUIT_IO_FEED_DISTANCE` | Ultrasonic sensor distance (cm) feed name | `wastedash-distance-cm` |
| `ADAFRUIT_IO_FEED_STATUS` | Device health status feed name | `wastedash-device-status` |
| `SIMULATION_MODE` | Enable bounded background simulation engine | `true` |
| `SIMULATION_TICK_SECONDS` | Interval between simulated operational ticks | `10` |
| `FRONTEND_ORIGIN` | Allowed CORS origin for Next.js web application | `http://localhost:3000` |

### Frontend Configuration (`frontend/.env.local`)

| Variable | Description | Value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Public backend REST API URL | `http://localhost:8000/api` |

> [!WARNING]
> Never prefix database connection strings, JWT signing keys, or Adafruit IO keys with `NEXT_PUBLIC_`. Private credentials must never be bundled into browser JavaScript.

---

## 5. Local Setup & Execution Guide

### Prerequisites
- Python 3.12+ (or 3.10+)
- Node.js 18+ and npm
- Git

### 1. Clone & Set Up Backend

```bash
# Clone the repository
git clone <repository_url>
cd <repository_folder>

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Files

```bash
# Copy example configuration to active local development files
cp .env.example .env
cp ../frontend/.env.example ../frontend/.env.local
```

### 3. Initialize & Migrate Databases

Run the safe, idempotent migration utility. It automatically backs up existing records, initializes the three isolated schemas, and seeds baseline GCC operational taxonomy:

```bash
python migrate_legacy_db.py
```

*Output:*
- Creates timestamped backup in `backend/backups/chennai_waste_backup_<timestamp>.db`
- Generates `backend/users.db` (User authentication accounts & bootstrap administrator)
- Generates `backend/staff.db` (Profiles for all 35 GCC municipal staff designations)
- Generates `backend/waste_management.db` (200 GCC Wards, 12 Plants, 24 Vehicles, IoT devices, Weighbridge records)

### 4. Start Backend Server

```bash
# From the backend directory:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger API Documentation: `http://localhost:8000/docs`
- Redoc API Specification: `http://localhost:8000/redoc`

### 5. Start Frontend Application

```bash
cd ../frontend
npm install
npm run dev
```
- Web Application Dashboard: `http://localhost:3000`

---

## 6. Demo Accounts & Role-Based Access Control (RBAC)

The platform enforces backend authorization across all endpoints using JWT tokens. For development and evaluation, synthetic demo accounts are provisioned via `migrate_legacy_db.py`:

| Role Title | Department | Email / Username | Development Password | Access Scope |
|---|---|---|---|---|
| **System Administrator** | Administration | `admin@chennaiswm.gov.in` | `Admin@123` | Full system access, accounts, models |
| **Bootstrap Administrator** | Administration | `admin@wastesegeregate.in` | `admin123` *(Temporary)* | Initial setup; forced change required |
| **AI Systems Lead** | Technology | `ai.lead@chennaiswm.gov.in` | `Admin@123` | AI model training, dataset reviews |
| **Municipal Commissioner** | Executive | `commissioner@chennaiswm.gov.in` | `Staff@123` | City-wide strategic KPIs & oversight |
| **Municipal Health Officer** | Public Health | `health.officer@chennaiswm.gov.in` | `Staff@123` | Health compliance & sanitation |
| **Sanitary Inspector** | Ward Health | `sanitary.inspector102@chennaiswm.gov.in` | `Staff@123` | Ward 102 sanitation & complaints |
| **Collection Vehicle Driver** | Transportation | `driver.gc01@chennaiswm.gov.in` | `Staff@123` | Vehicle GC-01 trips & route status |
| **Weighbridge Operator** | Processing | `weighbridge.perungudi@chennaiswm.gov.in` | `Staff@123` | Scale weighment tickets (Perungudi) |
| **Public Resident / Citizen** | Citizens | `citizen.chennai@gmail.com` | `Citizen@123` | Public portal, grievance logging |

*Note: In production environments, passwords must be rotated immediately, and one-time password setup links are enforced.*

---

## 7. AI Waste Classification & Classical CV Fallback

WasteDash implements a multi-tiered vision pipeline designed to ensure 100% operational continuity even when remote AI microservices or GPU deep learning backends are offline.

```
       Incoming Image / Webcam Frame
                     │
                     ▼
       ┌───────────────────────────┐
       │ Layer 1: Image Validation │
       │  • Resolution ≥ 32x32     │
       │  • Pitch black / Blank    │
       │  • Blur check (Laplacian) │
       └─────────────┬─────────────┘
                     │ (Valid)
                     ▼
       ┌───────────────────────────┐
       │ Primary AI Inference      │──[Fails / Times Out / Low Conf < 0.65]──┐
       │ (YOLOv8 / MobileNet)      │                                         │
       └─────────────┬─────────────┘                                         │
                     │ (Success ≥ 0.65)                                      │
                     ▼                                                       │
         High Confidence Detection                                           ▼
         (classification_method:                                ┌───────────────────────────┐
             "primary_ai")                                      │ Layer 2: Classical CV     │
                                                                │  • Color Histograms (HSV) │
                                                                │  • Contour Rectangularity │
                                                                │  • Edge & Texture Density │
                                                                │  • Specular Reflection    │
                                                                └─────────────┬─────────────┘
                                                                              │
                                                                              ▼
                                                                ┌───────────────────────────┐
                                                                │ Layer 3 & 4: Heuristics   │
                                                                │  • Calibrated Scores      │
                                                                │  • Bounded (0.20 - 0.92)  │
                                                                └─────────────┬─────────────┘
                                                                              │
                                                                              ▼
                                                                ┌───────────────────────────┐
                                                                │ Layer 5: Uncertain Gating │
                                                                │  • Score < 0.38 → Unknown │
                                                                │  • requires_review = True │
                                                                │  • classification_method: │
                                                                │    "fallback_heuristic"   │
                                                                └───────────────────────────┘
```

### Fallback Characteristics
- **Diagnostic Transparency**: Fallback responses explicitly declare `fallback_used: true`, `classification_method: "fallback_heuristic"`, and the exact primary failure cause (`exception_raised`, `low_confidence`, `service_timeout`).
- **No Fabricated Probabilities**: Heuristic scores are bounded between `0.20` and `0.92` to avoid falsely mimicking calibrated Bayesian probabilities.
- **Fail-Safe Gating**: Indeterminate visual features return `predicted_category: "unknown"` with `requires_review: true` to prevent hazardous or electronic waste from being misclassified as compostable organic waste.

---

## 8. Adafruit IO MQTT Integration

WasteDash ingests real-time telemetry from smart bins and truck scales via Adafruit IO's cloud MQTT broker.

### Broker Specifications
- **Host**: `io.adafruit.com`
- **Port**: `8883` (MQTT over TLS)
- **Transport**: Encrypted TLS with system CA certificate verification
- **Authentication**: `ADAFRUIT_IO_USERNAME` and `ADAFRUIT_IO_KEY`

### Feed & Topic Architecture
Topics follow the canonical Adafruit IO feed pattern:
`<ADAFRUIT_IO_USERNAME>/feeds/<feed-key>`

| Telemetry Measurement | Default Feed Key | Supported Data Format | Valid Range |
|---|---|---|---|
| **Bin Fill Percentage** | `wastedash-bin-fill` | Scalar float or JSON `{ "value": 78.5, "device_id": "BIN-102-01" }` | `0.0% – 100.0%` |
| **Truck Scale Weight** | `wastedash-weight-kg` | Scalar float or JSON `{ "weight_kg": 420.0 }` | `0.0 – 50,000.0 kg` |
| **Ultrasonic Distance** | `wastedash-distance-cm` | Distance to waste pile surface in cm | `2.0 – 400.0 cm` |
| **Device Status & Battery** | `wastedash-device-status` | JSON `{ "battery_pct": 88.0, "temp_c": 31.5 }` | Clamped to physical limits |

### Resilience Features
- **Deduplication**: In-memory LRU tracking discards repeated message payloads.
- **Stale Telemetry Indication**: Telemetry older than 5 minutes is flagged as stale (`is_stale: true`) on the dashboard.
- **Exponential Reconnection Backoff**: Background reconnects back off from 2 seconds to 60 seconds without blocking API startup.
- **Hardware Firmware**: Tested ESP32 code is provided in `iot/esp32_hx711_scale/esp32_hx711_scale.ino`.

---

## 9. Real-Time Simulation Engine

When physical IoT devices or GPS trucks are not actively transmitting, the backend provides a bounded synthetic simulation engine (`SIMULATION_MODE=true`):
- **Data Provenance**: All synthetic records carry explicit fields:
  ```python
  is_simulated = True
  data_source = "simulation"
  ```
- **Bounded Retention**: Telemetry records are capped at 500 records per device to prevent uncontrolled database growth.
- **Controlled Lifecycle**: Can be dynamically toggled via the API:
  - `POST /api/simulation/start`
  - `POST /api/simulation/stop`
  - `GET /api/simulation/status`

---

## 10. Automated Testing & Verification

The test suite validates end-to-end functionality across all subsystems:

```bash
# Activate virtual environment
source .venv/bin/activate

# 1. Run AI Fallback & Adafruit IO MQTT test suites (27 tests)
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_ai_fallback.py backend/tests/test_adafruit_mqtt.py -v

# 2. Run Authentication & RBAC API test suite (12 tests)
PYTHONPATH=backend .venv/bin/python backend/test_auth_api.py

# 3. Run Admin, Dataset Review, Training & Detection flow (14 tests)
PYTHONPATH=backend .venv/bin/python backend/test_admin_training_flow.py

# 4. Verify Frontend Production Build (33 static pages)
cd frontend
npm run build
```

---

## 11. Production Preparation for Render

To prepare for cloud deployment on Render (without modifying live infrastructure):

### 1. Provision 3 Isolated PostgreSQL Instances
Create three PostgreSQL databases in your Render dashboard:
1. `wastedash-users-db`
2. `wastedash-staff-db`
3. `wastedash-operations-db`

### 2. Configure Backend Web Service
- **Environment**: Python 3
- **Build Command**: `pip install -r backend/requirements.txt`
- **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `USER_DATABASE_URL`: Connection string from `wastedash-users-db`
  - `STAFF_DATABASE_URL`: Connection string from `wastedash-staff-db`
  - `WASTE_DATABASE_URL`: Connection string from `wastedash-operations-db`
  - `JWT_SECRET_KEY`: Secure 64-character random hex string
  - `ADAFRUIT_IO_USERNAME`: Configured Adafruit IO username
  - `ADAFRUIT_IO_KEY`: Configured Adafruit IO AIO key
  - `SIMULATION_MODE`: `false` (in strict production) or `true` (for municipal demo)
  - `FRONTEND_ORIGIN`: Deployed Render frontend URL

### 3. Configure Frontend Web Service
- **Environment**: Node
- **Build Command**: `cd frontend && npm install && npm run build`
- **Start Command**: `cd frontend && npm start`
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: `https://<your-backend-service>.onrender.com/api`

---

## 12. Troubleshooting

| Issue | Probable Cause | Resolution |
|---|---|---|
| `OperationalError: no such table` | Database has not been initialized | Run `python backend/migrate_legacy_db.py` to create tables in all 3 databases. |
| `KeyError: 'ADAFRUIT_IO_KEY'` | Environment variables missing | Copy `.env.example` to `.env` and fill in credentials. |
| MQTT connects with status `Disconnected` | Network or firewall blocks port 8883 | Ensure outbound TCP port `8883` is open for TLS traffic to `io.adafruit.com`. |
| AI prediction indicates `fallback_heuristic` | Primary deep learning model not loaded | Normal behavior when running on lightweight CPU hosts without heavy YOLO weights. |
| Frontend displays `API Connection Error` | Backend not running or CORS mismatch | Verify backend is running on `127.0.0.1:8000` and `FRONTEND_ORIGIN` matches frontend host. |

---

## 13. License & Attribution

Designed and developed for Greater Chennai Corporation (GCC) Solid Waste Management (SWM) AI Optimization Initiative. Licensed under the MIT License.