#!/usr/bin/env python3
"""Phase 4: Reorganize - Create target folder structure and copy files."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Process area folder names
PROCESS_FOLDERS = {
    "01. GOVERNANCE E STRATEGIA": "01_GOVERNANCE_E_STRATEGIA",
    "02. GESTIONE DEL RISCHIO": "02_GESTIONE_DEL_RISCHIO",
    "03. GESTIONE DEGLI ASSET": "03_GESTIONE_DEGLI_ASSET",
    "04. CONTROLLO DEGLI ACCESSI": "04_CONTROLLO_DEGLI_ACCESSI",
    "05. PROTEZIONE DEI DATI": "05_PROTEZIONE_DEI_DATI",
    "06. SICUREZZA DELLE RETI": "06_SICUREZZA_DELLE_RETI",
    "07. SICUREZZA ENDPOINT": "07_SICUREZZA_ENDPOINT",
    "08. GESTIONE VULNERABILITÀ": "08_GESTIONE_VULNERABILITA",
    "09. CHANGE MANAGEMENT": "09_CHANGE_MANAGEMENT",
    "10. SICUREZZA APPLICATIVA": "10_SICUREZZA_APPLICATIVA",
    "11. SICUREZZA FISICA": "11_SICUREZZA_FISICA",
    "12. MONITORAGGIO E DETECTION": "12_MONITORAGGIO_E_DETECTION",
    "13. INCIDENT MANAGEMENT": "13_INCIDENT_MANAGEMENT",
    "14. CONTINUITÀ OPERATIVA": "14_CONTINUITA_OPERATIVA",
    "15. THREAT INTELLIGENCE": "15_THREAT_INTELLIGENCE",
    "16. FORMAZIONE E AWARENESS": "16_FORMAZIONE_E_AWARENESS",
    "17. GESTIONE FORNITORI": "17_GESTIONE_FORNITORI",
    "18. COMPLIANCE E AUDIT": "18_COMPLIANCE_E_AUDIT",
    "19. RISORSE UMANE": "19_RISORSE_UMANE",
    "20. MIGLIORAMENTO CONTINUO": "20_MIGLIORAMENTO_CONTINUO",
}

TYPE_FOLDERS = ["POL", "PRC", "PRO", "LG", "IO", "MAN", "PLB", "PIA", "REG", "REP", "DOC"]


def normalize_title(title):
    """Convert document title to filesystem-safe name."""
    t = title.replace("'", "").replace('"', "").replace("(", "").replace(")", "")
    t = re.sub(r"[^a-zA-Z0-9àèéìòùÀÈÉÌÒÙ\s]", "", t)
    t = re.sub(r"\s+", "_", t.strip())
    # Remove accented chars for filesystem safety
    replacements = {"à": "a", "è": "e", "é": "e", "ì": "i", "ò": "o", "ù": "u",
                    "À": "A", "È": "E", "É": "E", "Ì": "I", "Ò": "O", "Ù": "U"}
    for k, v in replacements.items():
        t = t.replace(k, v)
    return t[:80]  # max length


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def build_plan(mapping_data, source_path, target_path):
    """Build reorganization plan from mapping data."""
    operations = []
    source = Path(source_path)
    target = Path(target_path)

    # Create directory structure plan
    dirs_to_create = set()
    dirs_to_create.add(str(target / "_NON_CLASSIFICATI"))
    dirs_to_create.add(str(target / "_ARCHIVIO_VERSIONI"))
    dirs_to_create.add(str(target / "_REPORT_SISTEMA"))

    for proc_name, folder_name in PROCESS_FOLDERS.items():
        for type_folder in TYPE_FOLDERS:
            dirs_to_create.add(str(target / folder_name / type_folder))

    # Plan file copies for mapped documents
    for doc_entry in mapping_data["document_mapping"]:
        if doc_entry["status"] == "GAP":
            continue

        processo = doc_entry["processo"]
        tipologia = doc_entry["tipologia"]
        cod_doc = doc_entry["cod_doc"]
        titolo = doc_entry["titolo"]

        proc_folder = PROCESS_FOLDERS.get(processo, "00_UNKNOWN")
        type_folder = tipologia if tipologia in TYPE_FOLDERS else "DOC"

        for i, mapped_file in enumerate(doc_entry["mapped_files"]):
            src_file = source / mapped_file["file_path"]
            ext = Path(mapped_file["file_name"]).suffix

            if len(doc_entry["mapped_files"]) > 1:
                version = f"v{i+1}.0"
            else:
                version = "v1.0"

            new_name = f"{cod_doc}_{normalize_title(titolo)}_{version}{ext}"
            dest_file = target / proc_folder / type_folder / new_name

            operations.append({
                "action": "COPY",
                "source": str(src_file),
                "destination": str(dest_file),
                "cod_doc": cod_doc,
                "confidence": mapped_file["confidence"],
                "confidence_level": mapped_file["confidence_level"],
                "status": doc_entry["status"]
            })

    # Plan orphan copies
    for orphan in mapping_data.get("orphans", []):
        src_file = source / orphan["file_path"]
        dest_file = target / "_NON_CLASSIFICATI" / orphan["file_name"]
        operations.append({
            "action": "COPY",
            "source": str(src_file),
            "destination": str(dest_file),
            "cod_doc": None,
            "confidence": orphan["confidence"],
            "confidence_level": "UNCLASSIFIED",
            "status": "ORPHAN"
        })

    return {
        "plan_date": datetime.now().isoformat(),
        "source_path": str(source),
        "target_path": str(target),
        "directories_to_create": sorted(dirs_to_create),
        "total_operations": len(operations),
        "operations": operations
    }


def execute_plan(plan, dry_run=True):
    """Execute the reorganization plan."""
    log = []
    errors = []

    if dry_run:
        print("\n=== DRY RUN MODE - No files will be modified ===\n")
    else:
        print("\n=== EXECUTING REORGANIZATION ===\n")

    # Create directories
    for dir_path in plan["directories_to_create"]:
        if dry_run:
            print(f"  [MKDIR] {dir_path}")
        else:
            os.makedirs(dir_path, exist_ok=True)
        log.append({"action": "MKDIR", "path": dir_path, "status": "OK" if not dry_run else "DRY_RUN"})

    # Execute file operations
    copied = 0
    failed = 0
    for op in plan["operations"]:
        src = op["source"]
        dst = op["destination"]
        cod = op.get("cod_doc", "N/A")

        if dry_run:
            exists = "✓" if os.path.exists(src) else "✗"
            print(f"  [{exists}] {op['action']} [{cod}] {Path(src).name} -> {Path(dst).name}")
            log.append({**op, "status": "DRY_RUN", "timestamp": datetime.now().isoformat()})
        else:
            try:
                if not os.path.exists(src):
                    raise FileNotFoundError(f"Source not found: {src}")

                # Ensure destination directory exists
                os.makedirs(Path(dst).parent, exist_ok=True)

                # Handle name collision
                if os.path.exists(dst):
                    stem = Path(dst).stem
                    ext = Path(dst).suffix
                    parent = Path(dst).parent
                    counter = 1
                    while os.path.exists(dst):
                        dst = str(parent / f"{stem}_{counter}{ext}")
                        counter += 1

                # Copy file
                shutil.copy2(src, dst)

                # Verify integrity
                src_hash = sha256_file(src)
                dst_hash = sha256_file(dst)
                if src_hash != dst_hash:
                    raise ValueError(f"Integrity check failed: {src_hash} != {dst_hash}")

                copied += 1
                print(f"  [✓] {Path(src).name} -> {Path(dst).name}")
                log.append({
                    **op, "destination": dst, "status": "OK",
                    "src_hash": src_hash, "dst_hash": dst_hash,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                failed += 1
                print(f"  [✗] FAILED: {Path(src).name} - {e}", file=sys.stderr)
                errors.append({"source": src, "destination": dst, "error": str(e)})
                log.append({**op, "status": "FAILED", "error": str(e), "timestamp": datetime.now().isoformat()})

    if not dry_run:
        print(f"\n  Copied: {copied}, Failed: {failed}")

    return {
        "execution_date": datetime.now().isoformat(),
        "mode": "dry_run" if dry_run else "execute",
        "total_operations": len(plan["operations"]),
        "copied": copied if not dry_run else 0,
        "failed": failed if not dry_run else 0,
        "log": log,
        "errors": errors
    }


def rollback(log_file):
    """Rollback executed operations by removing copied files."""
    with open(log_file, "r", encoding="utf-8") as f:
        exec_log = json.load(f)

    if exec_log.get("mode") != "execute":
        print("Error: Can only rollback executed operations", file=sys.stderr)
        return

    removed = 0
    for entry in reversed(exec_log.get("log", [])):
        if entry.get("status") == "OK" and entry.get("action") == "COPY":
            dst = entry["destination"]
            if os.path.exists(dst):
                os.remove(dst)
                removed += 1
                print(f"  [UNDO] Removed: {dst}")

    print(f"\nRollback complete: {removed} files removed")


def main():
    parser = argparse.ArgumentParser(description="Phase 4: Reorganize documents")
    parser.add_argument("mapping", help="Path to mapping.json from Phase 3")
    parser.add_argument("target_path", help="Target directory for reorganized structure")
    parser.add_argument("--source", help="Source directory (override mapping source)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    parser.add_argument("--execute", action="store_true", help="Actually copy files")
    parser.add_argument("--rollback", help="Rollback using execution log file")
    parser.add_argument("--output", "-o", default="operations_log.json", help="Operations log output")
    args = parser.parse_args()

    if args.rollback:
        rollback(args.rollback)
        return

    with open(args.mapping, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    source_path = args.source or mapping_data.get("source_path", "")
    if not source_path:
        print("Error: source path required (--source or from mapping)", file=sys.stderr)
        sys.exit(1)

    plan = build_plan(mapping_data, source_path, args.target_path)

    with open("reorganization_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"Plan saved: reorganization_plan.json ({plan['total_operations']} operations)")

    is_dry_run = not args.execute
    result = execute_plan(plan, dry_run=is_dry_run)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Log saved: {args.output}")


if __name__ == "__main__":
    main()
