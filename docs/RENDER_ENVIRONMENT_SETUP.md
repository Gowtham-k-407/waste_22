# WasteDash — Render Deployment & Environment Configuration Guide
### Greater Chennai Corporation (GCC) Municipal Solid Waste Segregation & AI Platform

This guide provides complete, deployment-ready environment variable checklists, database provisioning steps, and secret-handling procedures for hosting the WasteDash platform on [Render](https://render.com).

---

## 1. Architectural Overview on Render

WasteDash is structured to run as distinct, decoupled cloud resources on Render:

```
┌─────────────────────────────────┐
│       RENDER WEB SERVICE        │
│       Frontend (Next.js)        │
│  e.g. waste-frontend.onrender   │
└────────────────┬────────────────┘
                 │ HTTPS (REST)
                 ▼
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│       RENDER WEB SERVICE        │  Private  │       RENDER WEB SERVICE        │
│       Backend (FastAPI)         │──────────▶│   AI Inference Microservice     │
│    e.g. waste-22.onrender.com   │   HTTP    │   (Optional Standalone Worker)  │
└───────┬────────┬────────┬───────┘           └─────────────────────────────────┘
        │        │        │
        │        │        │ Private PostgreSQL Connections
        ▼        ▼        ▼
┌──────────────┬──────────────┬──────────────┐
│  DATABASE A  │  DATABASE B  │  DATABASE C  │
│  User & Auth │    Staff     │  Operations  │
│  PostgreSQL  │  PostgreSQL  │  PostgreSQL  │
└──────────────┴──────────────┴──────────────┘
```

---

## 2. Render Service Checklists

### A. Frontend Web Service (Next.js)

- **Service Type**: Web Service
- **Environment**: Node
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`
- **Auto-Deploy**: Yes (on git push to `main`)

#### Environment Variables Checklist

| Variable Name | Required | Example / Recommended Value | Description |
|---|:---:|---|---|
| `NODE_VERSION` | Yes | `18.20.0` or `20.12.0` | Node.js runtime version |
| `NEXT_PUBLIC_API_URL` | **Yes** | `https://waste-22.onrender.com/api` | Public URL of the deployed Backend API (must include `/api`) |
| `NEXT_PUBLIC_MUNICIPALITY_NAME` | No | `Greater Chennai Corporation` | Municipal display name |
| `NEXT_PUBLIC_DEFAULT_CITY` | No | `Chennai` | Default regional context |
| `NEXT_PUBLIC_APP_VERSION` | No | `2.2.0` | Frontend release version |

> [!CAUTION]
> **Zero-Secret Rule**: Never add database passwords, JWT secrets, S3 credentials, or Adafruit IO keys to the Frontend service. Next.js bakes `NEXT_PUBLIC_*` variables directly into public browser JavaScript bundles.

---

### B. Backend Web Service (FastAPI)

- **Service Type**: Web Service
- **Environment**: Python 3
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/health`

#### Environment Variables Checklist

| Variable Name | Required | Example / Recommended Value | Description |
|---|:---:|---|---|
| `PYTHON_VERSION` | Yes | `3.12.3` | Python runtime version |
| `APP_ENV` | Yes | `production` | Application mode |
| `DEBUG` | Yes | `false` | Disable debug logs in production |
| `PROJECT_NAME` | No | `Chennai Solid Waste Segregation & AI Optimization Platform` | OpenAPI & API banner title |
| `API_V1_STR` | No | `/api` | Base API router prefix |
| `JWT_SECRET_KEY` | **Yes** | `[Generate 64-char hex string]` | Secret key used to sign JWT tokens |
| `ALGORITHM` | No | `HS256` | JWT signature algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `10080` | Session expiration in minutes (7 days) |
| `CORS_ORIGINS` | **Yes** | `https://<your-frontend>.onrender.com,http://localhost:3000` | Comma-separated allowed web origins |
| `USER_DATABASE_URL` | **Yes** | `postgresql://user:pass@dpg-users.render.com/wastedash_users` | Render Database A connection URI |
| `STAFF_DATABASE_URL` | **Yes** | `postgresql://user:pass@dpg-staff.render.com/wastedash_staff` | Render Database B connection URI |
| `WASTE_DATABASE_URL` | **Yes** | `postgresql://user:pass@dpg-ops.render.com/wastedash_operations` | Render Database C connection URI |
| `DATABASE_URL` | No | *(Defaults to `WASTE_DATABASE_URL`)* | Legacy compatibility pointer |
| `STORAGE_PROVIDER` | No | `local` *(or `s3` for cloud storage)* | File storage driver (`local` or `s3`) |
| `STORAGE_BUCKET` | If s3 | `wastedash-production-assets` | S3 bucket name |
| `STORAGE_ENDPOINT` | If s3 | *(Optional for Cloudflare R2 / MinIO)* | Custom S3 endpoint URL |
| `STORAGE_ACCESS_KEY` | If s3 | `[Supplied by AWS/Cloudflare]` | Cloud storage access key ID |
| `STORAGE_SECRET_KEY` | If s3 | `[Supplied by AWS/Cloudflare]` | Cloud storage secret key |
| `STORAGE_REGION` | If s3 | `ap-south-1` | Cloud storage region |
| `ADAFRUIT_IO_USERNAME` | **Yes** | `[Your Adafruit IO username]` | Adafruit IO account identifier |
| `ADAFRUIT_IO_KEY` | **Yes** | `[Your Adafruit IO AIO Key]` | Adafruit IO active authentication key |
| `ADAFRUIT_IO_HOST` | No | `io.adafruit.com` | Secure MQTT broker host |
| `ADAFRUIT_IO_PORT` | No | `8883` | Secure TLS MQTT port |
| `ADAFRUIT_IO_USE_TLS` | No | `true` | Enforce TLS certificate validation |
| `ADAFRUIT_IO_FEED_PREFIX` | No | `wastedash` | Feed namespace prefix |
| `ADAFRUIT_IO_FEEDS` | No | `wastedash-telemetry,wastedash-bin-fill,wastedash-scale-weight,wastedash-temperature,wastedash-humidity,wastedash-device-status` | Comma-separated feed keys to subscribe |
| `FALLBACK_CLASSIFICATION_ENABLED` | No | `true` | Enable 5-layer classical CV fallback |
| `AI_CONFIDENCE_THRESHOLD` | No | `0.45` | Fallback activation confidence threshold |
| `FRAME_SAMPLING_INTERVAL_MS` | No | `300` | Sampling rate for video frames |
| `MAX_IMAGE_SIZE_MB` | No | `15.0` | Maximum upload size in megabytes |
| `INFERENCE_TIMEOUT_SECONDS` | No | `15.0` | Maximum seconds before fallback triggers |
| `TRAINING_THRESHOLD` | No | `500` | Validated images to trigger retraining |
| `AI_INFERENCE_URL` | No | `https://<your-ai-service>.onrender.com` | URL of decoupled AI microservice (leave empty if in-process) |
| `AI_INFERENCE_API_KEY` | If AI micro | `[Shared Secret Key]` | Shared secret key matching AI service |
| `SIMULATION_MODE` | **Yes** | `false` *(production)* or `true` *(demo)* | Enable bounded simulation engine |
| `SIMULATION_TICK_SECONDS` | No | `8` | Interval between simulated fleet ticks |
| `ADMIN_BOOTSTRAP_EMAIL` | No | `admin@wastesegeregate.in` | Temporary bootstrap admin email |
| `ADMIN_BOOTSTRAP_PASSWORD` | No | `[Change on first login]` | Temporary bootstrap admin password |

---

### C. Standalone AI Inference Service (Optional Render Service)

*If deploying computer vision inference as a separate Render Web Service to scale independently from the core API:*

- **Service Type**: Web Service
- **Environment**: Python 3
- **Root Directory**: `ai-service`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`

#### Environment Variables Checklist

| Variable Name | Required | Example / Recommended Value | Description |
|---|:---:|---|---|
| `PYTHON_VERSION` | Yes | `3.12.3` | Python runtime version |
| `AI_SERVICE_ENV` | No | `production` | Runtime mode |
| `AI_SERVICE_API_KEY` | **Yes** | `[Shared Secret Key]` | API key (must match backend's `AI_INFERENCE_API_KEY`) |
| `ALLOWED_ORIGINS` | Yes | `https://waste-22.onrender.com` | Backend API hostname permitted to invoke inference |
| `MODEL_FRAMEWORK` | No | `pytorch_yolov8` | Vision inference engine |
| `MODEL_WEIGHTS_PATH` | No | `models_checkpoints/yolov8_waste.pt` | Path to primary weights |
| `FALLBACK_MODEL_PATH` | No | `models_checkpoints/classifier_v2.1.pt` | Path to candidate weights |
| `DEVICE` | No | `cpu` | Execution hardware target (`cpu` on standard Render tiers) |
| `CONFIDENCE_THRESHOLD` | No | `0.45` | Model detection threshold |
| `BATCH_SIZE` | No | `16` | Max batch size |

---

## 3. Database Safety & Render PostgreSQL Provisioning

### Why Three Databases?
Monolithic municipal applications often fail security audits when operational telemetry shares physical tables with citizen authentication data and employee records. WasteDash uses three isolated schemas:
1. **Database A (`USER_DATABASE_URL`)**: Citizen accounts, Bcrypt hashes, password resets, audit logs.
2. **Database B (`STAFF_DATABASE_URL`)**: 35 GCC municipal staff designations, employee IDs, ward boundaries.
3. **Database C (`WASTE_DATABASE_URL`)**: 200 Wards, 12 Plants, 24 Vehicles, IoT Telemetry, Grievances, AI Datasets.

### Step-by-Step Render PostgreSQL Provisioning

1. In the Render Dashboard, click **New +** → **PostgreSQL**.
2. Create **Database 1**:
   - **Name**: `wastedash-users-db`
   - **Database**: `wastedash_users`
   - **User**: `user_admin`
   - Copy the **Internal Database URL** (e.g., `postgres://user_admin:...@dpg-xxxx-a.render.com/wastedash_users`)
   - Assign to Backend environment variable: `USER_DATABASE_URL`
3. Create **Database 2**:
   - **Name**: `wastedash-staff-db`
   - **Database**: `wastedash_staff`
   - **User**: `staff_admin`
   - Copy the **Internal Database URL**
   - Assign to Backend environment variable: `STAFF_DATABASE_URL`
4. Create **Database 3**:
   - **Name**: `wastedash-operations-db`
   - **Database**: `wastedash_operations`
   - **User**: `ops_admin`
   - Copy the **Internal Database URL**
   - Assign to Backend environment variable: `WASTE_DATABASE_URL`

> [!NOTE]
> Render provides database URLs starting with `postgres://`. The WasteDash configuration engine (`normalize_database_url` in `backend/app/core/config.py`) automatically translates this prefix to `postgresql://` to satisfy modern SQLAlchemy requirements.

### Safe Data Migration from Local SQLite to Render PostgreSQL

To populate initial municipal taxonomy without losing data:
1. Set the remote connection strings in a temporary migration environment.
2. Run the idempotent migration utility:
   ```bash
   python backend/migrate_legacy_db.py
   ```
3. The script creates schemas, applies necessary indexes, seeds initial GCC taxonomy (200 wards, 12 plants, 24 vehicles), and validates record counts.

---

## 4. Secret Management & Values You Must Supply

When deploying to Render, the following credentials must be generated or provided manually:

1. **`JWT_SECRET_KEY`**:
   - Generate via terminal:
     ```bash
     openssl rand -hex 32
     ```
   - Paste the resulting 64-character string into the Render Backend Environment settings.

2. **`ADAFRUIT_IO_USERNAME` & `ADAFRUIT_IO_KEY`**:
   - Log in to [io.adafruit.com](https://io.adafruit.com).
   - Click **My Key** (yellow key icon) in the header.
   - Copy your **Username** and **Active Key**.
   - Paste them into `ADAFRUIT_IO_USERNAME` and `ADAFRUIT_IO_KEY` in the Render Backend settings.

3. **`AI_INFERENCE_API_KEY`** *(Optional)*:
   - If using a decoupled AI microservice, generate a random 32-character key and set it identically on both the Backend and the AI Service.

4. **Production Admin Password Rotation**:
   - The initial bootstrap password (`admin123`) is strictly for initialization. Log in as `admin@wastesegeregate.in` immediately after deployment and rotate the password via the Profile Settings page.

---

## 5. Verification Commands

To verify your configuration locally before committing:

```bash
# 1. Run all unit and integration tests
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_ai_fallback.py backend/tests/test_adafruit_mqtt.py

# 2. Verify Authentication and RBAC endpoints
PYTHONPATH=backend .venv/bin/python backend/test_auth_api.py

# 3. Verify Admin flow, Dataset verification & AI training
PYTHONPATH=backend .venv/bin/python backend/test_admin_training_flow.py

# 4. Verify Next.js production build succeeds with environment variables
cd frontend && npm run build
```
