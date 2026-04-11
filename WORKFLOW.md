# 🌿 Plant Advisor — Full System Workflow

## Overview
Plant Advisor is a full-stack AI-powered web application:
1. **Smart Recommender** — Personalized plant care reports
2. **Leaf Diagnostic** — Disease detection from photos

Stack: React + Firebase (frontend) | FastAPI + Qdrant + ML Models (backend) | GPT-4o → Qwen 2.5 7B fine-tuned (LLM).

---

## 🧱 High-Level Architecture

```
USER BROWSER
    │
    ▼
React Frontend
    │  Firebase Auth + Firestore
    ▼  HTTP / SSE
FastAPI Backend
    ├── Smart Recommender → LLM (GPT-4o / Qwen 2.5 7B FT) + Qdrant + Local DB
    └── Leaf Diagnostic   → YOLO + ViT ML Models
```

---

## 🔐 Authentication Flow

1. User visits → **LandingPage**
2. Login/Signup → **Firebase Auth**
3. **AuthContext** holds session globally in React
4. All feature routes in **ProtectedRoute** — redirects if not logged in
5. `/admin` additionally checks `adminOnly`

---

## 🌱 Smart Recommender — Full Workflow

### Step 1 — Language Selection (`/recommender`)
- `GET /api/languages` → available languages
- `GET /api/form-labels/{lang}` → all translated labels

### Step 2 — Plant Form (`/recommender/form`)
- Inputs: plant name, Country/Region/City, temperature, humidity, light, soil, watering, fertilizer, experience
- Location strings translated via `POST /api/translate-locations`
- Submit → `POST /api/analyze` → returns **session_id**

### Step 3 — Streaming Analysis (`/recommender/results`)
Frontend opens SSE to `GET /api/analyze-stream/{session_id}`.

Backend pipeline:
```
1. VALIDATE PLANT NAME (GPT-4o) → get English name
2. TRANSLATE inputs to English for DB lookup
3. DATABASE LOOKUP
   ├── Qdrant (remote, semantic, score > 0.5)  ← Primary
   └── Local JSON/Embeddings DB (data/)         ← Backup
4. IF data found  → build context → call LLM
   IF no data     → LLM generates profile → store to Qdrant + local DB
5. LLM — 2-Tier Fallback
   ├── Tier 1: GPT-4o              (OpenAI API)     ← Primary
   └── Tier 2: Qwen 2.5 7B FT     (Fine-tuned)     ← Fallback
6. REPORT — 3-Phase Markdown
   ├── Phase 1: Current Conditions Assessment
   ├── Phase 2: Environmental Match Analysis
   └── Phase 3: Action Plan (immediate/short-term/seasonal)
7. STREAM chunks → Frontend via SSE
```

### Step 4 — Results
- Report rendered live as Markdown
- `GET /api/download-report/{id}` → `.md` file
- Logged to Firestore: `type: "smart_recommender"`

---

## 🍃 Leaf Diagnostic — Full Workflow

### Step 1 — Image Upload (`/diagnostic`)
- User uploads leaf photo → `POST /api/diagnose`

### Step 2 — ML Pipeline (`ml_diagnostics.py`)
```
1. YOLO (~51MB)  → detect leaf regions → bounding boxes + confidence
2. ViT (~328MB)  → classify each region → disease name + confidence %
3. FILTER        → only return confidence > 0%
```

### Step 3 — Results (`/diagnostic/result`)
- Disease names + confidence bars
- Logged to Firestore: `type: "leaf_diagnosis"`

---

## 👤 User Profile & Admin

- **Profile** (`/profile`) — personal history from Firestore `userHistory/{uid}/actions/`
- **Admin** (`/admin`) — global metrics, `adminOnly` protected

---

## 🗄️ Data Layer

| Store | Location | Role |
|-------|----------|------|
| Qdrant | `185.215.167.14:6333` | Primary vector DB, semantic search |
| Local DB | `data/01_raw → 02_cleaned → 03_vectorized` | Backup, populated by data_collector |
| Firestore | Firebase cloud | User profiles + activity history |

---

## 🤖 LLM Architecture

| Tier | Model | Provider | Role |
|------|-------|----------|------|
| 1 | GPT-4o | OpenAI API | **Primary** |
| 2 | Qwen 2.5 7B (fine-tuned) | Self-hosted / API | **Fallback** |

- Auto-continuation loop if token limit hit mid-report
- All prompts + errors translated by `language_manager.py`

---

## 🔄 Data Collection Pipeline (`data_collector.py`)

```
Phase 1 — SCRAPING
  YouTube: transcripts from trusted gardening channels
  Reddit:  r/gardening, r/vegetablegardening, r/Hydroponics...
  Wikipedia: cultivation/farming sections
  Websites: gardeningknowhow.com, almanac.com, extension.org...

Phase 2 — CLEANING
  Dedup, filter low-quality, normalize text

Phase 3 — VECTORIZATION
  sentence-transformers (all-mpnet-base-v2)
  → Upload to Qdrant + save .npy to 03_vectorized_data/
```

---

## 📡 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/languages` | Available UI languages |
| GET | `/api/form-labels/{lang}` | Translated form labels |
| POST | `/api/translate-locations` | Translate location strings |
| POST | `/api/analyze` | Start analysis → session_id |
| GET | `/api/analyze-stream/{id}` | Stream AI report (SSE) |
| GET | `/api/download-report/{id}` | Download .md report |
| GET | `/api/results/{id}` | Session status |
| POST | `/api/diagnose` | Leaf disease diagnosis |

---
---

# 🎨 Prompt for AI Image Generator

> Paste into **Midjourney**, **DALL-E 3**, **Ideogram**, or **Adobe Firefly**:

---

Create a clean, modern **system architecture diagram** for a web application called "Plant Advisor". Use a **dark background** (deep green-black #0f1a0f) with **glowing neon green and teal** accents. Use a **vertical flowchart** layout with clearly labeled rounded boxes connected by labeled arrows.

**Layer 1 — Top:** A browser/person icon labeled "USER"

**Layer 2 — Frontend (green boxes, wide horizontal row):**
`Landing Page` | `Smart Recommender` | `Leaf Diagnostic` | `User Profile` | `Admin Dashboard` | `Login / Signup`

**Layer 3 — Firebase (purple boxes, side by side):**
`Firebase Auth` | `Firestore DB (user history)`

**Layer 4 — FastAPI Backend (large blue box), split into TWO pipelines:**

Left: **Smart Recommender Pipeline**
`Validate Plant Name (GPT-4o)` → `DB Lookup` → `[Qdrant PRIMARY | Local JSON BACKUP]` → `LLM: GPT-4o → Qwen2.5-7B FT (fallback)` → `Stream Report via SSE`

Right: **Leaf Diagnostic Pipeline**
`Upload Image` → `YOLO Model (51MB)` → `ViT Model (328MB)` → `Confidence Scores`

**Layer 5 — Data Layer (orange boxes):**
`Qdrant Vector DB (remote)` | `Local data/ (raw→cleaned→vectorized)` | `Firebase Firestore`

**Arrow labels:** REST/SSE · Auth Token · Firestore Read/Write · Semantic Search · Embeddings · LLM Fallback Chain · Image Upload

**Color legend (bottom corner):**
Green = Frontend · Blue = Backend · Purple = Firebase · Teal = AI/LLM · Orange = Database

Style: dark-mode tech infographic, flat design icons, no photos, readable labels, professional — suitable for a README or slide deck.

---

## 🚀 Deployment (Final Task)

The final task is integrating and deploying **both AI features inside the same unified web application**:

- **Smart Recommender** (LLM pipeline: GPT-4o + Qwen 2.5 7B fine-tuned fallback) and
- **Leaf Diagnostic** (Computer Vision pipeline: YOLO + ViT models)

are both served from the **same FastAPI backend** and accessible through the **same React frontend**, giving users a single, cohesive Plant Advisor experience.
