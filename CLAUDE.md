# CLAUDE.md — INVEST Orientation Intake System

## Project Overview
A Streamlit-based digital intake system for the INVEST workforce development program at an America's Job Center of California (AJCC). Replaces paper-based orientation with digital forms, AI-powered document verification, and automated packaging/delivery.

## Tech Stack
- **Framework:** Streamlit (NOT FastAPI — this is a Streamlit app)
- **Language:** Python
- **AI Integration:** Claude Vision API (document verification)
- **PDF Generation:** ReportLab
- **QR Codes:** qrcode library
- **Data:** Local JSON (zero-persistence — data is packaged and emailed, not stored)
- **Platform:** Windows (primary development)

## Architecture

### Core Principle: Zero-Persistence Compliance
No participant data is stored on the server after session completion. Forms are completed in-browser, packaged into a zip file, and emailed to a designated address. This is a compliance requirement, not a preference.

### File Roles
| File | Responsibility |
|------|---------------|
| `app.py` (~1,310 lines) | Page routing, UI rendering, Streamlit page logic |
| `forms.py` | Form definitions, PDF generation (standalone, no app.py imports) |
| `sheets.py` | Google Sheets integration (currently disabled, kept for future use) |
| `config.py` | All configuration values — paths, URLs, document groups, settings |
| `app/styling.py` | CSS styling via `get_app_css()` |
| `app/services/image_processor.py` | `check_image_quality()`, `enhance_image()` |
| `app/services/data_manager.py` | CRUD operations for participant data during session |
| `app/services/document_verifier.py` | AI-powered document verification via Claude Vision API |
| `app/services/qr_generator.py` | QR code creation for participant tracking |

### Key Design Decisions
1. **Streamlit, not FastAPI** — entire UI generated from Python, no separate HTML/JS
2. **Modular services** — each service file has one job (single responsibility)
3. **Configuration centralized** in `config.py` — no hardcoded values in service files
4. **forms.py is standalone** — it doesn't import from app.py, keeps clean boundaries
5. **Zero data at rest** — zip + email delivery, no database persistence

## Coding Conventions
- Python, PEP 8 style
- Descriptive function names (e.g., `check_image_quality` not `chk_img`)
- Docstrings on all public functions
- Error handling with try/except, meaningful error messages
- Configuration values always imported from config.py

## Environment
- `.env` contains API keys (never committed)
- `.env.example` shows required variables without real values
- `.streamlit/` contains Streamlit-specific config

## What NOT to Do
- Don't add data persistence/storage — this is zero-persistence by design
- Don't hardcode configuration values — always use config.py
- Don't put business logic in app.py — extract to services/
- Don't modify forms.py to depend on app.py — keep it standalone
- Don't commit .env or any file containing API keys
