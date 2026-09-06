# SIH26122 — Intelligent Data Capture & Schedule-Linking Layer

## Overview

A system that ingests messy infrastructure field progress reports, extracts
structured execution claims, matches them to the correct activities in a
project baseline schedule, performs validation and conflict checks, and
requires human planner approval before anything becomes final.

## Tech Stack

### Backend
- Python
- FastAPI
- Pydantic v2
- SQLite

### Frontend
- React
- TypeScript
- Vite
- TanStack Query

### AI / Matching
- OpenAI-compatible LLM API
- sentence-transformers
- FAISS
- RapidFuzz

## Project Structure

backend/
  routers/
  models/
  shared/

frontend/
  src/
  sample_data/

## Development

Never commit `.env` or API keys.

Create a local `.env` file from the provided environment template before
running components that require external credentials.

## Git Workflow

- `main` is protected from direct development.
- Each member works on their assigned feature branch.
- Changes are merged through Pull Requests.
- At least one other team member reviews a PR before merge.
