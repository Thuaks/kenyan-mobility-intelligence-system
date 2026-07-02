
## 🚦 What is this thing?

Nairobi has **9,500+ matatus**, **135 gazetted routes**, and roughly **4 million daily commuters** — and almost no public data infrastructure telling anyone which routes are dangerous, when demand will spike, or where accidents cluster.

**NUMIP fixes that.** It's a full machine learning platform that scores every matatu route by risk, forecasts hourly passenger demand, clusters accident blackspots with DBSCAN, reads the actual sentiment of Nairobi's Twitter complaints about traffic, and — because Africa's Talking accounts cost money — sends gloriously fake SMS alerts to SACCO operators in sandbox mode.

It is, unapologetically, four ML models wearing a FastAPI trench coat with a Streamlit dashboard on top.

---

## 🧠 The Brains

| Engine | Model | What it actually does |
|---|---|---|
| 🚦 **Route Risk Scoring** | XGBoost + SHAP | Scores all 20 routes 1–5, then explains *why* with real feature attribution |
| 📈 **Demand Forecasting** | XGBoost (Prophet, RIP) | Predicts hourly passenger volume 7 days out |
| 📍 **Blackspot Detection** | DBSCAN (haversine) | Clusters 3,200+ accident records into actual danger zones on a real map |
| 📣 **Social Intelligence** | VADER + Sheng-aware sentiment | Reads Nairobi's traffic complaints in English *and* Sheng |
| 📲 **SMS Alert Pipeline** | Mock Africa's Talking | Sends believable fake SMS with real message IDs, zero real money spent |

---

## 🛠️ Built With (and Fought With)

<div align="center">

![Python](https://img.shields.io/badge/Python-2ECC71?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-E74C3C?style=for-the-badge&logoColor=white)
![SHAP](https://img.shields.io/badge/SHAP-9B59B6?style=for-the-badge&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-3498DB?style=for-the-badge&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFC300?style=for-the-badge&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)
![Git](https://img.shields.io/badge/Git-E74C3C?style=for-the-badge&logo=git&logoColor=white)

</div>

---

## ⚡ The Five Pages

| Page | What you'll see |
|---|---|
| 🏠 **Home & KPIs** | 8 headline metrics, risk distribution donut, accident trends, the findings nobody asked for but everyone needs |
| 🗺️ **Route Risk Map** | Live Folium map, SHAP-explained risk drivers, an actual working SMS alert button |
| 📈 **Demand Forecast** | 7-day hourly passenger predictions, demand heatmaps, spike alerts |
| 📍 **Blackspot Intelligence** | DBSCAN clusters plotted on real Nairobi coordinates, cause-of-accident breakdowns |
| 📣 **Social Feed** | Live-feeling sentiment cards, topic clustering, keyword clouds from synthetic-but-believable tweets |

---

## 🔥 Honest War Stories From Building This

> *Because every README pretends everything went smoothly. This one doesn't.*

- **The bcrypt incident:** `passlib` quietly checking `bcrypt.__about__.__version__` — an attribute that stopped existing in bcrypt 4.1 — broke login in production for an embarrassingly long time. Fixed by bypassing passlib entirely and calling bcrypt directly like adults.
- **The 502 that wasn't:** Railway injects its own `$PORT` at runtime. Hardcoding `--port 8000` works perfectly... until it doesn't, ever, on Railway specifically.
- **The Streamlit Cloud Python 3.14 mystery:** `runtime.txt` doesn't work on Streamlit Cloud. `.python-version` does. Nobody tells you this until `scikit-learn` refuses to build against a release candidate of numpy that doesn't even officially exist yet.
- **The thread-storm that looked like a hang:** A 4-fold cross-validation on 20 rows of data should take milliseconds. On a CPU-throttled free-tier container with no `n_jobs=1` set, it took *forever*, looked exactly like a frozen process, and survived three separate debugging sessions before we found it.
- **The `nump` → `numip` rename that ate `numpy`:** A find-and-replace renamed every `import numpy as np` into `import numipy as np`. Six files. One very confused `ModuleNotFoundError`. Lesson learned: substring renames and Python package names do not mix.

---

## 🚀 Quick Start

```bash
git clone https://github.com/Thuaks/kenyan-mobility-intelligence-system.git
cd kenyan-mobility-intelligence-system

pip install -r requirements.txt
cp .env.example .env

make seed      # generates synthetic Nairobi data
make train     # trains all 4 ML models
make api       # → http://localhost:8000/docs
make dashboard # → http://localhost:8501
```

Or skip all that and just run it in Docker:

```bash
docker compose up --build
```

---

## 🌍 Who Would Actually Use This

| Who | Why |
|---|---|
| **NTSA Kenya** | Real-time blackspot intelligence instead of waiting for the annual report |
| **Nairobi County** | Route-level demand data to actually plan GTFS formalisation |
| **Matatu SACCOs** | Daily demand forecasts so they stop guessing how many vehicles to deploy |
| **Insurance companies** | Route risk scores that aren't vibes-based |
| **You, the recruiter reading this** | Proof that I can ship ML, build the API around it, deploy it twice (badly, then well), and write honest documentation about the process |

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,17,24&height=100&section=footer" width="100%"/>

*Built by Alex Thuku · MIT License · Nairobi, Kenya*

</div>
