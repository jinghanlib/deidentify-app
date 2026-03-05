# De-Identification Methodology for IRB Documentation

This document describes the de-identification methodology used by the De-Identification App. You may include this (or a modified version) in your IRB application's data handling section.

---

## Overview

The De-Identification App removes personally identifiable information (PII) from research data using automated natural language processing (NLP) and pattern matching. The tool follows **HIPAA Safe Harbor** guidelines, which specify 18 categories of identifiers that must be removed for data to be considered de-identified.

## Processing Environment

- **Local Processing Only**: All data processing occurs on the researcher's local machine
- **Network Isolation**: The application runs in a Docker container with network access disabled (`--network none`)
- **No Cloud Services**: No data is transmitted to external APIs or cloud services
- **No Data Persistence**: Input data is mounted read-only and is not copied into the application

## HIPAA Safe Harbor Identifiers

The tool detects and anonymizes the following identifier categories:

| # | HIPAA Identifier | Detection Method |
|---|------------------|------------------|
| 1 | Names | Named Entity Recognition (SpaCy NER) |
| 2 | Geographic data (smaller than state) | NER + pattern matching |
| 3 | Dates (except year) | Pattern matching |
| 4 | Phone numbers | Pattern matching |
| 5 | Fax numbers | Pattern matching |
| 6 | Email addresses | Pattern matching |
| 7 | Social Security numbers | Pattern matching |
| 8 | Medical record numbers | Custom pattern matching |
| 9 | Health plan beneficiary numbers | Custom pattern matching |
| 10 | Account numbers | Pattern matching |
| 11 | Certificate/license numbers | Pattern matching |
| 12 | Vehicle identifiers | Custom pattern matching |
| 13 | Device identifiers | Custom pattern matching |
| 14 | Web URLs | Pattern matching |
| 15 | IP addresses | Pattern matching |
| 16 | Biometric identifiers | Custom pattern matching |
| 17 | Full-face photographs | Out of scope (text only) |
| 18 | Other unique identifiers | Configurable custom patterns |

## Technology Stack

- **Microsoft Presidio** (v2.2.x): Open-source PII detection and anonymization framework developed by Microsoft
- **SpaCy** (en_core_web_lg): Pre-trained English NLP model for named entity recognition
- **Custom Recognizers**: Pattern-based recognizers for domain-specific identifiers (MRNs, study IDs, etc.)

## Anonymization Strategies

Researchers can select from the following anonymization strategies for each identifier type:

| Strategy | Description | Example |
|----------|-------------|---------|
| **Redaction** | Replace with `[REDACTED]` | "John Smith" → "[REDACTED]" |
| **Type Tagging** | Replace with entity type and counter | "John Smith" → "[PERSON_1]" |
| **Masking** | Partial character replacement | "John Smith" → "J*** S****" |
| **Hashing** | SHA-256 deterministic pseudonym | "John Smith" → "a1b2c3d4" |
| **Fake Replacement** | Replace with realistic synthetic data | "John Smith" → "Jane Doe" |

## Confidence Thresholds

Each detection includes a confidence score (0.0-1.0). Researchers can configure the minimum confidence threshold:

- **Aggressive (0.3-0.5)**: Maximizes detection, may include false positives
- **Moderate (0.7)**: Balanced approach (recommended default)
- **Conservative (0.8-1.0)**: Minimizes false positives, may miss some identifiers

**Recommendation**: For IRB-approved research, we recommend a threshold of 0.5 with manual review of flagged items to balance completeness with accuracy.

## Audit Trail

Each de-identification run produces a JSON audit log documenting:

- Unique run identifier (UUID)
- Timestamp
- Configuration settings (entity types, threshold, strategies)
- Summary statistics (total records, total detections by type)
- Per-detection details:
  - Record identifier
  - Field name
  - Entity type detected
  - Confidence score
  - Position in text (start/end character)
  - Anonymization action taken
  - **Length of original text (NOT the text itself)**

**Important**: The audit log never contains the original PII text, only metadata about the detection.

## Limitations

1. **Language**: The NLP model is trained on English text. Detection accuracy may be reduced for other languages.
2. **Context**: Some PII may be missed if it appears in unusual contexts or formats.
3. **Domain-Specific Terms**: Medical or research-specific identifiers may require custom recognizer configuration.
4. **Images**: The tool processes text only; embedded images are not analyzed.

## Quality Assurance

We recommend the following QA process:

1. **Sample Review**: Manually review a random sample of de-identified records
2. **Threshold Tuning**: Adjust confidence threshold based on false positive/negative rates
3. **Custom Patterns**: Add domain-specific patterns for identifiers unique to your study
4. **Audit Log Review**: Review the audit log for unexpected patterns or missed detections

## Recommended IRB Language

You may adapt the following language for your IRB application:

> Data de-identification will be performed using the De-Identification App, an open-source tool that runs locally on the researcher's computer with no network access. The tool uses Microsoft Presidio and SpaCy natural language processing to detect and remove HIPAA Safe Harbor identifiers. All processing occurs locally; no data is transmitted externally. Each de-identification run produces an audit log documenting the identifiers detected and actions taken, without recording the original PII text. The researcher will review a sample of de-identified records to verify accuracy before analysis.

---

## Version Information

- Document Version: 1.0
- App Version: 1.0.0
- Presidio Version: 2.2.355
- SpaCy Model: en_core_web_lg (3.7.x)
