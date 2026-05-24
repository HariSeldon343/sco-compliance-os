---
name: ict-doc-reorganizer
description: "Analyze, classify and reorganize ICT security documentation folders according to a standardized 137-document taxonomy covering 20 process areas and 10 document types, mapped to NIS2, ISO 27001, FNCS 2025, ACN, AgID, and GDPR requirements. Use this skill when the user wants to: (1) scan a folder of security documents and classify them, (2) reorganize documents into a structured compliance framework, (3) generate gap analysis or compliance coverage reports, (4) map existing documentation to NIS2/ISO/ACN/FNCS requirements, (5) identify missing or incomplete security documents. Triggers: mentions of 'document reorganization', 'security documentation', 'gap analysis', 'compliance mapping', 'NIS2 compliance', 'indice documentale', 'riorganizzazione documentale', 'sicurezza ICT', or any request to sort/classify/organize security-related files in a folder."
---

# ICT Document Reorganizer

Classify and reorganize ICT security documentation according to a 137-document taxonomy (20 process areas, 10 document types) mapped to NIS2, ISO 27001, FNCS 2025, ACN-DET, AgID-MM, GDPR.

## Workflow Overview

The process runs in 5 sequential phases:

1. **DISCOVERY** — Scan folder recursively, extract metadata and text previews
2. **ANALYSIS** — Classify each document (process area, doc code, type, FNCS function, priority)
3. **MAPPING** — Build correspondence matrix, identify gaps, duplicates, orphans
4. **REORGANIZE** — Create target structure and copy files (dry-run first, then execute)
5. **REPORTING** — Generate gap analysis, compliance map, executive summary

## Prerequisites

Install dependencies before first run:
```bash
pip install python-docx PyPDF2 pdfplumber openpyxl python-pptx pandas --break-system-packages
```

## Phase 1: Discovery

Run the discovery script on the user's source folder:

```bash
python scripts/discovery.py <source_path> [--output inventory.json] [--exclude .git,node_modules] [--max-depth 0]
```

The script recursively walks the directory, extracts file metadata (name, size, dates, SHA-256), and text preview (first 2000 chars) from supported formats: .docx, .pdf, .xlsx, .pptx, .txt, .md, .html, .csv, .odt.

Output: `inventory.json` with all file entries.

## Phase 2: Analysis (Classification)

Load the full taxonomy from `references/document_index.json`. Classify each document using 5 signals:

1. **Filename patterns** — keywords matching document types (policy, procedura, registro, etc.)
2. **Folder path** — parent folder names suggesting process areas
3. **Text content** — semantic analysis of extracted preview
4. **Normative references** — citations to ISO/NIS2/FNCS/ACN found in text, cross-referenced with `references/normative_mapping.json`
5. **Document metadata** — author, properties, tags

Assign 5 classification dimensions per document:

| Field | Values |
|-------|--------|
| PROCESSO | One of 20 areas (01-20) |
| COD_DOC | One of 137 codes (POL-001 to REG-019) |
| TIPOLOGIA | POL, PRC, PRO, LG, IO, MAN, PLB, PIA, REG, REP, DOC |
| FUNZIONE_FNCS | GV, ID, PR, DE, RS, RC |
| PRIORITA | ALTA, MEDIA, BASSA |

**Confidence scoring:** HIGH (≥0.85), MEDIUM (0.60–0.84), LOW (0.30–0.59), UNCLASSIFIED (<0.30).

Run: `python scripts/classify.py inventory.json [--index references/document_index.json] [--output classification.json] [--threshold 0.85]`

For MEDIUM/LOW confidence, prompt user interactively:
```
[?] backup_policy_2024.pdf => PRO-011 (Procedura Backup e Restore) [conf: 0.72]
    Alt.1: POL-008 (Politica Protezione Dati) [conf: 0.58]
    Confirm? [Y/n/1/skip]
```

See `references/classification_rules.md` for detailed keyword patterns and heuristics.

## Phase 3: Mapping

Build correspondence matrix: `python scripts/mapping.py classification.json [--output mapping.json]`

Status codes per COD_DOC:

| Status | Meaning | Action |
|--------|---------|--------|
| MAPPED | File matched | Move to target |
| PARTIAL | Partial coverage | Flag as draft |
| MULTI-MATCH | Covers multiple COD_DOCs | Cross-reference |
| GAP | No file exists | Report in gap analysis |
| ORPHAN | Unclassifiable | Move to `_NON_CLASSIFICATI/` |
| SUPERSEDED | Older version | Archive |

Detect duplicates via SHA-256. Group versions by COD_DOC, sort by date.

## Phase 4: Reorganize

**Target structure:**
```
ROOT/
├── 01_GOVERNANCE_E_STRATEGIA/{POL,PRC,DOC,REG,PIA,REP}/
├── 02_GESTIONE_DEL_RISCHIO/{PRC,PRO,DOC,REG,PIA}/
├── ... (all 20 process areas)
├── 20_MIGLIORAMENTO_CONTINUO/{PRC,PRO,REG,REP}/
├── _NON_CLASSIFICATI/
├── _ARCHIVIO_VERSIONI/
└── _REPORT_SISTEMA/
```

**Naming:** `[COD_DOC]_[Titolo_Normalizzato]_v[ver].[ext]`

```bash
# Dry-run (preview only)
python scripts/reorganize.py mapping.json <target_path> --source <source_path> --dry-run

# Execute (copies files, never deletes source)
python scripts/reorganize.py mapping.json <target_path> --source <source_path> --execute
```

**Safety rules:** Always copy never delete. Verify SHA-256 post-copy. Log everything. Support rollback.

## Phase 5: Reporting

```bash
python scripts/report.py mapping.json [--type gap|compliance|inventory|summary|all] [--format xlsx|docx|json] [--output reports/]
```

| Report | Content |
|--------|---------|
| gap_analysis | 137 COD_DOC status, priority, required actions |
| compliance_map | Normative source × documents matrix |
| inventory | Complete classified document list |
| completion_map | 20 processes × 10 types coverage pivot |
| executive_summary | Management summary with KPIs |

**KPIs:** Document coverage %, coverage by priority (ALTA/MEDIA/BASSA), by process area, normative coverage %, orphan ratio.

## Reference Files

- `references/document_index.json` — Full 137-document taxonomy. Read for COD_DOC, titles, areas, types, FNCS, priorities, requirements.
- `references/normative_mapping.json` — 67 normative requirements → document codes mapping.
- `references/classification_rules.md` — Keyword patterns, type indicators, classification heuristics.

## User Commands (Claude Code shortcuts)

| Command | Action |
|---------|--------|
| `/scan <path>` | Run Phase 1 |
| `/classify` | Run Phase 2 |
| `/map` | Run Phase 3 |
| `/plan` | Dry-run Phase 4 |
| `/execute` | Phase 4 with confirmation |
| `/report <type>` | Generate report |
| `/status` | Show state |
| `/rollback` | Undo last operation |

## Configuration

Place `config.json` in working directory:
```json
{
  "source_path": "/path/to/documents",
  "target_path": "/path/to/output",
  "mode": "dry-run",
  "confidence_threshold": 0.85,
  "interactive_review": true,
  "exclude_patterns": [".git", "node_modules", "__pycache__", ".DS_Store"],
  "ocr_enabled": false,
  "language": "it",
  "backup_original": true,
  "rename_files": true,
  "report_formats": ["xlsx", "docx", "json"]
}
```
