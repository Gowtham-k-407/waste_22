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
└────────────────┬────────────────┘           └─────────────────────────────────┘
                 │
                 │ Single PostgreSQL Connection Pool (DATABASE_URL)
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               RENDER CONSOLIDATED POSTGRESQL DATABASE           │
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ Domain: users   │  │ Domain: staff    │  │ Domain: waste_  │ │
│  │ Accounts & Auth │  │ Profiles & Roles │  │ management      │ │
│  │ (users.* views) │  │ (staff.* views)  │  │ (waste_mgmt.*)  │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
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
| `DATABASE_URL` | **Yes** | `postgresql://user:pass@dpg-abc123-a.render.com/wastedash` | Consolidated Render PostgreSQL Internal Connection URI |
| `USER_DATABASE_URL` | No | *(Defaults to `DATABASE_URL`)* | Optional domain alias (backward compatibility) |
| `STAFF_DATABASE_URL` | No | *(Defaults to `DATABASE_URL`)* | Optional domain alias (backward compatibility) |
| `WASTE_DATABASE_URL` | No | *(Defaults to `DATABASE_URL`)* | Optional domain alias (backward compatibility) |
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

## 3. Database Architecture & Render PostgreSQL Provisioning

### Consolidated Architecture with Three Logical Domains
The application consolidates all data into a single PostgreSQL database with connection pooling while strictly maintaining three logical domains:
1. **Domain: `users`**: Citizen and admin accounts, bcrypt password hashes, password reset tokens, authentication audit logs, and AI reference linkages.
2. **Domain: `waste_management`**: Municipal zones (15), wards (200), processing plants (12), collection fleet (24 vehicles), waste categories (11), detections, complaints, IoT telemetry, and recommendations.
3. **Domain: `staff`**: Municipal staff profiles (35 designations), duty assignments, and staff audit logs.

PostgreSQL schemas (`users`, `staff`, `waste_management`) and updatable domain views provide full domain encapsulation without altering existing ORM queries.

### Step-by-Step Render PostgreSQL Provisioning

1. In the Render Dashboard, click **New +** → **PostgreSQL**.
2. Configure the database instance:
   - **Name**: `wastedash-postgres`
   - **Database**: `wastedash`
   - **User**: `wastedash_admin`
   - **Region**: Choose the same region as the backend service (e.g. `Oregon (US West)` or `Frankfurt`) for low-latency private networking.
   - **Plan**: `Starter` or higher (free tier can be used for initial testing).
3. Copy the **Internal Database URL** (e.g., `postgres://wastedash_admin:...@dpg-xxxx-a.render.com/wastedash`).
   - Private networking within Render eliminates public internet egress latency and egress costs.
4. Set the environment variable in the Backend Web Service:
   - `DATABASE_URL` = `[Paste the Render Internal Database URL]`
   - *(Note: `APP_ENV=production` ensures no fallback to SQLite can ever occur in production).*

> [!NOTE]
> Render provides database URLs starting with `postgres://`. The WasteDash configuration engine (`normalize_database_url` in `backend/app/core/config.py`) automatically translates this prefix to `postgresql+psycopg2://` to enforce the high-performance psycopg2 driver.

### Database Migration & Zero-Downtime Deployment Sequence

Follow this safe cutover sequence:

```
1. Provision PostgreSQL on Render
               │
               ▼
2. Configure DATABASE_URL in Render Backend Environment
               │
               ▼
3. Run Alembic Schema Migrations
   Command: alembic upgrade head
               │
               ▼
4. Run Repeatable Data Migration & Integrity Verification
   Command: python backend/migrate_to_postgres.py
               │
               ▼
5. Verify Health Check (/api/health)
   Response: {"status": "healthy", "database": {"engine": "postgresql", ...}}
               │
               ▼
6. Complete Production Cutover
```

#### Running the Migration Script
The migration utility handles SHA-256 backup creation, topological table ordering, type conversion, idempotent inserts, and sequence synchronization:
```bash
# Set target URL and execute migration:
DATABASE_URL="postgresql://wastedash_admin:password@dpg-xxxx-a.render.com/wastedash" python backend/migrate_to_postgres.py
```
Key safety guarantees:
- **Verified Backups**: Automatically creates timestamped SHA-256 checksummed backups of all three SQLite files in `backend/backups/`.
- **Zero Data Loss**: Preserves all IDs, bcrypt password hashes, and cross-domain relationships.
- **Idempotent**: Safe to re-run; uses `ON CONFLICT DO NOTHING` to prevent duplicates.
- **Sequence Synchronization**: Automatically aligns all PostgreSQL auto-increment sequences (`nextval`) to `MAX(id) + 1`.
- **Rollback Procedure**: In the unlikely event of an issue, restoring the original SQLite databases from `backend/backups/` and reverting `DATABASE_URL` restores immediate operational state.

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
