#!/usr/bin/env python3
"""Phase 3: Mapping - Build correspondence matrix between files and document index."""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent / "references"


def load_index(index_path=None):
    if index_path is None:
        index_path = SCRIPT_DIR / "document_index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_mapping(classification_data, index_docs):
    """Build full mapping: file->COD_DOC and COD_DOC->status."""
    cod_doc_files = defaultdict(list)
    orphans = []
    all_files = []

    for clf in classification_data["classifications"]:
        cod = clf["classification"]["cod_doc"]
        if clf["is_orphan"] or cod is None:
            orphans.append({
                "file_path": clf["file_path"],
                "file_name": clf["file_name"],
                "confidence": clf["confidence"],
                "status": "ORPHAN"
            })
        else:
            cod_doc_files[cod].append(clf)

    # Detect duplicates (same checksum)
    checksum_groups = defaultdict(list)
    for clf in classification_data["classifications"]:
        cs = clf.get("checksum", "")
        if cs:
            checksum_groups[cs].append(clf)

    duplicates = []
    for cs, group in checksum_groups.items():
        if len(group) > 1:
            duplicates.append({
                "checksum": cs,
                "files": [g["file_path"] for g in group],
                "count": len(group)
            })

    # Build COD_DOC status map
    index_map = {doc["cod_doc"]: doc for doc in index_docs}
    cod_doc_status = []

    for doc in index_docs:
        cod = doc["cod_doc"]
        files = cod_doc_files.get(cod, [])

        if len(files) == 0:
            status = "GAP"
        elif len(files) == 1:
            f = files[0]
            if f["confidence"] >= 0.85:
                status = "MAPPED"
            else:
                status = "PARTIAL"
        else:
            # Multiple files for same COD_DOC - check versions vs duplicates
            checksums = set(f.get("checksum", "") for f in files)
            if len(checksums) == 1 and "" not in checksums:
                status = "MAPPED"  # duplicates of same file
            else:
                status = "MULTI-MATCH"

        mapped_files = []
        for f in files:
            mapped_files.append({
                "file_path": f["file_path"],
                "file_name": f["file_name"],
                "confidence": f["confidence"],
                "confidence_level": f["confidence_level"],
                "checksum": f.get("checksum", "")
            })

        cod_doc_status.append({
            "cod_doc": cod,
            "titolo": doc["titolo"],
            "processo": doc["processo"],
            "tipologia": doc["tipologia"],
            "funzione_fncs": doc["funzione_fncs"],
            "priorita": doc["priorita"],
            "requisiti_fonti": doc.get("requisiti_fonti", ""),
            "status": status,
            "mapped_files": mapped_files,
            "file_count": len(files)
        })

    # Compute statistics
    status_counts = defaultdict(int)
    for item in cod_doc_status:
        status_counts[item["status"]] += 1

    priority_coverage = defaultdict(lambda: {"total": 0, "covered": 0})
    for item in cod_doc_status:
        p = item["priorita"]
        if p:
            priority_coverage[p]["total"] += 1
            if item["status"] in ("MAPPED", "MULTI-MATCH", "PARTIAL"):
                priority_coverage[p]["covered"] += 1

    process_coverage = defaultdict(lambda: {"total": 0, "covered": 0})
    for item in cod_doc_status:
        proc = item["processo"]
        process_coverage[proc]["total"] += 1
        if item["status"] in ("MAPPED", "MULTI-MATCH", "PARTIAL"):
            process_coverage[proc]["covered"] += 1

    total_docs = len(index_docs)
    covered = status_counts.get("MAPPED", 0) + status_counts.get("MULTI-MATCH", 0) + status_counts.get("PARTIAL", 0)

    return {
        "mapping_date": datetime.now().isoformat(),
        "source_path": classification_data.get("source_path", ""),
        "summary": {
            "total_index_documents": total_docs,
            "total_source_files": classification_data["total_classified"],
            "coverage_percent": round(covered / total_docs * 100, 1) if total_docs > 0 else 0,
            "status_counts": dict(status_counts),
            "orphan_count": len(orphans),
            "duplicate_groups": len(duplicates),
        },
        "priority_coverage": {
            k: {**v, "percent": round(v["covered"] / v["total"] * 100, 1) if v["total"] > 0 else 0}
            for k, v in priority_coverage.items()
        },
        "process_coverage": {
            k: {**v, "percent": round(v["covered"] / v["total"] * 100, 1) if v["total"] > 0 else 0}
            for k, v in sorted(process_coverage.items())
        },
        "document_mapping": cod_doc_status,
        "orphans": orphans,
        "duplicates": duplicates
    }


def print_summary(mapping):
    s = mapping["summary"]
    print(f"\n{'='*60}")
    print(f"  MAPPING SUMMARY")
    print(f"{'='*60}")
    print(f"  Index documents:    {s['total_index_documents']}")
    print(f"  Source files:       {s['total_source_files']}")
    print(f"  Coverage:           {s['coverage_percent']}%")
    print(f"  MAPPED:             {s['status_counts'].get('MAPPED', 0)}")
    print(f"  PARTIAL:            {s['status_counts'].get('PARTIAL', 0)}")
    print(f"  MULTI-MATCH:        {s['status_counts'].get('MULTI-MATCH', 0)}")
    print(f"  GAP:                {s['status_counts'].get('GAP', 0)}")
    print(f"  Orphans:            {s['orphan_count']}")
    print(f"  Duplicate groups:   {s['duplicate_groups']}")
    print()

    print("  Priority Coverage:")
    for prio, data in mapping["priority_coverage"].items():
        print(f"    {prio}: {data['covered']}/{data['total']} ({data['percent']}%)")
    print()

    gaps = [d for d in mapping["document_mapping"] if d["status"] == "GAP"]
    if gaps:
        print(f"  TOP GAPS (ALTA priority):")
        alta_gaps = [g for g in gaps if g["priorita"] == "ALTA"][:10]
        for g in alta_gaps:
            print(f"    [{g['cod_doc']}] {g['titolo']}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Build correspondence mapping")
    parser.add_argument("classification", help="Path to classification.json from Phase 2")
    parser.add_argument("--index", default=None, help="Path to document_index.json")
    parser.add_argument("--output", "-o", default="mapping.json", help="Output file")
    args = parser.parse_args()

    with open(args.classification, "r", encoding="utf-8") as f:
        clf_data = json.load(f)

    index_docs = load_index(args.index)
    mapping = build_mapping(clf_data, index_docs)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print_summary(mapping)
    print(f"Output: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
