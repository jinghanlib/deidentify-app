# De-Identification App

A local-only tool for removing personally identifiable information (PII) from research data. Built for human subjects researchers who need HIPAA-compliant de-identification with full audit trails.

**All processing happens on your computer. Your data never leaves your machine.**

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)

---

## Features

- **HIPAA Safe Harbor Compliant** - Detects all 18 identifier types
- **Multiple Anonymization Strategies** - Redact, mask, hash, or replace with fake data
- **Audit Logs for IRB** - Document every detection and action taken
- **Offline Processing** - Docker runs with `--network none` for maximum security
- **User-Friendly UI** - Streamlit interface designed for non-technical researchers
- **Supports CSV, Excel, and Text** - Common research data formats

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac, Windows, or Linux)

### Run the App

**Mac/Linux:**
```bash
git clone https://github.com/jinghanlib/deidentify-app.git
cd deidentify-app
./run.sh
```

**Windows:**
```batch
git clone https://github.com/jinghanlib/deidentify-app.git
cd deidentify-app
run.bat
```

The launcher will:
1. Check that Docker is installed and running
2. Build the image (first time only, ~5-10 minutes)
3. Start the container with network isolation
4. Open your browser to http://localhost:8501

### Alternative: Using uv (for developers)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd deidentify-app
uv sync
uv run python -m spacy download en_core_web_lg

# Run the app
uv run streamlit run app/main.py
```

---

## How It Works

### 1. Upload Your Data

Upload CSV, Excel, or text files. The app previews the first 5 rows.

### 2. Configure Columns

Tell the app how to process each column:

| Type | Description | Example |
|------|-------------|---------|
| **Skip** | Don't process | `record_id`, `date_collected` |
| **Structured** | Regex patterns only | Email or phone columns |
| **Free Text** | Full NER + regex | Notes, comments, descriptions |
| **Direct Identifier** | Always fully redact | SSN, MRN columns |

### 3. Select Entity Types

Choose which PII types to detect:
- Names, Locations, Dates
- Phone numbers, Email addresses
- SSN, Medical record numbers
- And more (18 HIPAA identifier types)

### 4. Choose Anonymization Strategy

| Strategy | Example | Use Case |
|----------|---------|----------|
| **Redact** | `[REDACTED]` | Maximum privacy |
| **Type Tag** | `[PERSON_1]` | Preserve entity counts for analysis |
| **Mask** | `J*** S****` | Keep partial structure |
| **Hash** | `a1b2c3d4` | Link records across files |
| **Fake** | `Jane Doe` | Preserve readability |

### 5. Export

Download:
- **De-identified file** (same format as input)
- **Audit log** (JSON, required for IRB documentation)

---

## File Locations

| Purpose | Location |
|---------|----------|
| Input data | `data/` |
| De-identified output | `output/` |
| Audit logs | `audit/` |
| Sample data | `data/sample/` |

---

## Security

This tool is designed with research data security in mind:

- **Network Isolation**: Docker container runs with `--network none`
- **No Cloud APIs**: All NLP processing uses local SpaCy models
- **No Telemetry**: Streamlit telemetry is disabled
- **Non-Root User**: Container runs as unprivileged user
- **Read-Only Input**: Input data directory is mounted read-only
- **Audit Trail**: Every detection and action is logged (without PII)

---

## For IRB Documentation

The audit log provides everything needed for IRB compliance:

```json
{
  "run_id": "uuid",
  "timestamp": "2024-01-15T10:30:00Z",
  "settings": {
    "entities_selected": ["PERSON", "EMAIL_ADDRESS"],
    "confidence_threshold": 0.7,
    "strategy_per_entity": {"PERSON": "hash"}
  },
  "summary": {
    "total_records": 100,
    "total_detections": 342
  }
}
```

The audit log **never contains the original PII** - only entity type, position, confidence, and action taken.

See `docs/irb_methodology.md` for a template you can include in your IRB application.

---

## Configuration

### Confidence Threshold

Adjust detection sensitivity:

| Level | Threshold | Description |
|-------|-----------|-------------|
| Aggressive | 0.3-0.5 | More detections, some false positives |
| Moderate | 0.7 | Balanced (default) |
| Conservative | 0.8-1.0 | Fewer false positives, may miss some |

**For IRB**: We recommend 0.5 with manual review of flagged items.

---

## Tech Stack

- **[Microsoft Presidio](https://microsoft.github.io/presidio/)** - PII detection and anonymization
- **[SpaCy](https://spacy.io/)** (`en_core_web_lg`) - Named entity recognition
- **[Streamlit](https://streamlit.io/)** - Web interface
- **[Docker](https://www.docker.com/)** - Containerization and isolation

---

## Development

### Running Tests

```bash
uv run pytest tests/ -v
```

### Project Structure

```
deidentify-app/
├── app/
│   ├── main.py              # Streamlit entry point
│   ├── pipeline.py          # Core Presidio pipeline
│   ├── recognizers/         # Custom PII recognizers
│   ├── operators/           # Anonymization strategies
│   ├── utils/               # File I/O, audit logging
│   └── ui/                  # Streamlit UI components
├── data/sample/             # Synthetic test data
├── tests/                   # Unit tests
└── docs/                    # Documentation
```

### Adding Custom Recognizers

See `app/recognizers/custom.py` for examples of custom PII patterns (MRNs, study IDs, etc.).

---

## Troubleshooting

See [docs/QUICKSTART.md](docs/QUICKSTART.md#troubleshooting) for common issues and solutions.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Microsoft Presidio](https://github.com/microsoft/presidio) for the PII detection engine
- [SpaCy](https://spacy.io/) for NER models
- [Streamlit](https://streamlit.io/) for the UI framework
