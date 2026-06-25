# 🚦 NUMIP — Nairobi Urban Mobility Intelligence Platform

> Real-time transit demand forecasting · Matatu route risk scoring ·
> Road safety blackspot detection · Social incident intelligence
> **Nairobi, Kenya**

[![CI](https://github.com/YOUR_USERNAME/numip/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/numip/actions)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)](https://streamlit.io)

---

## The Problem

Nairobi operates ~9,500 matatus across 135 gazetted routes carrying 4 million
daily passengers. Yet route utilisation is never measured at the route level,
road safety assessment is reactive and annual, and matatu fares fluctuate with
no predictive signal. **Kenya has the data. Nobody has built the pipeline.**

NUMIP merges NTSA accident records, OpenStreetMap road network data,
NASA weather, and social media into a single ML intelligence platform.

---

## Four ML Engines

| Engine | Model | Output |
|---|---|---|
| 🚦 **Demand Forecasting** | Prophet + XGBoost | Hourly passenger demand, 7-day forward |
| 🗺️ **Route Risk Scoring** | XGBoost + SHAP | Per-route safety score (1–5) + top drivers |
| 📍 **Blackspot Detection** | DBSCAN (haversine) | Accident cluster zones on Nairobi roads |
| 📣 **Social Intelligence** | VADER + TF-IDF/LSA | Incident detection from matatu tweets |

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/numip.git
cd numip

# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment config
cp .env.example .env

# 3. Generate data + seed DB
make seed

# 4. Train all ML models (generates 19 figures + saves models)
make train

# 5. Run the API
make api
# → http://localhost:8000/docs

# 6. Run the dashboard (separate terminal)
make dashboard
# → http://localhost:8501
```

Or with Docker:
```bash
make docker-up
# API   → http://localhost:8000/docs
# Dashboard → http://localhost:8501
```

---

## Project Structure

```
numip/
├── app/
│   ├── main.py                    # FastAPI app factory
│   ├── core/                      # Config, logging, JWT security
│   ├── db/                        # SQLAlchemy + DuckDB clients
│   ├── models/                    # ORM: User, Route, RiskScore, Forecast, Alert
│   ├── schemas/                   # Pydantic v2 request/response models
│   ├── services/                  # Business logic layer
│   ├── api/routers/               # 6 router modules, 24 endpoints
│   └── dashboard/
│       ├── streamlit_app.py       # Main entry point
│       ├── pages/                 # 5 Streamlit pages
│       └── components/            # Reusable charts + Folium maps
├── ml/
│   ├── features.py                # Shared feature engineering
│   ├── risk/classifier.py         # XGBoost + SHAP risk model
│   ├── demand/forecaster.py       # Prophet + XGBoost demand models
│   ├── blackspot/detector.py      # DBSCAN spatial clustering
│   ├── nlp/sentiment.py           # VADER + topic modelling
│   └── pipeline/run_pipeline.py   # Master orchestrator
├── data/processed/                # Generated CSV datasets (gitignored)
├── models/saved/                  # Trained model artifacts (gitignored)
├── figures/                       # 19 diagnostic figures (gitignored)
├── scripts/generate_data.py       # Synthetic data seeder
├── tests/                         # 20 pytest tests
├── Dockerfile + docker-compose    # Production containers
├── render.yaml                    # Render.com deployment manifest
└── .streamlit/config.toml         # Streamlit theme config
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register new account |
| POST | `/api/v1/auth/login` | Login, receive JWT tokens |
| GET  | `/api/v1/auth/me` | Current user profile |
| GET  | `/api/v1/routes/` | List all 20 matatu routes |
| GET  | `/api/v1/routes/{id}/risk` | Risk score + SHAP drivers |
| GET  | `/api/v1/routes/{id}/analytics` | Full route analytics |
| GET  | `/api/v1/routes/risk/summary` | Aggregate risk distribution |
| GET  | `/api/v1/demand/forecast/{id}` | 1–14 day hourly forecast |
| GET  | `/api/v1/demand/spikes` | Demand spike alerts |
| GET  | `/api/v1/demand/summary` | Hour × day demand matrix |
| GET  | `/api/v1/accidents/stats` | Aggregate accident statistics |
| GET  | `/api/v1/accidents/blackspots` | DBSCAN cluster GeoJSON |
| GET  | `/api/v1/accidents/heatmap-data` | Map heatmap coordinates |
| GET  | `/api/v1/social/incidents` | Recent incident tweets |
| GET  | `/api/v1/social/sentiment` | Sentiment summary + topics |
| GET  | `/api/v1/admin/users` | User management [admin] |
| GET  | `/api/v1/admin/system/stats` | Record counts [admin] |


---

## Deployment

### API → Render.com (Free tier)
```
1. Push repo to GitHub
2. New Web Service → connect repo
3. Runtime: Docker → Dockerfile
4. Environment: set SECRET_KEY to a random 32-char string
5. Deploy → API live at https://numip-api.onrender.com/docs
```


---

## Data Sources

| Dataset | Source | Records |
|---|---|---|
| Accident records | NTSA Kenya (synthetic) | 3,200 |
| Route profiles | Digital Matatus / OSM | 20 routes |
| Hourly demand | Census-weighted proxy | 262,800 |
| Social tweets | X / Twitter (synthetic) | 2,800 |
| Weather | NASA POWER API | 1,461 days |

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy · DuckDB · SQLite · Alembic · Pydantic v2 · JWT  
**ML:** XGBoost · Prophet · DBSCAN · SHAP · VADER · TF-IDF · LSA · K-Means  
**Dashboard:** Streamlit · Plotly · Folium · Seaborn  
**Infra:** Docker · GitHub Actions · Render.com · Streamlit Community Cloud

---

## Stakeholders

| Organisation | Use Case |
|---|---|
| NTSA Kenya | Real-time blackspot intelligence |
| Nairobi County | Route demand data for GTFS formalisation |
| Matatu SACCOs | Daily demand forecasts for vehicle dispatch |
| Insurance companies | Route risk scores for premium pricing |
| World Bank / USAID | Evidence base for infrastructure interventions |

---

*MIT License · Nairobi, Kenya · 2024*
