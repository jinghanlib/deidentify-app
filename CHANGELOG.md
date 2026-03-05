# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-XX-XX

### Added

- Initial release
- HIPAA Safe Harbor compliant PII detection (18 identifier types)
- Multiple anonymization strategies: redact, mask, hash, type tag, fake replacement
- Support for CSV, Excel, and text file formats
- Streamlit web interface with before/after preview
- Audit log generation for IRB compliance
- Docker deployment with network isolation
- Custom recognizers for MRNs, study IDs, insurance IDs
- Configurable confidence thresholds
- Column type auto-detection
- One-click launcher scripts for Mac/Linux and Windows
- uv support for development workflow

### Security

- Docker container runs with `--network none`
- No external API calls
- Runs as non-root user in container
- Input data mounted read-only
- Audit logs never contain original PII text
