# Civic Complaint AI Backend

AI-powered image analysis for civic complaint categorization and routing.

## Overview

This backend service provides intelligent image analysis capabilities for civic complaint management systems. It uses advanced AI agents to analyze images, categorize complaints, and route them to appropriate departments.

## Features

- Vision-based image analysis using Google Gemini
- Automated complaint categorization
- Department routing based on complaint type
- FastAPI-based REST API
- LangGraph workflow orchestration

## Installation

```bash
uv sync
```

## Running the Application

```bash
uvicorn main:app --reload
```

## API Endpoints

- `POST /api/complaints/analyze` - Analyze complaint images and categorize

## Development

Install development dependencies:

```bash
uv sync --dev
```

Run tests:

```bash
pytest
```

## Technology Stack

- FastAPI
- LangGraph
- LangChain
- Google Gemini AI
- Pydantic
