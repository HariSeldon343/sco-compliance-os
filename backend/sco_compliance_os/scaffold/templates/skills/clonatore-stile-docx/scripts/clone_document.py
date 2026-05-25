#!/usr/bin/env python3
"""
clone_document.py — Clona lo stile di un documento .docx di riferimento e
inserisce nuovo contenuto, preservando integralmente:
- header e footer (testo e immagini)
- stili nominati
- sezioni e margini
- numerazione di pagina
- gerarchia titoli

Strategia: "template + body replacement".
1. Copia fisica del file di riferimento
2. Apertura con python-docx
3. Rimozione di tutti i paragrafi/tabelle del body (preservando section properties)
4. Inserimento del nuovo contenuto usando gli stili esistenti
5. Eventuale sostituzione globale font, header/footer, segnaposto
6. Salvataggio file finale

Uso da linea di comando:
    python clone_document.py \
        --reference path/al/riferimento.docx \
        --content path/al/contenuto.json \
        --output path/output.docx \
        [--font "Aptos"] \
        [--header-replacements '{"vecchio":"nuovo"}'] \
        [--footer-replacements '{"vecchio":"nuovo"}'] \
        [--placeholders '{"[DATA]":"26/04/2026"}']

Formato del file content.json:
{
    "blocks": [
        {"type": "heading1", "text": "Capitolo 1"},
        {"type": "heading2", "text": "Sezione 1.1"},
        {"type": "paragraph", "text": "Testo del paragrafo..."},
        {"type": "quote", "text": "Citazione"},
        {"type": "list_item", "text": "Voce di elenco", "level": 0},
        {"type": "table", "rows": [["A","B"], ["C","D"]]}
    ]
}
"""

import argparse
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path

try:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Pt
except ImportError:
    print("Errore: python-docx non installato. Esegui: pip install python-docx --break-system-packages")
    sys.exit(1)


# =============================================================================
# UTILITY: GESTIONE BODY
# =============================================================================

def remove_body_content(doc):
    """Rimuove tutti gli elementi del body (paragrafi e tabelle) preservando
    le section properties (sectPr) che contengono header/footer references,
    margini, dimensioni pagina."""
    body = doc.element.body
    sectPr = None

    # Salva l'ultimo sectPr (è quello che contiene i riferimenti a header/footer)
    last_sectPr = body.find(qn("w:sectPr"))
    if last_sectPr is not None:
        sectPr = deepcopy(last_sectPr)

    # Rimuovi tutti i figli tranne sectPr
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)

    return sectPr


def get_or_create_style(doc, style_name, fallback="Normal"):
    """Restituisce uno stile esistente o un fallback."""
    try:
        return doc.styles[style_name]
    except KeyError:
        # Tenta varianti italiane
        italian_map = {
            "Heading 1": ["Titolo 1"],
            "Heading 2": ["Titolo 2"],
            "Heading 3": ["Titolo 3"],
            "Heading 4": ["Titolo 4"],
            "Quote": ["Citazione"],
            "Normal": ["Normale"],
            "List Bullet": ["Elenco puntato"],
            "List Number": ["Elenco numerato"],
        }
        for variant in italian_map.get(style_name, []):
            try:
                return doc.styles[variant]
            except KeyError:
                continue
        # Tenta inverso (italiano → inglese)
        reverse_map = {
            "Titolo 1": "Heading 1",
            "Titolo 2": "Heading 2",
            "Titolo 3": "Heading 3",
            "Citazione": "Quote",
            "Normale": "Normal",
        }
        if style_name in reverse_map:
            try:
                return doc.styles[reverse_map[style_name]]
            except KeyError:
                pass
        # Fallback
        return doc.styles[fallback] if fallback in [s.name for s in doc.styles] else None


# =============================================================================
# UTILITY: APPLICAZIONE CONTENUTO
# =============================================================================

BLOCK_STYLE_MAP = {
    "heading1": "Heading 1",
    "heading2": "Heading 2",
    "heading3": "Heading 3",
    "heading4": "Heading 4",
    "paragraph": "Normal",
    "quote": "Quote",
    "list_item": "List Bullet",
    "list_number": "List Number",
    "title": "Title",
    "subtitle": "Subtitle",
}


def add_block(doc, block):
    """Aggiunge un blocco di contenuto al documento usando lo stile appropriato."""
    btype = block.get("type", "paragraph")

    if btype == "table":
        rows = block.get("rows", [])
        if not rows:
            return
        table = doc.add_table(rows=len(rows), cols=len(rows[0]))
        # Applica stile tabella se esiste nel documento
        try:
            table.style = doc.styles["Table Grid"]
        except KeyError:
            pass
        for i, row in enumerate(rows):
            for j, cell_text in enumerate(row):
                table.cell(i, j).text = str(cell_text)
        return

    style_name = BLOCK_STYLE_MAP.get(btype, "Normal")
    style = get_or_create_style(doc, style_name)

    text = block.get("text", "")
    para = doc.add_paragraph(text)
    if style is not None:
        try:
            para.style = style
        except Exception:
            pass  # se lo stile non esiste/non è applicabile, lascia default


# =============================================================================
# UTILITY: SOSTITUZIONE FONT GLOBALE
# =============================================================================

def replace_font_globally(doc, new_font_name):
    """Sostituisce il font in tutti gli stili e nei run espliciti del documento.
    Operazione invasiva: usare solo se l'utente ha esplicitamente scelto
    un font moderno diverso dall'originale."""
    if not new_font_name:
        return

    # 1. Aggiorna gli stili nominati
    for style in doc.styles:
        try:
            if hasattr(style, "font") and style.font is not None:
                style.font.name = new_font_name
                # Aggiorna anche eastAsia, hAnsi, cs in XML
                rPr = style.element.find(qn("w:rPr"))
                if rPr is not None:
                    rFonts = rPr.find(qn("w:rFonts"))
                    if rFonts is not None:
                        rFonts.set(qn("w:ascii"), new_font_name)
                        rFonts.set(qn("w:hAnsi"), new_font_name)
                        rFonts.set(qn("w:cs"), new_font_name)
                        rFonts.set(qn("w:eastAsia"), new_font_name)
        except Exception:
            continue

    # 2. Aggiorna run espliciti nel body
    for para in doc.paragraphs:
        for run in para.runs:
            if run.font.name:
                run.font.name = new_font_name
            rPr = run._element.find(qn("w:rPr"))
            if rPr is not None:
                rFonts = rPr.find(qn("w:rFonts"))
                if rFonts is not None:
                    rFonts.set(qn("w:ascii"), new_font_name)
                    rFonts.set(qn("w:hAnsi"), new_font_name)
                    rFonts.set(qn("w:cs"), new_font_name)
                    rFonts.set(qn("w:eastAsia"), new_font_name)

    # 3. Aggiorna run nelle tabelle
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.font.name:
                            run.font.name = new_font_name

    # 4. Aggiorna run negli header e footer
    for section in doc.sections:
        for hdr_ftr in [section.header, section.footer,
                        section.first_page_header, section.first_page_footer,
                        section.even_page_header, section.even_page_footer]:
            if hdr_ftr is None:
                continue
            for para in hdr_ftr.paragraphs:
                for run in para.runs:
                    if run.font.name:
                        run.font.name = new_font_name


# =============================================================================
# UTILITY: SOSTITUZIONE TESTO IN HEADER/FOOTER
# =============================================================================

def replace_in_header_footer(section_part, replacements):
    """Esegue find&replace nel testo dei paragrafi di header o footer.
    Preserva la formattazione del run."""
    if section_part is None or not replacements:
        return
    for para in section_part.paragraphs:
        # Approccio cumulativo: ricostruisce il testo del paragrafo a partire dai run
        full_text = "".join(run.text for run in para.runs)
        new_text = full_text
        for old, new in replacements.items():
            new_text = new_text.replace(old, new)
        if new_text != full_text and para.runs:
            # Inserisce il testo modificato nel primo run e svuota gli altri
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ""


def update_headers_footers(doc, header_replacements=None, footer_replacements=None):
    """Aggiorna il testo di tutti gli header e footer del documento."""
    for section in doc.sections:
        if header_replacements:
            replace_in_header_footer(section.header, header_replacements)
            try:
                replace_in_header_footer(section.first_page_header, header_replacements)
            except Exception:
                pass
            try:
                replace_in_header_footer(section.even_page_header, header_replacements)
            except Exception:
                pass
        if footer_replacements:
            replace_in_header_footer(section.footer, footer_replacements)
            try:
                replace_in_header_footer(section.first_page_footer, footer_replacements)
            except Exception:
                pass
            try:
                replace_in_header_footer(section.even_page_footer, footer_replacements)
            except Exception:
                pass


# =============================================================================
# UTILITY: SOSTITUZIONE SEGNAPOSTO NEL BODY
# =============================================================================

def replace_placeholders_in_body(doc, placeholders):
    """Sostituisce segnaposto nel body. Da chiamare dopo l'inserimento del contenuto."""
    if not placeholders:
        return
    for para in doc.paragraphs:
        full_text = "".join(run.text for run in para.runs)
        new_text = full_text
        for old, new in placeholders.items():
            new_text = new_text.replace(old, new)
        if new_text != full_text and para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ""


# =============================================================================
# RIMOZIONE COMMENTI E REVISIONI
# =============================================================================

def clean_comments_and_revisions(doc):
    """Rimuove commenti e revisioni dal documento finale."""
    body = doc.element.body
    # Rimuovi commentRangeStart, commentRangeEnd, commentReference
    for tag in ["w:commentRangeStart", "w:commentRangeEnd", "w:commentReference"]:
        for el in body.iter(qn(tag)):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
    # Accetta tutte le revisioni: rimuove ins/del e mantiene il contenuto
    for ins in list(body.iter(qn("w:ins"))):
        parent = ins.getparent()
        if parent is not None:
            for child in list(ins):
                ins.addprevious(child)
            parent.remove(ins)
    for del_el in list(body.iter(qn("w:del"))):
        parent = del_el.getparent()
        if parent is not None:
            parent.remove(del_el)


# =============================================================================
# MAIN
# =============================================================================

def clone(reference_path, content, output_path,
          new_font=None,
          header_replacements=None,
          footer_replacements=None,
          placeholders=None):
    """Funzione principale di clonazione."""
    ref = Path(reference_path)
    out = Path(output_path)

    if not ref.exists():
        raise FileNotFoundError(f"File di riferimento non trovato: {reference_path}")
    if ref.suffix.lower() != ".docx":
        raise ValueError(f"Formato non supportato: {ref.suffix}. Atteso: .docx")

    # 1. Copia fisica
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(ref), str(out))

    # 2. Apertura
    doc = Document(str(out))

    # 3. Rimuovi body content (preservando sectPr)
    sectPr = remove_body_content(doc)

    # 4. Pulisci commenti e revisioni
    clean_comments_and_revisions(doc)

    # 5. Inserisci nuovo contenuto
    if isinstance(content, dict):
        blocks = content.get("blocks", [])
    elif isinstance(content, list):
        blocks = content
    else:
        # Stringa: la trattiamo come singolo paragrafo
        blocks = [{"type": "paragraph", "text": str(content)}]

    for block in blocks:
        add_block(doc, block)

    # 6. Reinserisci sectPr alla fine del body se presente
    if sectPr is not None:
        body = doc.element.body
        # rimuovi eventuale sectPr già presente (potrebbe essere rimasto)
        existing = body.find(qn("w:sectPr"))
        if existing is not None:
            body.remove(existing)
        body.append(sectPr)

    # 7. Sostituzioni globali font (opzionale)
    if new_font:
        replace_font_globally(doc, new_font)

    # 8. Aggiornamento header/footer (opzionale)
    if header_replacements or footer_replacements:
        update_headers_footers(doc, header_replacements, footer_replacements)

    # 9. Sostituzione segnaposto nel body (opzionale)
    if placeholders:
        replace_placeholders_in_body(doc, placeholders)

    # 10. Salvataggio
    doc.save(str(out))
    return str(out)


def main():
    parser = argparse.ArgumentParser(description="Clona stile editoriale di un .docx")
    parser.add_argument("--reference", required=True, help="Path al .docx di riferimento")
    parser.add_argument("--content", required=True,
                        help="Path a content.json con i blocchi del nuovo contenuto, "
                             "oppure stringa di testo da inserire come paragrafo unico")
    parser.add_argument("--output", required=True, help="Path al file .docx di output")
    parser.add_argument("--font", default=None,
                        help="Font moderno da applicare globalmente (sovrascrive l'originale)")
    parser.add_argument("--header-replacements", default=None,
                        help='JSON di sostituzioni nel testo dell\'header, es: \'{"vecchio":"nuovo"}\'')
    parser.add_argument("--footer-replacements", default=None,
                        help='JSON di sostituzioni nel testo del footer')
    parser.add_argument("--placeholders", default=None,
                        help='JSON di sostituzioni segnaposto nel body, es: \'{"[DATA]":"26/04/2026"}\'')

    args = parser.parse_args()

    # Carica il content
    content_path = Path(args.content)
    if content_path.exists() and content_path.suffix.lower() == ".json":
        with open(content_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    else:
        # Trattalo come stringa di testo
        content = args.content

    header_repl = json.loads(args.header_replacements) if args.header_replacements else None
    footer_repl = json.loads(args.footer_replacements) if args.footer_replacements else None
    placeholders = json.loads(args.placeholders) if args.placeholders else None

    output = clone(
        reference_path=args.reference,
        content=content,
        output_path=args.output,
        new_font=args.font,
        header_replacements=header_repl,
        footer_replacements=footer_repl,
        placeholders=placeholders,
    )
    print(f"OK: documento generato in {output}")


if __name__ == "__main__":
    main()
