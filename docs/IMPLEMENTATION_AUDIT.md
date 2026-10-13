# Phase One Implementation Audit — WasteDash / GCC Smart Waste Platform

**Document Version:** 1.0.0  
**Repository:** `Automated-Commercial-Solid-Waste-Segregation-Optimization-Dashboard-for-Municipal-Recycling-Plants`  
**Date:** October 2026  
**Auditor:** Senior Full-Stack, ML, MLOps, IoT & Cloud Deployment Engineering Agent  

---

## 1. Executive Summary & Baseline State

This repository implements the **Automated Commercial Solid Waste Segregation Optimization Dashboard for Municipal Recycling Plants (Greater Chennai Corporation)**. 
- **Frontend**: Next.js 14.2 (App Router), React 18, TypeScript, Tailwind CSS, Leaflet GIS, Recharts, Lucide React. Build status: **Clean production build (33 static pages compiled without errors)**.
- **Backend**: FastAPI 0.110+, SQLAlchemy 2.0, SQLite (`chennai_waste.db`), Uvicorn.
- **Current Deployment**: Render Backend at `https://waste-22.onrender.com/api` (active), Frontend default API URL configured to Render backend.

While the user interface, navigation, and SQLite schemas are mature, the audit identifies critical architectural gaps:
1. Classification inference in `ai_vision_service.py` is heuristic (filename keyword parsing, RGB channel heuristics, synthetic bounding boxes) rather than genuine deep learning neural inference.
2. Model retraining in `training_worker.py` is a time-sleep simulation producing synthetic exponential decay loss curves.
3. Fleet telemetry and vehicle locations are static database seeds; MQTT IoT telemetry is mocked.
4. Database is single-node SQLite without Alembic migrations or managed PostgreSQL support.
5. Uploaded images are saved to local disk (`backend/uploads`) without cloud object storage abstraction.
6. The Model Switch feature only toggles a database boolean without swapping actual inference model weights.

---

## 2. Existing Functional Modules

The following components are genuinely implemented, verified, and operational:

1. **Authentication & Role-Based Access Control (RBAC)**:
   - File: `backend/app/api/auth.py`, `backend/app/core/security.py`, `frontend/lib/auth-context.tsx`.
   - Passlib Bcrypt password hashing, JWT token issuance with 7-day expiration.
   - 6 Defined Municipal Roles: `public`, `contributor`, `municipal_officer`, `plant_operator`, `ai_admin`, `system_admin`.
   - Full user profile management, password change/reset workflows, and registration bonus mechanics.

2. **Municipal Reference Data & Geographic Schema**:
   - File: `backend/app/services/seed_service.py`, `backend/app/models/geography.py`, `facility.py`, `vehicle.py`.
   - 15 Greater Chennai Corporation Zones (Thiruvottiyur to Sholinganallur).
   - 200 GCC Wards with population densities, collection schedules, and daily tonnage estimates.
   - 12 Waste Segregation Facilities (Perungudi, Kodungaiyur, Madhavaram Bio-CNG, etc.).
   - 24 Smart Collection Trucks (GC-01 to GC-24).
   - 11 Standardized Municipal Waste Streams.

3. **Leaflet GIS Map (`/map`)**:
   - File: `frontend/components/LeafletMap.tsx`, `frontend/app/map/page.tsx`.
   - OpenStreetMap base layer with Chennai boundary coordinates.
   - Entity inspector for vehicles, facilities, and ward intensity zones.

4. **128-Dimensional Visual Feature Embeddings & Personal AI Memory**:
   - File: `backend/app/services/ai_vision_service.py`, `backend/app/api/memory.py`, `frontend/app/my-ai-memory/page.tsx`.
   - Luminance grid (64-d), edge gradients (32-d), morphology (16-d), and texture energy (16-d) L2-normalized feature vectors.
   - Cosine similarity matching against private user references for personalized classifications.

5. **Citizen Upload & Administrative Verification Queue**:
   - File: `backend/app/api/uploads.py`, `backend/app/api/admin_portal.py`, `frontend/app/admin/page.tsx`.
   - Image upload pipeline with blur checking (Laplacian variance) and duplicate detection (SHA-256).
   - Admin single/batch approval, label correction, and rejection reason tracking.

6. **Verified Dataset Hub & Export**:
   - File: `backend/app/api/admin_portal.py:348-430`, `frontend/app/admin/dataset/page.tsx`.
   - Search, train/val/test split tagging, JSON and CSV exports.

7. **Alerts & Incident Dispatch**:
   - File: `backend/app/api/alerts.py`, `frontend/app/alerts/page.tsx`.
   - Critical/High/Medium alert filtering and status resolution.

---

## 3. Simulated, Heuristic, or Mock Modules

The audit identified the following simulated or heuristic modules:

1. **AI Inference (`AIVisionService.detect_and_classify`)**:
   - Heuristics: Uses `filename_hint` string matching (e.g. `any(term in hint for term in ["phone", "mobile"])`), aspect ratio ranges, and RGB channel averages.
   - Bounding boxes: Generated algorithmically via `random.uniform()`.
   - Claimed framework: "PyTorch 2.2 / YOLOv8-Waste", but no PyTorch model or YOLO `.pt` file is executed.

2. **Model Retraining Pipeline (`training_worker.py`)**:
   - Simulated: Executes a background thread with `time.sleep(0.9)` per epoch. Calculates synthetic loss curves via `start_train_loss * ((end_train_loss / start_train_loss) ** ratio)`.
   - No neural network weights are trained or exported.

3. **Fleet IoT & Telemetry**:
   - Static: 24 collection vehicles have fixed or random coordinates generated during DB seed.
   - MQTT URL `mqtt://iot.chennaiswm.gov.in/fleet/detections` is descriptive text; no MQTT client connection is established.

4. **Waste Composition Trends (`/waste/composition-trends`)**:
   - Hardcoded: `backend/app/api/waste.py:14-33` returns static monthly series arrays without querying waste records.

5. **External Data Connectors (`data_connector_service.py`)**:
   - Static Catalog: Lists URLs for GCC and CPCB without active synchronization or live scraping.

6. **Model Switch / Rollback**:
   - Toggles `is_active_production` in `ai_models` database table, but does not alter the underlying inference logic since inference is hardcoded in `ai_vision_service.py`.

---

## 4. Broken or Incomplete Integrations

1. **Test Environment Dependency**:
   - FastAPI `TestClient` required `httpx`, which was omitted from `requirements.txt`. (Fixed during baseline setup).
2. **Missing Persistent Storage Backend**:
   - Image files are stored in local `backend/uploads/`. On cloud platforms like Render with ephemeral disks, user uploads and model checkpoints are lost upon container restart.
3. **Frontend API URL Ambiguity**:
   - `frontend/lib/api.ts` defaults to Render (`https://waste-22.onrender.com/api`) when `NEXT_PUBLIC_API_URL` is omitted, causing confusion during local offline development.
4. **Email Dispatch**:
   - Password reset tokens are generated in the database, but no email provider is connected to send the reset link.

---

## 5. Database and Persistence Risks

1. **SQLite Concurrency & Ephemeral Storage on Render**:
   - SQLite locks entire database on write, leading to `database is locked` errors during concurrent uploads and training telemetry updates.
   - Ephemeral disk on Render wipes local SQLite file on deploy unless using external PostgreSQL.
2. **Missing Migration Framework**:
   - Tables were created using `Base.metadata.create_all(bind=engine)` without Alembic migrations, risking schema drift.
3. **Non-Idempotent Seed Execution Risk**:
   - While `seed_service.py` checks existing counts, adding new seed entities can duplicate entries without strict unique constraints.

---

## 6. AI Model and Dataset Compatibility Issues

1. **Inference Memory Budget on Free-Tier Hosting**:
   - Free/Starter hosting limits RAM to 512MB–1GB. Loading heavyweight multi-gigabyte models can trigger Out-Of-Memory (OOM) termination.
   - Solution: Use lightweight, efficient pretrained vision architectures (e.g., MobileNetV3 / EfficientNet-B0 or optimized ONNX models with manageable footprints under 50MB) and support decoupled inference endpoints via `AI_INFERENCE_URL`.
2. **11-Class Municipal Taxonomy Alignment**:
   - Public datasets (such as TACO or TrashNet) have distinct class taxonomies (e.g., 6 classes in TrashNet, 60 in TACO).
   - An explicit, robust category mapping layer is required to translate model outputs into the GCC 11 municipal categories (`Organic Waste`, `Food Waste`, `Plastic`, `Paper`, `Cardboard`, `Glass`, `Metal`, `Textile Waste`, `Electronic Waste`, `Hazardous Waste`, `Mixed Waste`).

---

## 7. Security and Deployment Risks

1. **Hardcoded Fallbacks in Source**:
   - `config.py` contains default secret keys; must strictly support `os.getenv("JWT_SECRET_KEY")`.
2. **Unauthenticated Image Static Mount**:
   - `/uploads` is mounted via `StaticFiles(directory=settings.MEDIA_DIR)` without access control checks for private references.
3. **Ephemeral File System**:
   - Uploaded citizen photos and candidate model weights require a persistent cloud storage abstraction (S3/R2/Local file provider interface).

---

## 8. Ordered Implementation Plan

| Phase | Milestone | Objective |
|---|---|---|
| **Phase 2** | Cloud Database & Storage | Implement PostgreSQL support via SQLAlchemy 2.x, Alembic migrations, idempotent seeding, and S3-compatible/Local pluggable storage provider. |
| **Phase 3** | Real AI Vision Inference | Integrate actual neural vision classification (Hugging Face / PyTorch / ONNX), remove filename/RGB heuristics, build model abstraction layer with category mapping. |
| **Phase 4** | Dataset Ingestion & Seeding | Command-line dataset ingestion (`python -m app.scripts.import_waste_dataset`) with real provenance tracking and attribution. |
| **Phase 5** | Genuine Contribution & Training | Human-in-the-loop workflow: admin approval triggers real transfer-learning fine-tuning worker; genuine loss curves & checkpoint generation. |
| **Phase 6** | Model Switching & Rollback | End-to-end atomic model switching: database pointer updates, inference engine reloads active weights, automated rollback on failure. |
| **Phase 7** | Extensible IoT Architecture | Paho MQTT client integration, time-series telemetry persistence, deterministic IoT simulator, and ESP32 Arduino/C++ firmware starter code. |
| **Phase 8** | Real-Time Analytics & Calculations | Replace hardcoded trends with real database queries; implement deterministic routing solver for fleet optimization. |
| **Phase 9** | Security & RBAC Hardening | Backend server-side permission enforcement on all privileged routes, rate limiting, and private storage signed URL access. |
| **Phase 10** | API Reliability & Frontend Integration | Update `frontend/lib/api.ts` with error normalization, dual local/cloud support, and build validation. |
| **Phase 11** | Comprehensive Automated Testing | Full test suite: DB tests, AI inference tests, training tests, MQTT tests, and frontend build verification. |
| **Phase 12** | Deployment & Documentation | Production `.env.example`, deployment guides, and final `docs/IMPLEMENTATION_REPORT.md`. |
