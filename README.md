# 🚦 NUMIP — Nairobi Urban Mobility Intelligence Platform


An AI-powered urban mobility analytics platform designed to improve decision-making across Kenya's public transport sector.

The system combines machine learning, geospatial analytics, traffic safety intelligence, and social data monitoring to provide actionable insights for transport operators, planners, researchers, and policymakers.

---


## The Problem

Nairobi operates ~9,500 matatus across 135 gazetted routes carrying 4 million
daily passengers. Yet route utilisation is never measured at the route level,
road safety assessment is reactive and annual, and matatu fares fluctuate with
no predictive signal. **Kenya has the data. Nobody has built the pipeline.**

NUMIP merges NTSA accident records, OpenStreetMap road network data,
NASA weather, and social media into a single ML intelligence platform.

---


## Key Features

### 📈 Demand Forecasting
Predict passenger demand across transport routes using machine learning models.

**Capabilities**
- Hourly demand prediction
- Trend analysis
- Peak traffic identification
- Future demand forecasting

### 🛣 Route Risk Assessment
Analyze and rank transport routes according to safety indicators.

**Capabilities**
- Route risk scoring
- Safety factor analysis
- Risk trend monitoring
- Explainable ML predictions using SHAP

### 📍 Accident Blackspot Detection
Identify high-risk road segments using geospatial clustering algorithms.

**Capabilities**
- Accident hotspot mapping
- Spatial cluster detection
- Risk visualization
- Road safety intelligence

### 📣 Social Intelligence Monitoring
Monitor public sentiment and transport-related incidents from social platforms.

**Capabilities**
- Sentiment analysis
- Incident detection
- Topic extraction
- Public perception tracking

### 📊 Interactive Analytics Dashboard
Explore insights through an intuitive web-based dashboard.

**Capabilities**
- Real-time visualizations
- Interactive maps
- Performance metrics
- Route intelligence reporting

---

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- JWT Authentication
- REST APIs

### Data Science & Machine Learning
- Scikit-Learn
- XGBoost
- Prophet
- SHAP
- Pandas
- NumPy
- StatsModels

### NLP
- VADER Sentiment Analysis
- TF-IDF
- Topic Modelling

### Geospatial Analytics
- DBSCAN Clustering
- Folium
- OpenStreetMap

### Dashboard & Visualization
- Streamlit
- Plotly
- Matplotlib

### Database
- DuckDB
- SQLAlchemy ORM

### DevOps
- Docker
- GitHub Actions
- CI/CD Pipelines

---

## System Architecture

```text
Data Sources
│
├── Accident Records
├── Weather Data
├── Route Information
├── Social Media Data
│
▼
Data Processing Layer
│
├── Cleaning
├── Feature Engineering
├── Transformation
│
▼
Machine Learning Layer
│
├── Demand Forecasting
├── Risk Scoring
├── Blackspot Detection
├── Social Intelligence
│
▼
API Layer (FastAPI)
│
▼
Dashboard Layer (Streamlit)
```

---

## Project Structure

```text
app/
├── api/
├── services/
├── models/
├── schemas/
├── dashboard/

ml/
├── demand/
├── risk/
├── blackspot/
├── nlp/

data/
models/
tests/
scripts/
```

---

## Machine Learning Models

| Component | Technique |
|------------|------------|
| Demand Forecasting | Prophet + XGBoost |
| Route Risk Scoring | XGBoost + SHAP |
| Blackspot Detection | DBSCAN |
| Social Intelligence | VADER + TF-IDF |

---

## Skills Demonstrated

This project showcases:

- Full-Stack Development
- Data Science
- Machine Learning
- Predictive Analytics
- Geospatial Analysis
- Natural Language Processing
- REST API Development
- Database Design
- Data Engineering
- Dashboard Development
- Docker Containerization
- CI/CD Automation

---


## Author

### Alex Thuku

Data Scientist | Web Developer


---

