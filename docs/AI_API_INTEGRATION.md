# WasteDash — Laptop-Hosted AI API Server Integration Guide
### Distributed Architecture: Render Cloud Backend + Local Laptop AI Compute Server

This guide documents the architectural integration between the cloud-hosted **WasteDash Main Project** (FastAPI backend + Next.js frontend deployed on Render) and the **Laptop-Hosted WasteDash AI API Microservice** (running locally on GPU/CPU laptop hardware).

---

## 1. Architectural Architecture & Service Boundaries

```
┌────────────────────────────────────────────────────────┐
│                   BROWSER / CLIENT                     │
│               Next.js Frontend (Render)                │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS (/api/*)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   MAIN BACKEND                         │
│               FastAPI Gateway (Render)                 │
│                                                        │
│  - JWT Authentication & Strict RBAC Enforcement        │
│  - Database A (Users), B (Staff), C (Waste Operations) │
│  - Classical OpenCV Multi-Cue Fallback Engine          │
│  - AIServiceClient (Connection Pooling, Fast Timeouts) │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ Secure Tunnel / Public Ingress
                            │ (Header: X-API-Key / Bearer Token)
                            ▼
┌────────────────────────────────────────────────────────┐
│               LAPTOP AI COMPUTE SERVER                 │
│           Standalone AI API (Port 8001)                │
│                                                        │
│  - ResNet50 Waste Classifier (PyTorch)                 │
│  - YOLO11n Real-Time Detector (Ultralytics)            │
│  - Asynchronous Retraining Pipeline & Checkpointing    │
│  - Candidate Evaluation Gates & Model Registry         │
└────────────────────────────────────────────────────────┘
```

### Key Architectural Tenets
1. **Zero Cloud AI Compute Costs**: Heavy neural inference, matrix multiplications, PyTorch transfer learning, and model checkpointing execute exclusively on the user's laptop.
2. **Main Backend as Authoritative Gateway**: The browser **never** talks to the laptop AI API directly. The frontend only communicates with the Render backend via `/api`.
3. **Additive Health & Graceful Degradation**: If the laptop is closed, offline, or experiencing network latency, the main backend continues operating without 500 errors, utilizing its built-in classical OpenCV computer vision engine as an immediate failover.
4. **Zero-Secret Rule**: The laptop AI URL, service API tokens, and admin tokens remain strictly in the Render backend's environment variables. They are **never** prefixed with `NEXT_PUBLIC_` or leaked to frontend JavaScript bundles.

---

## 2. Network Architecture: Connecting Render to Laptop

### The Challenge
- In a cloud container environment like Render, `http://127.0.0.1` or `http://localhost` resolves **inside the Render container itself**, not your laptop.
- Private RFC 1918 LAN addresses (e.g., `http://192.168.1.50:8001` or `http://10.79.x.x:8001`) are **non-routable** over the public internet.

### Supported Ingress Options

| Mechanism | Description | Best For | Security |
|---|---|---|---|
| **Cloudflare Tunnel (Recommended)** | `cloudflared tunnel --url http://localhost:8001` generates a secure HTTPS tunnel hostname (e.g. `https://wastedash-ai.yourdomain.com`). | Production Render deployment | TLS 1.3 encrypted, zero open inbound firewall ports. |
| **Tailscale / WireGuard** | Private mesh VPN joining Render container to laptop subnet. | Private enterprise networks | WireGuard peer-to-peer encryption. |
| **ngrok / localtunnel** | `ngrok http 8001` provides temporary public HTTPS forwarding. | Quick debugging and integration testing | HTTPS tunnel with token authorization. |
| **Direct LAN IP** | `http://192.168.x.x:8001` | **Local development only** (when backend and frontend are also running on the local network). | LAN-only access. |

---

## 3. Environment Variables Configuration

### Render Backend Web Service Environment
Configure these variables in the Render Dashboard (**Dashboard -> Backend Service -> Environment**):

```bash
# ==============================================================================
# Laptop AI Compute Server Integration Settings
# ==============================================================================
AI_API_BASE_URL=https://your-laptop-tunnel.trycloudflare.com
AI_API_TOKEN=your_secure_random_ai_service_token
AI_ADMIN_API_KEY=your_secure_random_ai_admin_token

# Connection & Read Timeouts
AI_API_CONNECT_TIMEOUT_SECONDS=3.0
AI_API_TIMEOUT_SECONDS=60.0

# HTTP Connection Pool Controls
AI_API_POOL_CONNECTIONS=10
AI_API_POOL_MAXSIZE=25
AI_API_MAX_RETRIES=2

# Fallback Configuration
FALLBACK_CLASSIFICATION_ENABLED=true
AI_CONFIDENCE_THRESHOLD=0.45
```

### Local Development Environment (`backend/.env`)
When running both services on your laptop:

```bash
AI_API_BASE_URL=http://127.0.0.1:8001
AI_API_TOKEN=replace_with_secure_random_ai_service_key
AI_ADMIN_API_KEY=replace_with_secure_random_ai_admin_key
AI_API_CONNECT_TIMEOUT_SECONDS=3.0
AI_API_TIMEOUT_SECONDS=60.0
```

---

## 4. End-to-End Workflow Verification

### Workflow 1: Contributor Image Upload & Inference
1. **Submission**: An authenticated citizen or municipal officer uploads an image via the Next.js frontend:
   `POST /api/contributions/upload-and-predict`
2. **Main Backend Authorization**: Main backend validates JWT token, verifies file size (limit: 15MB), computes image SHA256 checksum, and evaluates image sharpness.
3. **Laptop Dispatch**: `AIServiceClient.classify_image()` forwards the binary stream to the laptop:
   `POST /api/v1/ai/predict/image` (with headers `X-API-Key: <AI_API_TOKEN>`)
4. **Laptop Inference**: The laptop runs the fine-tuned ResNet50 model and returns the predicted GCC category, confidence percentage, and taxonomic breakdown.
5. **Validation & Normalization**: The backend verifies the confidence threshold against `AI_CONFIDENCE_THRESHOLD` (0.45). If confidence is below threshold or the laptop is offline, the backend activates the OpenCV classical heuristic fallback without crashing.
6. **Persistence**: The classification is durably stored in Database C (`ImageContribution` table in `waste_management.db`).
7. **Response**: The frontend receives the exact existing response schema:
   ```json
   {
     "success": true,
     "contribution_id": 142,
     "predicted_category": "Plastic",
     "confidence": 0.942,
     "requires_review": false,
     "reward_points": 15
   }
   ```

### Workflow 2: Asynchronous Retraining on Laptop
1. **Trigger**: An authorized System Administrator or Municipal AI Manager triggers retraining:
   `POST /api/admin/train-model`
2. **RBAC Guard**: Ordinary contributors receive `403 Forbidden`. Only verified admin roles (`system_admin`, `ai_admin`, `municipal_officer`) can initiate training.
3. **Laptop Dispatch**: `AIServiceClient.submit_training_job()` sends the approved dataset manifest to:
   `POST /api/v1/ai/training/jobs` (with header `Authorization: Bearer <AI_ADMIN_API_KEY>`)
4. **Database Persistence**: The main backend inserts an active record into the `TrainingJob` table with the remote `job_code` (e.g. `JOB-REMOTE-20261018-091244`) and initial stage `initializing`.
5. **Telemetry Polling**: When authorized staff view `/admin/model-training`, the frontend calls `GET /api/admin/training-status`. The backend polls the laptop (`GET /api/v1/ai/training/jobs/{job_id}`) and synchronizes:
   - `progress_pct` (0.0% to 100.0%)
   - `current_epoch` / `total_epochs`
   - Training loss & validation loss
   - Validation Accuracy & F1 score
   - Real-time training logs
6. **Candidate Checkpointing**: When training finishes on the laptop, the evaluation gate verifies metrics (Accuracy >= 85%, F1 >= 85%). If passed, the candidate version is registered into `AIModelVersion` with status `candidate`.
7. **Model Activation**: Admin reviews metrics and clicks Activate (`POST /api/admin/models/{id}/activate`). The backend notifies the laptop (`POST /api/v1/ai/models/{version}/activate`), updates the active production flag in Database C, and archives previous models.

---

## 5. Offline Resilience & Failure Handling

| Failure Scenario | Backend Behavior | Result |
|---|---|---|
| **Laptop Offline / In Sleep Mode** | Connect timeout triggers after 3.0s fast-fail. `AIServiceUnavailableException` is caught. | Backend seamlessly falls back to OpenCV heuristic engine for live camera / uploads; health check reports `ai_service: {reachable: false}`; database and dashboards remain 100% operational. |
| **Laptop Network Drop During Retraining** | Status synchronization catches timeout gracefully without raising an uncaught exception. | Polling returns the last persisted state in Database C with a warning in logs; no 500 error thrown to user. |
| **Invalid / Incompatible Candidate Model** | Gate evaluation check rejects activation with HTTP 400. | Prevents broken or sub-threshold models from ever entering production. |
| **Unauthenticated Training Request** | Security dependency halts request before any remote networking code executes. | Returns HTTP 401 / 403 immediately; laptop server is never pinged. |
