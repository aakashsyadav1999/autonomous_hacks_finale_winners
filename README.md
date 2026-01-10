# Smart Civic Complaint Management System - AI Backend

AI-powered image analysis backend for civic complaint categorization and routing.

## Features

- **Image Analysis**: Analyzes civic issue images using Google Gemini 2.5 Flash
- **Multi-Issue Detection**: Detects multiple civic issues in a single image
- **Automatic Categorization**: Classifies issues into 4 categories
- **Department Routing**: Maps issues to appropriate municipal departments
- **Severity Assessment**: Assigns Low/Medium/High severity levels

## Categories & Departments

| Category | Department |
|----------|------------|
| Garbage/Waste accumulation | Sanitation Department |
| Manholes/drainage opening damage | Roads & Infrastructure |
| Water leakage | Water Supply Department |
| Drainage overflow | Drainage Department |

## Setup

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Google API Key for Gemini

### Installation

```bash
# Install dependencies
uv sync

# Copy environment file and add your API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Running the Server

```bash
# Run the FastAPI server
uv run uvicorn main:app --reload --port 8000
```

## API Endpoints

### Analyze Complaint

**POST** `/api/v1/analyze/complaint`

Analyze a civic complaint image.

**Request Body:**
```json
{
  "image": "<base64_encoded_image>",
  "street": "Main Street",
  "area": "Downtown",
  "postal_code": "12345",
  "latitude": 12.9716,
  "longitude": 77.5946
}
```

**Response:**
```json
{
  "is_valid": true,
  "data": [
    {
      "category": "Garbage/Waste accumulation",
      "department": "Sanitation Department",
      "severity": "High"
    }
  ],
  "error": null
}
```

## Testing with cURL

See the `test_curl.sh` file for sample cURL commands.
