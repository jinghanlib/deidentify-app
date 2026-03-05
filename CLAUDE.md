# De-Identification Pipeline — CLAUDE.md

## Project Overview
A local-only, Docker-containerized application for de-identifying human subjects research data using Microsoft Presidio. Built with a Streamlit UI for non-technical researchers. All processing happens locally — no data ever leaves the machine.

## Critical Constraints (READ FIRST)
- **NEVER** use external/cloud NLP APIs (no OpenAI, no Google NLP, no AWS Comprehend)
- **NEVER** log, print, or write raw PII to stdout, debug logs, or temp files
- **NEVER** transmit data over the network — this app runs fully offline once built
- **ALL** NER models must run locally (SpaCy `en_core_web_lg`)
- **TEST ONLY** with synthetic data in `data/sample/` — never commit real participant data
- Real data is mounted at runtime via Docker volume and never persists in the image

## IRB & Ethics Context
This tool processes data collected under IRB-approved human subjects research protocols.
De-identification must follow HIPAA Safe Harbor guidelines (18 identifier types).
The tool must produce an **audit log** documenting what was detected, what action was taken,
and what confidence threshold was used — this is required for IRB compliance documentation.

## Architecture

```
deidentify-app/
├── CLAUDE.md                  # This file — project context for Claude Code
├── Dockerfile                 # Production container (multi-stage, --network none at runtime)
├── docker-compose.yml         # Easy launch with volume mounts
├── requirements.txt           # Pinned Python dependencies
├── pyproject.toml             # Project metadata
│
├── app/
│   ├── __init__.py
│   ├── main.py                # Streamlit entry point
│   ├── pipeline.py            # Core Presidio pipeline orchestration
│   ├── recognizers/
│   │   ├── __init__.py
│   │   └── custom.py          # Custom recognizers (study IDs, MRNs, etc.)
│   ├── operators/
│   │   ├── __init__.py
│   │   └── strategies.py      # Anonymization strategies (redact, hash, pseudonym, mask)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── io.py              # File I/O (CSV, Excel, text)
│   │   ├── audit.py           # Audit log generation for IRB compliance
│   │   └── column_detector.py # Auto-detect column types (structured vs free text)
│   └── ui/
│       ├── __init__.py
│       ├── sidebar.py         # Entity type selection, threshold controls
│       ├── preview.py         # Before/after preview with highlighting
│       └── export.py          # Download de-identified file + audit log
│
├── data/
│   ├── sample/
│   │   └── sample_dataset.csv # Synthetic demo data (safe to commit)
│   └── .gitkeep               # Real data is NEVER committed
│
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py       # Unit tests for core pipeline
│   ├── test_recognizers.py    # Tests for custom recognizers
│   └── test_audit.py          # Verify audit log completeness
│
└── docs/
    ├── irb_methodology.md     # De-identification methodology for IRB appendix
    └── user_guide.md          # How to use the app (for researchers)
```

## Tech Stack
- **Python 3.11** — base language
- **Microsoft Presidio** (`presidio-analyzer`, `presidio-anonymizer`) — PII detection & anonymization
- **SpaCy** (`en_core_web_lg`) — NER backend for Presidio
- **Streamlit** — web UI (runs locally on port 8501)
- **pandas** — data handling
- **openpyxl** — Excel file support
- **Docker** — containerized deployment, runs with `--network none`

## Presidio Entity Types to Support
### HIPAA Safe Harbor (18 identifiers) — Map to Presidio entities:
| HIPAA Identifier | Presidio Entity | Detection Method |
|---|---|---|
| Names | PERSON | SpaCy NER |
| Geographic (< state) | LOCATION, GPE | SpaCy NER + regex |
| Dates (except year) | DATE_TIME | Presidio built-in |
| Phone numbers | PHONE_NUMBER | Presidio built-in |
| Fax numbers | PHONE_NUMBER | Presidio built-in |
| Email addresses | EMAIL_ADDRESS | Presidio built-in |
| SSN | US_SSN | Presidio built-in |
| Medical record numbers | MEDICAL_RECORD | Custom recognizer |
| Health plan beneficiary | INSURANCE_ID | Custom recognizer |
| Account numbers | FINANCIAL | Custom recognizer |
| License/cert numbers | US_DRIVER_LICENSE | Presidio built-in |
| Vehicle IDs | VEHICLE_ID | Custom recognizer |
| Device IDs | DEVICE_ID | Custom recognizer |
| URLs | URL | Presidio built-in |
| IP addresses | IP_ADDRESS | Presidio built-in |
| Biometric IDs | BIOMETRIC_ID | Custom recognizer |
| Photos/images | N/A | Out of scope (text only) |
| Other unique identifiers | CUSTOM_ID | Custom recognizer (study-specific) |

## Anonymization Strategies (User-Selectable Per Entity Type)
- **Redact**: Replace with `[REDACTED]` — simplest, most conservative
- **Replace with type tag**: Replace with `[PERSON_1]`, `[LOCATION_2]` — preserves entity counts
- **Mask**: Partial masking, e.g., `S***h J*****n`, `***-**-6789` — retains partial structure
- **Hash (SHA-256)**: Deterministic pseudonym, same input → same hash — preserves linkage across records
- **Fake replacement**: Replace with realistic fake data via Faker — preserves readability

## Confidence Threshold
- Presidio returns confidence scores (0.0–1.0) for each detection
- Default threshold: **0.7** (moderate — catches most PII with acceptable false positives)
- User can adjust via slider in the UI
- Lower (0.3–0.5): aggressive — more false positives, fewer missed PII
- Higher (0.8–1.0): conservative — fewer false positives, may miss some PII
- **For IRB purposes**: recommend 0.5 with manual review of flagged items

## Audit Log Requirements
Each de-identification run must produce a JSON audit log containing:
```json
{
  "run_id": "uuid",
  "timestamp": "ISO-8601",
  "input_file": "filename (no path)",
  "settings": {
    "entities_selected": ["PERSON", "EMAIL_ADDRESS", ...],
    "confidence_threshold": 0.7,
    "strategy_per_entity": {"PERSON": "hash", "EMAIL_ADDRESS": "redact", ...}
  },
  "summary": {
    "total_records": 100,
    "total_detections": 342,
    "detections_by_entity": {"PERSON": 89, "EMAIL_ADDRESS": 45, ...},
    "records_with_no_detections": 3
  },
  "details": [
    {
      "record_id": 1,
      "field": "medical_notes",
      "entity_type": "PERSON",
      "original_length": 15,
      "confidence": 0.92,
      "action": "hash",
      "position": {"start": 8, "end": 22}
    }
  ]
}
```
**IMPORTANT**: The audit log must NEVER contain the original PII text — only entity type, position, length, confidence, and action taken.

## UI Requirements (Streamlit)
1. **File Upload**: CSV, XLSX, or TXT. Show preview of first 5 rows.
2. **Column Selection**: Auto-detect column types. Let user mark columns as:
   - `skip` (don't process, e.g., record_id)
   - `structured` (apply regex-only, e.g., email column)
   - `free_text` (apply full NER + regex, e.g., medical_notes)
   - `direct_identifier` (always fully redact, e.g., SSN column)
3. **Entity Type Selector**: Checkboxes for each entity type. Select/deselect all.
4. **Confidence Threshold**: Slider 0.0–1.0 with presets (Aggressive/Moderate/Conservative).
5. **Strategy Selector**: Per-entity-type dropdown for anonymization strategy.
6. **Preview**: Side-by-side before/after with color-coded highlights per entity type.
7. **Export**: Download de-identified file (same format as input) + audit log JSON.

## Development Workflow
1. Work in `deidentify-app/` directory
2. Use virtual environment: `python -m venv .venv && source .venv/bin/activate`
3. Install deps: `pip install -r requirements.txt && python -m spacy download en_core_web_lg`
4. Run locally: `streamlit run app/main.py`
5. Run tests: `pytest tests/ -v`
6. Build Docker: `docker build -t deidentify-app .`
7. Run Docker: `docker run --network none -p 8501:8501 -v ./data:/workspace/data deidentify-app`

## Code Style
- Python 3.11+ with type hints on all function signatures
- Docstrings on all public functions (Google style)
- No print statements — use Python `logging` module
- Constants in UPPER_SNAKE_CASE
- Streamlit state management via `st.session_state`

## Testing Requirements
- Every custom recognizer must have at least 3 positive and 2 negative test cases
- Pipeline tests must verify that NO original PII appears in output
- Audit log tests must verify completeness and that no PII leaks into the log
- Use the synthetic `data/sample/sample_dataset.csv` for all tests

## When Uncertain
- Over-redact rather than under-redact — false positives are safer than missed PII
- If a column type is ambiguous, default to `free_text` (most thorough processing)
- If a detection's confidence is borderline, include it and let the user decide in review
