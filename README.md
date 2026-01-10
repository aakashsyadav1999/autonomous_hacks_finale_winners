# Smart Civic Complaint Management System - AI Backend

AI-powered backend for analyzing civic complaint images, verifying work completion, and generating predictive analytics reports.

## Tech Stack

- **FastAPI** - Web framework
- **Google Gemini 2.5 Flash** - AI/ML model
- **LangGraph** - Agent orchestration
- **Shapely** - Geospatial ward mapping
- **uv** - Package manager

## Setup

```bash
cd ai_backend

# Create .env file
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

# Install dependencies
uv sync

# Run server
uv run uvicorn main:app --reload --port 8080
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | - | Google AI API key |
| `MODEL_NAME` | No | `gemini-2.5-flash` | Gemini model name |
| `DEBUG` | No | `false` | Enable debug mode |

---

## API Endpoints

Base URL: `http://localhost:8080/api/v1`

---

### 1. Complaint Analysis

**Endpoint:** `POST /api/v1/analyze/complaint`

Analyzes a civic complaint image and returns detected issues with category, department, severity, tools, safety equipment, and ward mapping.

**Request:**
```json
{
  "image": "<base64_encoded_image>",
  "street": "MG Road",
  "area": "Nikol",
  "postal_code": "382350",
  "latitude": 23.0425,
  "longitude": 72.6346
}
```

**Response (Valid Issue):**
```json
{
  "is_valid": true,
  "data": [
    {
      "category": "Garbage/Waste accumulation",
      "department": "Sanitation Department",
      "severity": "Medium",
      "suggested_tools": ["Broom", "Garbage bags", "Shovel", "Wheelbarrow"],
      "safety_equipment": ["Heavy-duty gloves", "Face mask", "Safety boots"]
    }
  ],
  "ward_no": "24",
  "error": null
}
```

**Response (Invalid Image):**
```json
{
  "is_valid": false,
  "data": [],
  "ward_no": null,
  "error": "Image does not contain recognizable civic issues"
}
```

---

### 2. Work Verification

**Endpoint:** `POST /api/v1/verify/completion`

Compares before/after images to verify if contractor work has been completed.

**Request:**
```json
{
  "before_image": "<base64_encoded_original_complaint_image>",
  "after_image": "<base64_encoded_contractor_completion_image>",
  "category": "Garbage/Waste accumulation"
}
```

**Response (Completed):**
```json
{
  "is_completed": true,
  "error": null
}
```

**Response (Not Completed):**
```json
{
  "is_completed": false,
  "error": "Garbage is still visible in the after image"
}
```

---

### 3. Predictive Analysis

**Endpoint:** `POST /api/v1/analytics/predict`

Analyzes historical ticket data and generates an HTML predictive report for the next 30 days.

**Request:**
```json
{
  "tickets": [
    {
      "ticket_number": "TKT-001",
      "category": "Manholes/drainage opening damage",
      "severity": "High",
      "department": "Roads & Infrastructure",
      "ward_no": "24",
      "ward_name": "Nikol",
      "created_at": "2025-12-01T10:00:00",
      "resolved_at": "2025-12-05T14:00:00"
    }
  ]
}
```

**Response:**
```json
{
  "report_html": "<!DOCTYPE html><html>...predictive report...</html>",
  "generated_at": "2026-01-11T04:55:00",
  "error": null
}
```

---

### 4. Health Checks

**Endpoints:**
- `GET /api/v1/analyze/health`
- `GET /api/v1/verify/health`
- `GET /api/v1/analytics/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "complaint-analysis"
}
```

---

## Issue Categories

| Category | Department |
|----------|------------|
| Garbage/Waste accumulation | Sanitation Department |
| Manholes/drainage opening damage | Roads & Infrastructure |
| Water leakage | Water Supply Department |
| Drainage overflow | Drainage Department |

## Severity Levels

- **Low** - Minor issues, no immediate danger
- **Medium** - Moderate issues requiring attention
- **High** - Critical issues requiring urgent action

---

## cURL Examples

### Analyze Complaint
```bash
curl -X POST "http://localhost:8080/api/v1/analyze/complaint" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "<base64_image>",
    "street": "SG Road",
    "area": "Nikol",
    "postal_code": "382350",
    "latitude": 23.0425,
    "longitude": 72.6346
  }'
```

### Verify Work Completion
```bash
curl -X POST "http://localhost:8080/api/v1/verify/completion" \
  -H "Content-Type: application/json" \
  -d '{
    "before_image": "<base64_before>",
    "after_image": "<base64_after>",
    "category": "Garbage/Waste accumulation"
  }'
```

### Generate Predictive Report
```bash
curl -X POST "http://localhost:8080/api/v1/analytics/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "tickets": [
      {
        "ticket_number": "TKT-001",
        "category": "Drainage overflow",
        "severity": "High",
        "department": "Drainage Department",
        "ward_no": "21",
        "ward_name": "Dariapur",
        "created_at": "2025-12-01T10:00:00",
        "resolved_at": "2025-12-05T14:00:00"
      }
    ]
  }'
```

---

## API Documentation

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
