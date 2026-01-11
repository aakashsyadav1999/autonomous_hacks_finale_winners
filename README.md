# Smart Civic Complaint Management System

A comprehensive platform for citizens to report civic issues in Ahmedabad, Gujarat, India. Features AI-powered complaint analysis, automatic categorization, work verification, and predictive analytics.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Smart Civic Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐          ┌──────────────────┐             │
│  │   Django Backend │◄────────►│    AI Backend    │             │
│  │   (Port 8000)    │   REST   │   (Port 8080)    │             │
│  │                  │   API    │                  │             │
│  │  • User Portal   │          │  • Image Analysis│             │
│  │  • Admin Portal  │          │  • Work Verify   │             │
│  │  • Ticket Mgmt   │          │  • Predictions   │             │
│  │  • Contractor    │          │  • Ward Mapping  │             │
│  └──────────────────┘          └──────────────────┘             │
│           │                            │                         │
│           ▼                            ▼                         │
│    ┌────────────┐              ┌──────────────┐                 │
│    │  SQLite DB │              │ Google Gemini│                 │
│    └────────────┘              │  2.5 Flash   │                 │
│                                └──────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🌟 Features

### User Portal (Django)
- 📸 Photo capture with GPS location
- 🗺️ Automatic reverse geocoding
- 🎫 Ticket tracking (CMP-YYYYMMDD-NNN format)
- ⭐ Work rating system (1-5 stars)

### Admin Portal (Django)
- 👥 Ward management
- 🔧 Contractor management
- 📋 Ticket assignment & status updates

### AI Features (FastAPI)
- 🔍 **Image Analysis**: Detect civic issues, categorize, assess severity
- 🛠️ **Tool Suggestions**: Recommended tools & safety equipment
- 📍 **Ward Mapping**: GeoJSON-based location to ward mapping
- ✅ **Work Verification**: Before/after image comparison
- 📊 **Predictive Analytics**: 30-day risk prediction reports

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Git
- Google AI API Key

### 1. Clone & Setup

```bash
git clone <repository-url>
cd autonomous_hacks_finale_winners
```

### 2. Start Django Backend (Port 8000)

```bash
cd django_backend
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver 0.0.0.0:8000
```

### 3. Start AI Backend (Port 8080)

```bash
cd ai_backend
cp .env.example .env
# Add GOOGLE_API_KEY to .env

uv sync
uv run uvicorn main:app --reload --port 8080
```

---

## 📡 API Endpoints

### Django Backend (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/capture/` | GET | Photo capture page |
| `/track/` | GET | Ticket tracking page |
| `/admin/` | GET | Django admin |
| `/api/user/capture-photo/` | POST | Submit photo with location |
| `/api/user/submit-complaint/` | POST | Submit complaint for AI analysis |
| `/api/user/track-ticket/` | GET | Track ticket by number |
| `/api/user/rate-ticket/` | POST | Rate resolved ticket |

### AI Backend (Port 8080)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze/complaint` | POST | Analyze complaint image |
| `/api/v1/verify/completion` | POST | Verify work completion |
| `/api/v1/analytics/predict` | POST | Generate predictive report |
| `/docs` | GET | Swagger API documentation |

---

## 🗂️ Project Structure

```
autonomous_hacks_finale_winners/
├── django_backend/           # Django web application
│   ├── civic_complaint_system/  # Project settings
│   ├── user_portal/             # Citizen-facing app
│   ├── admin_portal/            # Admin management
│   └── requirements.txt
│
├── ai_backend/               # FastAPI AI services
│   ├── app/
│   │   ├── agents/              # AI agents (vision, verification, predictive)
│   │   ├── api/routes/          # API endpoints
│   │   ├── api/schemas/         # Pydantic models
│   │   ├── services/            # Ward mapping service
│   │   └── data/                # GeoJSON ward boundaries
│   ├── main.py
│   └── pyproject.toml
│
└── README.md                 # This file
```

---

## 📋 Issue Categories

| Category | Department | Severity Levels |
|----------|------------|-----------------|
| Garbage/Waste accumulation | Sanitation Department | Low, Medium, High |
| Manholes/drainage damage | Roads & Infrastructure | Low, Medium, High |
| Water leakage | Water Supply Department | Low, Medium, High |
| Drainage overflow | Drainage Department | Low, Medium, High |

---

## 🔄 Ticket Lifecycle

```
SUBMITTED → ASSIGNED → IN_PROGRESS → RESOLVED
    │           │            │           │
    └── AI      └── Admin    └── Work    └── User
       analyzes    assigns      starts      rates
```

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Web Backend | Django 5.0, Django REST Framework |
| AI Backend | FastAPI, LangGraph, Google Gemini 2.5 Flash |
| Database | SQLite3 (Django) |
| Geospatial | Shapely, geopy, Nominatim |
| Frontend | Bootstrap 5, Vanilla JavaScript |
| Package Manager | pip (Django), uv (AI) |

---

## 📚 Documentation

- **Django Backend**: See [django_backend/README.md](django_backend/README.md)
- **AI Backend**: See [ai_backend/README.md](ai_backend/README.md)
- **AI Swagger UI**: http://localhost:8080/docs

---

## 👥 Contributors

- **Development**: Smart Civic Team

---

**Made with ❤️ for a Better Ahmedabad**
