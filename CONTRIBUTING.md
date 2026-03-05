# Contributing to De-Identification App

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive in all interactions.

## Security First

This tool handles sensitive research data. When contributing:

- **NEVER** add code that transmits data over the network
- **NEVER** log, print, or write raw PII to stdout or files
- **NEVER** use external/cloud NLP APIs
- **ALWAYS** test with synthetic data only
- **ALWAYS** ensure audit logs contain no PII

## Getting Started

### Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/deidentify-app.git
cd deidentify-app

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
uv run python -m spacy download en_core_web_lg

# Run the app locally
uv run streamlit run app/main.py

# Run tests
uv run pytest tests/ -v
```

### Project Structure

```
app/
├── main.py              # Streamlit entry point
├── pipeline.py          # Core Presidio pipeline
├── recognizers/         # Custom PII recognizers
├── operators/           # Anonymization strategies
├── utils/               # File I/O, audit logging
└── ui/                  # Streamlit UI components
```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. **Never include actual PII** in bug reports

### Suggesting Features

1. Check existing feature requests
2. Use the feature request template
3. Explain the research use case

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add tests for new functionality
5. Run tests: `uv run pytest tests/ -v`
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

## Coding Standards

### Python Style

- Python 3.11+ with type hints on all function signatures
- Docstrings on all public functions (Google style)
- No print statements - use Python `logging` module
- Constants in UPPER_SNAKE_CASE

### Testing Requirements

- Every custom recognizer needs at least 3 positive and 2 negative test cases
- Pipeline tests must verify NO original PII appears in output
- Audit log tests must verify completeness and no PII leakage
- Use synthetic data in `data/sample/` for all tests

### Commit Messages

Use clear, descriptive commit messages:

```
Add custom recognizer for study IDs

- Support formats: STUDY-12345, BU-2024-78901
- Add positive and negative test cases
- Register with AnalyzerEngine
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update CHANGELOG.md if applicable
5. Request review from maintainers

## Adding Custom Recognizers

If you're adding a new PII pattern recognizer:

1. Add the recognizer class to `app/recognizers/custom.py`
2. Register it in `app/pipeline.py`
3. Add tests in `tests/test_recognizers.py`
4. Update the entity type table in `CLAUDE.md`

Example:

```python
class MyCustomRecognizer(PatternRecognizer):
    def __init__(self):
        patterns = [
            Pattern(
                name="my_pattern",
                regex=r"MY-\d{5}",
                score=0.8
            )
        ]
        super().__init__(
            supported_entity="MY_CUSTOM_ID",
            patterns=patterns
        )
```

## Questions?

Open an issue with the question label, or reach out to the maintainers.
