#!/usr/bin/env python3
"""Phase 2: Analysis - Classify documents using multi-signal approach.

This script provides automated classification helpers (filename patterns, normative 
reference detection, keyword matching). For semantic content analysis, Claude should 
read the inventory and use its own reasoning to refine classifications.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent / "references"

# Document type keywords (filename and content)
TYPE_PATTERNS = {
    "POL": {
        "filename": r"(?i)(policy|politica|principi|indirizzo)",
        "content": r"(?i)(l.organizzazione si impegna|obiettivo della presente policy|principi fondamentali|approvat[oa] da|organi direttivi)"
    },
    "PRC": {
        "filename": r"(?i)(processo|workflow|flusso)",
        "content": r"(?i)(flusso del processo|input.*output|RACI|responsabilit[àa] macro|swim lane)"
    },
    "PRO": {
        "filename": r"(?i)(procedura|modalit[àa]\s*operative|SOP|istruzioni\s*per)",
        "content": r"(?i)(chi fa cosa|modalit[àa] operative|step\s*\d|fase\s*\d|attivit[àa]\s*previste)"
    },
    "LG": {
        "filename": r"(?i)(linea\s*guida|guida|raccomandazion[ei]|best\s*practice)",
        "content": r"(?i)(si raccomanda|[eè] consigliabile|buona pratica|orientamento)"
    },
    "IO": {
        "filename": r"(?i)(istruzione\s*operativa|step.by.step|how.to)",
        "content": r"(?i)(eseguire i seguenti passaggi|step\s*1|istruzione\s*\d)"
    },
    "MAN": {
        "filename": r"(?i)(manuale|handbook|manual)",
        "content": r"(?i)(manuale\s*(operativo|tecnico|utente)|guida completa)"
    },
    "PLB": {
        "filename": r"(?i)(playbook|runbook|response\s*plan)",
        "content": r"(?i)(in caso di|scenario|escalation|azioni\s*predefin|decision\s*tree)"
    },
    "PIA": {
        "filename": r"(?i)(piano|plan|programma|roadmap)",
        "content": r"(?i)(tempistica|milestone|risorse\s*alloc|obiettivo\s*del\s*piano|cronoprogramma)"
    },
    "REG": {
        "filename": r"(?i)(registro|inventario|catalogo|elenco|log)",
        "content": r"(?i)(elenco\s*(completo|aggiornato)|catalogo|inventario|data\s*ultimo\s*aggiornamento)"
    },
    "REP": {
        "filename": r"(?i)(report|relazione|dashboard|KPI)",
        "content": r"(?i)(nel periodo|risultati|finding|raccomandazion|metriche|andamento)"
    },
    "DOC": {
        "filename": r"(?i)(documento|statement|dichiarazione|organigramma|charter)",
        "content": r"(?i)(dichiarazione|statement|organigramma|struttura organizzativa)"
    }
}

# Process area keywords
PROCESS_KEYWORDS = {
    "01. GOVERNANCE E STRATEGIA": ["governance", "comitato sicurezza", "direzione", "organizzazione sicurezza", "ruoli e responsabilità", "stakeholder", "strategia sicurezza"],
    "02. GESTIONE DEL RISCHIO": ["risk assessment", "analisi rischio", "trattamento rischio", "rischio residuo", "probabilità", "impatto", "SoA", "statement of applicability"],
    "03. GESTIONE DEGLI ASSET": ["asset", "inventario hardware", "inventario software", "CMDB", "classificazione informazioni", "servizi ICT", "flussi informativi"],
    "04. CONTROLLO DEGLI ACCESSI": ["controllo accessi", "autenticazione", "autorizzazione", "MFA", "password", "privilegiati", "IAM", "RBAC", "provisioning"],
    "05. PROTEZIONE DEI DATI": ["crittografia", "cifratura", "backup", "DLP", "data loss", "protezione dati", "mascheramento", "key management"],
    "06. SICUREZZA DELLE RETI": ["rete", "network", "firewall", "segmentazione", "VPN", "DMZ", "IDS", "IPS", "WiFi", "wireless"],
    "07. SICUREZZA ENDPOINT": ["endpoint", "antivirus", "EDR", "patching", "hardening", "configurazione sicura", "BYOD", "mobile device"],
    "08. GESTIONE VULNERABILITÀ": ["vulnerabilità", "vulnerability", "scanning", "penetration test", "CVE", "patch management", "remediation"],
    "09. CHANGE MANAGEMENT": ["change management", "gestione cambiamento", "rilascio", "deploy", "configurazione baseline", "CAB"],
    "10. SICUREZZA APPLICATIVA": ["sicurezza applicativa", "SDLC", "code review", "SAST", "DAST", "DevSecOps", "API security", "OWASP"],
    "11. SICUREZZA FISICA": ["sicurezza fisica", "accesso fisico", "videosorveglianza", "CED", "data center", "ambientale", "incendio", "controllo visitatori"],
    "12. MONITORAGGIO E DETECTION": ["monitoraggio", "SIEM", "SOC", "logging", "detection", "correlazione", "anomalia", "allarme", "use case"],
    "13. INCIDENT MANAGEMENT": ["incidente", "incident", "breach", "contenimento", "eradicazione", "risposta incidente", "notifica", "forensic", "triage"],
    "14. CONTINUITÀ OPERATIVA": ["continuità operativa", "BCP", "disaster recovery", "RPO", "RTO", "failover", "crisi", "business impact"],
    "15. THREAT INTELLIGENCE": ["threat intelligence", "minacce", "IoC", "indicatori compromissione", "TTP", "MITRE ATT&CK", "CTI"],
    "16. FORMAZIONE E AWARENESS": ["formazione", "awareness", "sensibilizzazione", "training", "phishing simulation", "e-learning", "competenze"],
    "17. GESTIONE FORNITORI": ["fornitore", "terza parte", "supply chain", "SLA", "contratto", "outsourcing", "subappalto", "due diligence"],
    "18. COMPLIANCE E AUDIT": ["audit", "compliance", "conformità", "riesame", "non conformità", "azione correttiva", "certificazione", "evidenze"],
    "19. RISORSE UMANE": ["risorse umane", "onboarding", "offboarding", "NDA", "disciplinare", "screening", "cessazione rapporto"],
    "20. MIGLIORAMENTO CONTINUO": ["miglioramento continuo", "PDCA", "KPI sicurezza", "obiettivi sicurezza", "gestione documentazione", "lessons learned", "riesame direzione"]
}

# Normative reference regex patterns
NORM_PATTERNS = [
    (r"ISO\s*27001[:.]?\s*([\d.]+|A\.\d+\.\d+)", "ISO27001"),
    (r"NIS\s*2[:.]?\s*Art\.?\s*(\d+)", "NIS2"),
    (r"FNCS[:.]?\s*(GV|ID|PR|DE|RS|RC)", "FNCS"),
    (r"ACN[-\s]*DET[:.]?\s*([A-Z]{2}\.[A-Z]{2})", "ACN-DET"),
    (r"GDPR[:.]?\s*Art\.?\s*(\d+)", "GDPR"),
    (r"AgID[-\s]*MM[:.]?\s*ABSC\s*(\d+)", "AgID-MM"),
    (r"L\.?\s*90/2024[:.]?\s*Art\.?\s*(\d+)", "L90/2024"),
    (r"D\.?\s*Lgs\.?\s*138/2024", "NIS2-DLgs"),
]


def load_index(index_path=None):
    if index_path is None:
        index_path = SCRIPT_DIR / "document_index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_normative_map(map_path=None):
    if map_path is None:
        map_path = SCRIPT_DIR / "normative_mapping.json"
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_type_from_filename(filename):
    scores = {}
    for type_code, patterns in TYPE_PATTERNS.items():
        if re.search(patterns["filename"], filename):
            scores[type_code] = 1.0
    return scores


def detect_type_from_content(text):
    if not text or text.startswith("["):
        return {}
    scores = {}
    for type_code, patterns in TYPE_PATTERNS.items():
        matches = len(re.findall(patterns["content"], text))
        if matches > 0:
            scores[type_code] = min(1.0, matches * 0.3)
    return scores


def detect_process_from_text(text, folder_path=""):
    combined = (folder_path + " " + text).lower()
    scores = {}
    for process, keywords in PROCESS_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in combined)
        if match_count > 0:
            scores[process] = min(1.0, match_count / max(3, len(keywords) * 0.4))
    return scores


def detect_normative_refs(text):
    refs = []
    for pattern, source in NORM_PATTERNS:
        for match in re.finditer(pattern, text):
            refs.append({"source": source, "reference": match.group(0), "detail": match.group(1) if match.lastindex else ""})
    return refs


def match_to_index(file_entry, index_docs):
    """Match a file to the best COD_DOC from the index. Returns sorted candidates."""
    filename = file_entry.get("file_name", "")
    text = file_entry.get("text_preview", "")
    folder = file_entry.get("folder_path", "")
    title_from_file = file_entry.get("title", "")

    type_fn = detect_type_from_filename(filename)
    type_ct = detect_type_from_content(text)
    process_scores = detect_process_from_text(text, folder)
    norm_refs = detect_normative_refs(text)
    norm_sources = {r["reference"] for r in norm_refs}

    candidates = []
    for doc in index_docs:
        score = 0.0
        signals = []

        # Filename match against doc title
        doc_title_words = set(doc["titolo"].lower().split())
        fn_words = set(re.sub(r"[_\-.]", " ", Path(filename).stem).lower().split())
        title_overlap = len(doc_title_words & fn_words) / max(len(doc_title_words), 1)
        if title_overlap > 0.2:
            score += title_overlap * 0.20
            signals.append(f"filename_title_match:{title_overlap:.2f}")

        # Type match
        doc_type = doc["tipologia"]
        if doc_type in type_fn:
            score += type_fn[doc_type] * 0.10
            signals.append("type_filename_match")
        if doc_type in type_ct:
            score += type_ct[doc_type] * 0.10
            signals.append("type_content_match")

        # Process match
        processo = doc["processo"]
        if processo in process_scores:
            score += process_scores[processo] * 0.25
            signals.append(f"process_match:{process_scores[processo]:.2f}")

        # Normative reference match
        doc_reqs = doc.get("requisiti_fonti", "")
        if doc_reqs and norm_sources:
            req_matches = sum(1 for ns in norm_sources if ns in doc_reqs)
            if req_matches > 0:
                norm_score = min(1.0, req_matches * 0.25)
                score += norm_score * 0.20
                signals.append(f"normative_match:{req_matches}")

        # Content keyword match against doc title and notes
        if text:
            doc_keywords = (doc["titolo"] + " " + doc.get("note", "")).lower()
            kw_list = [w for w in doc_keywords.split() if len(w) > 3]
            text_lower = text.lower()
            kw_hits = sum(1 for kw in kw_list if kw in text_lower)
            if kw_hits > 0:
                kw_score = min(1.0, kw_hits / max(3, len(kw_list) * 0.3))
                score += kw_score * 0.15
                signals.append(f"content_keywords:{kw_hits}")

        if score > 0.05:
            candidates.append({
                "cod_doc": doc["cod_doc"],
                "titolo": doc["titolo"],
                "processo": doc["processo"],
                "tipologia": doc["tipologia"],
                "funzione_fncs": doc["funzione_fncs"],
                "priorita": doc["priorita"],
                "confidence": round(min(1.0, score), 3),
                "signals": signals
            })

    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    return candidates[:5]


def classify_inventory(inventory, index_docs, threshold=0.85):
    results = []
    for file_entry in inventory["files"]:
        candidates = match_to_index(file_entry, index_docs)
        best = candidates[0] if candidates else None
        confidence = best["confidence"] if best else 0.0

        if confidence >= threshold:
            level = "HIGH"
        elif confidence >= 0.60:
            level = "MEDIUM"
        elif confidence >= 0.30:
            level = "LOW"
        else:
            level = "UNCLASSIFIED"

        norm_refs = detect_normative_refs(file_entry.get("text_preview", ""))

        result = {
            "file_id": file_entry["id"],
            "file_path": file_entry["file_path"],
            "file_name": file_entry["file_name"],
            "checksum": file_entry.get("checksum_sha256", ""),
            "classification": {
                "cod_doc": best["cod_doc"] if best else None,
                "titolo": best["titolo"] if best else None,
                "processo": best["processo"] if best else None,
                "tipologia": best["tipologia"] if best else None,
                "funzione_fncs": best["funzione_fncs"] if best else None,
                "priorita": best["priorita"] if best else None,
            },
            "confidence": confidence,
            "confidence_level": level,
            "signals": best["signals"] if best else [],
            "alternatives": candidates[1:4] if len(candidates) > 1 else [],
            "normative_refs_found": norm_refs,
            "needs_review": level in ("MEDIUM", "LOW"),
            "is_orphan": level == "UNCLASSIFIED"
        }
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Classify documents against ICT security index")
    parser.add_argument("inventory", help="Path to inventory.json from Phase 1")
    parser.add_argument("--index", default=None, help="Path to document_index.json")
    parser.add_argument("--output", "-o", default="classification.json", help="Output file")
    parser.add_argument("--threshold", type=float, default=0.85, help="Confidence threshold for auto-accept")
    args = parser.parse_args()

    with open(args.inventory, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    index_docs = load_index(args.index)
    print(f"Loaded {len(index_docs)} index documents", file=sys.stderr)
    print(f"Classifying {inventory['total_files']} files...", file=sys.stderr)

    results = classify_inventory(inventory, index_docs, args.threshold)

    stats = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNCLASSIFIED": 0}
    for r in results:
        stats[r["confidence_level"]] += 1

    output = {
        "source_path": inventory["source_path"],
        "classification_date": __import__("datetime").datetime.now().isoformat(),
        "threshold": args.threshold,
        "stats": stats,
        "total_classified": len(results),
        "needs_review": sum(1 for r in results if r["needs_review"]),
        "orphans": sum(1 for r in results if r["is_orphan"]),
        "classifications": results
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nClassification complete:", file=sys.stderr)
    print(f"  HIGH confidence: {stats['HIGH']}", file=sys.stderr)
    print(f"  MEDIUM (needs review): {stats['MEDIUM']}", file=sys.stderr)
    print(f"  LOW (needs review): {stats['LOW']}", file=sys.stderr)
    print(f"  UNCLASSIFIED (orphans): {stats['UNCLASSIFIED']}", file=sys.stderr)
    print(f"  Output: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
