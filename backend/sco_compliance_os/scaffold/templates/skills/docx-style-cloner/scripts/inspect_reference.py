#!/usr/bin/env python3
"""
inspect_reference.py — Analizza un documento .docx di riferimento e produce
un report JSON con tutti i parametri di stile rilevanti per la clonazione.

Uso:
    python inspect_reference.py <path_to_reference.docx>

Output: JSON su stdout con la struttura:
{
  "file": "...",
  "primary_font": {"name": "Calibri", "size_pt": 11},
  "named_styles_used": ["Normal", "Heading 1", "Heading 2", ...],
  "sections": [{"margins": {...}, "header": {...}, "footer": {...}}],
  "language": "it-IT",
  "tables_count": 0,
  "lists_count": 0,
  "images_in_headers_footers": [...],
  "warnings": [...]
}
"""

import json
import sys
from collections import Counter
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Emu
except ImportError:
    print(json.dumps({
        "error": "python-docx non installato. Esegui: pip install python-docx --break-system-packages"
    }))
    sys.exit(1)


def emu_to_cm(emu):
    """Converte Emu in centimetri."""
    if emu is None:
        return None
    return round(emu / 360000, 2)


def get_primary_font(doc):
    """Determina il font primario del corpo del testo analizzando i paragrafi
    con stile 'Normal' / 'Normale' o senza stile esplicito."""
    fonts = Counter()
    sizes = Counter()

    # Default da style 'Normal'
    try:
        normal = doc.styles["Normal"]
        if normal.font.name:
            fonts[normal.font.name] += 100  # peso forte
        if normal.font.size:
            sizes[normal.font.size.pt] += 100
    except KeyError:
        pass
    try:
        normal_it = doc.styles["Normale"]
        if normal_it.font.name:
            fonts[normal_it.font.name] += 100
        if normal_it.font.size:
            sizes[normal_it.font.size.pt] += 100
    except KeyError:
        pass

    # Conteggio sui run dei paragrafi del body
    for para in doc.paragraphs:
        for run in para.runs:
            if run.font.name:
                fonts[run.font.name] += 1
            if run.font.size:
                sizes[run.font.size.pt] += 1

    primary_font = fonts.most_common(1)[0][0] if fonts else None
    primary_size = sizes.most_common(1)[0][0] if sizes else None

    return {"name": primary_font, "size_pt": primary_size}


def get_named_styles_used(doc):
    """Restituisce l'elenco degli stili nominati effettivamente usati nel documento."""
    used = set()
    for para in doc.paragraphs:
        if para.style and para.style.name:
            used.add(para.style.name)
    for table in doc.tables:
        if table.style and table.style.name:
            used.add(table.style.name)
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if para.style and para.style.name:
                        used.add(para.style.name)
    return sorted(used)


def get_section_info(section):
    """Estrae margini, dimensioni pagina, header e footer di una sezione."""
    info = {
        "page_size_cm": {
            "width": emu_to_cm(section.page_width),
            "height": emu_to_cm(section.page_height),
        },
        "margins_cm": {
            "top": emu_to_cm(section.top_margin),
            "bottom": emu_to_cm(section.bottom_margin),
            "left": emu_to_cm(section.left_margin),
            "right": emu_to_cm(section.right_margin),
            "header_distance": emu_to_cm(section.header_distance),
            "footer_distance": emu_to_cm(section.footer_distance),
        },
        "orientation": str(section.orientation).split(".")[-1] if section.orientation else None,
        "header": extract_header_footer_content(section.header),
        "footer": extract_header_footer_content(section.footer),
    }
    return info


def extract_header_footer_content(header_or_footer):
    """Estrae testo e nome immagini da header o footer."""
    if header_or_footer is None:
        return {"text": "", "images": [], "is_linked_to_previous": False}

    text_parts = []
    for para in header_or_footer.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())

    # Cerca immagini iterando sull'XML
    images = []
    try:
        from docx.oxml.ns import qn
        for blip in header_or_footer._element.iter(qn("a:blip")):
            embed = blip.get(qn("r:embed"))
            if embed:
                # Risale al rId per ottenere il nome del file
                images.append({"rId": embed})
    except Exception:
        pass

    return {
        "text": " | ".join(text_parts),
        "paragraphs": text_parts,
        "images": images,
        "is_linked_to_previous": header_or_footer.is_linked_to_previous,
    }


def detect_language(doc):
    """Rileva la lingua dominante del documento dal style Normal o dai run."""
    try:
        from docx.oxml.ns import qn
        # Cerca w:lang nel default style
        styles_xml = doc.styles.element
        for lang_el in styles_xml.iter(qn("w:lang")):
            val = lang_el.get(qn("w:val"))
            if val:
                return val
    except Exception:
        pass
    return "unknown"


def count_lists(doc):
    """Conta paragrafi con numerazione/bullet (approssimato)."""
    count = 0
    for para in doc.paragraphs:
        if para.style and para.style.name and (
            "List" in para.style.name or "Elenco" in para.style.name
        ):
            count += 1
        elif para._p.find(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr"
        ) is not None:
            ppr = para._p.find(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr"
            )
            if ppr.find(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr"
            ) is not None:
                count += 1
    return count


def inspect(path):
    """Funzione principale: analizza il documento e restituisce dict report."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File non trovato: {path}"}
    if p.suffix.lower() != ".docx":
        return {"error": f"Formato non supportato: {p.suffix}. Atteso: .docx"}

    warnings = []
    try:
        doc = Document(str(p))
    except Exception as e:
        return {"error": f"Impossibile aprire il documento: {e}"}

    primary_font = get_primary_font(doc)
    named_styles = get_named_styles_used(doc)
    sections = [get_section_info(s) for s in doc.sections]
    language = detect_language(doc)
    tables_count = len(doc.tables)
    lists_count = count_lists(doc)

    # Avvisi
    if not primary_font["name"]:
        warnings.append("Font primario non rilevato: il documento potrebbe usare default Word")
    if not named_styles:
        warnings.append("Nessuno stile nominato rilevato: documento con formattazione manuale")

    return {
        "file": str(p),
        "primary_font": primary_font,
        "named_styles_used": named_styles,
        "sections_count": len(sections),
        "sections": sections,
        "language": language,
        "tables_count": tables_count,
        "lists_count": lists_count,
        "warnings": warnings,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Uso: python inspect_reference.py <file.docx>"}))
        sys.exit(1)

    result = inspect(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
