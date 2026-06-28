# Changelog

All notable changes to SilentFail will be documented here.

## [0.1.0] — 2026-06-16

### Added
- `SchemaDriftDetector` — detects silent None returns and unhandled exceptions on malformed inputs
- `ConfidentWrongDetector` — flags pipelines that answer incorrectly with no uncertainty hedging
- `SilentTruncationDetector` — detects output degradation near context window limits
- `HallucinatedStructureDetector` — catches invented keys, missing fields, and type mismatches in LLM output
- `Auditor` class — single entry point wiring all four detectors
- `AuditReport` — rich console summary and self-contained HTML export
- `LangChainRunner` and `FunctionRunner` — pipeline wrappers
- `GoldenDataset` — builder and loader for golden test samples
- 32 tests across Python 3.10, 3.11, 3.12
- CI/CD via GitHub Actions with automated PyPI publish on release
