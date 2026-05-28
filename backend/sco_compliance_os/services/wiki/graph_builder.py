"""Graph builder vault SCO — costruisce grafo navigabile entity + clienti + body wikilinks.

Produce nodi + edges per visualizzazione force-directed 2D (frontend
react-force-graph-2d). Walk completo del vault, lettura YAML frontmatter
via parse_vault_file esistente (Conv. 47 single source of truth: schema
del parser tipizzato services/vault/parser.py).

Nodi (estesi v0.12.1 Phase 2):
    - entity wiki (wiki/entities/*.md) tipizzate (entity_type, subtype,
      ambito_canonico, status)
    - clienti business (Business/*/clienti/*/_index.md) con ruolo
      cliente nel grafo
    - scadenze (entity_type=scadenza con parent_entity)
    - note generiche (qualsiasi .md del vault con wikilink nel body) ->
      categoria 'note'
    - placeholder per wikilink target inesistenti (status: missing) ->
      categoria 'missing'

Edges (estesi v0.12.1 Phase 2):
    - relationships fra entity (Dimensione 4 Ondata 3): recepisce, attua,
      abroga, modifica, supersedes, correlato-a, richiama, vigilato-da
      -> category='relationship'
    - applica_entity cliente -> entity (Dimensione 5 Ondata 3) con ruolo
      come label/type dell'arco -> category='applica'
    - wikilink nel body markdown qualunque file -> category='wikilink',
      type='menzione'

Edge case coperti:
    - regex wikilink: `[[wiki/entities/slug]]` o `[[slug]]` con alias `|...`
    - slug nodo cliente sicuro (lowercase + dash, no spazi/accenti) via
      stem path + prefix "cliente-" per disambiguazione
    - wikilink dentro fenced code block ``` ... ``` ESCLUSI (false positive
      su esempi di codice)
    - wikilink dentro inline code ` ... ` ESCLUSI
    - wikilink nel frontmatter YAML ESCLUSI (già parsati come relationships
      strutturate dal parser)
    - target wikilink che non esiste come nodo concreto -> emette
      placeholder con status "missing" + category "missing"
    - giornalieri (Giornaliero/YYYY-MM/YYYY-MM-DD.md) parsati come 'note'

Cartelle escluse dal walk body:
    - .git/, node_modules/, _archivio*/, .obsidian/, .claude/

Pattern Karpathy "schema is the product": il graph builder mantiene il
frontmatter strutturato come SSOT per relationships/applica_entity, e
aggiunge wikilink body come dimensione DENSITY complementare. Niente
inferenza semantica, solo regex testuale.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from sco_compliance_os.services.vault.parser import (
    VaultDocument,
    parse_vault_file,
)

logger = logging.getLogger(__name__)

# Regex wikilink: `[[wiki/entities/slug]]` o `[[Path/Cliente]]` o `[[slug|alias]]`.
# Cattura: gruppo 1 = path/slug completo, gruppo 2 = alias opzionale (scartato).
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]")

# Pattern per estrarre slug finale da wikilink target.
_SLUG_SAFE_RE = re.compile(r"[a-z0-9._-]+")

# Cartelle escluse dal walk body wikilink (rumore, non contenuto vault).
_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        ".obsidian",
        ".claude",
        ".vscode",
        ".idea",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "target",
    }
)

# Pattern prefix per cartelle _archivio (multi-variant).
_ARCHIVIO_PREFIX = "_archivio"


def _is_excluded_path(rel_path: Path) -> bool:
    """True se rel_path attraversa cartelle escluse dal walk wikilink body."""
    parts = rel_path.parts
    for part in parts:
        if part in _EXCLUDED_DIRS:
            return True
        # _archivio, _archivio_backup_*, _archivio_2024, etc.
        if part.lower().startswith(_ARCHIVIO_PREFIX):
            return True
    return False


def _strip_code_blocks(body: str) -> str:
    """Rimuove fenced code block triple backtick + inline code single backtick.

    Pattern: non vogliamo che `[[esempio]]` in un blocco codice diventi un edge
    del grafo. Strip distruttivo solo per il pass di wikilink parsing — il
    body originale resta nel doc.

    Ordine operazioni (importante):
    1. Strip fenced ``` ... ``` block (multi-line)
    2. Strip inline ` ... ` (single-line)
    """
    # Strip fenced code blocks (greedy non-greedy, single or triple backtick fence).
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    # Anche fence ~~~ se mai usata.
    body = re.sub(r"~~~.*?~~~", "", body, flags=re.DOTALL)
    # Strip inline code single backtick.
    body = re.sub(r"`[^`\n]+`", "", body)
    return body


def _slug_from_path(path: Path) -> str:
    """Normalizza filename in slug ASCII-safe."""
    return path.stem


def _cliente_id_from_path(path: Path) -> str:
    """Genera ID nodo cliente da path _index.md.

    Pattern: cliente-<slug-normalizzato> per evitare collisioni con
    slug entity wiki. Lowercase + dash, no accenti, no spazi.
    """
    parent_name = path.parent.name
    normalized = parent_name.lower().replace("_", "-").replace(" ", "-")
    normalized = re.sub(r"[^a-z0-9.-]", "", normalized)
    if not normalized:
        normalized = "unknown"
    return f"cliente-{normalized}"


def _normalize_segment_slug(segment: str) -> str:
    """Normalizza un singolo path segment in slug ASCII-safe."""
    normalized = segment.lower().replace("_", "-").replace(" ", "-")
    normalized = re.sub(r"[^a-z0-9.-]", "", normalized)
    return normalized


def _note_id_from_path(path: Path, vault_root: Path) -> str:
    """Genera ID stabile per nodo 'note' generico (file .md non entity/cliente).

    Pattern: usa path relativo per disambiguare omonimie (es. due _index.md
    in cartelle diverse hanno ID diversi).
    """
    try:
        rel = path.relative_to(vault_root)
    except ValueError:
        rel = path

    # Componi slug da rel path: lowercase + replace separator + strip .md.
    stem = rel.with_suffix("").as_posix().lower()
    # Sostituisce path separator con dash.
    stem = stem.replace("/", "-").replace("\\", "-")
    stem = stem.replace("_", "-").replace(" ", "-")
    stem = re.sub(r"[^a-z0-9.-]", "", stem)
    if not stem:
        stem = path.stem.lower()
    return f"note-{stem}"


def _extract_target_slug(wikilink_target: str) -> str:
    """Estrae slug finale da wikilink target arbitrario.

    Esempi:
        [[wiki/entities/d-lgs-138-2024]] -> d-lgs-138-2024
        wiki/entities/d-lgs-138-2024 -> d-lgs-138-2024
        d-lgs-138-2024 -> d-lgs-138-2024
        [[Business/CSQA-SIET/clienti/Don_Calabria_Negrar]] -> cliente-don-calabria-negrar
        Business/CSQA-SIET/clienti/Don_Calabria_Negrar/_index -> cliente-don-calabria-negrar
        [[slug|alias]] -> slug
        [[Giornaliero/2026-05/2026-05-25]] -> note-giornaliero-2026-05-2026-05-25
    """
    target = wikilink_target.strip()
    # Strip wikilink delimiters [[ e ]].
    if target.startswith("[["):
        target = target[2:]
    if target.endswith("]]"):
        target = target[:-2]
    # Strip alias "|alias" finale.
    if "|" in target:
        target = target.split("|", 1)[0]
    target = target.strip()

    # Cliente: contiene Business/.../clienti/<nome>
    lower = target.lower().replace("\\", "/")
    if "business/" in lower and "/clienti/" in lower:
        parts = target.replace("\\", "/").split("/")
        idx = -1
        for i, part in enumerate(parts):
            if part.lower() == "clienti":
                idx = i
                break
        if idx != -1 and idx + 1 < len(parts):
            cliente_name = parts[idx + 1]
            normalized = _normalize_segment_slug(cliente_name)
            if normalized:
                return f"cliente-{normalized}"

    # Default: ultimo segmento del path = slug.
    last_segment = target.replace("\\", "/").rstrip("/").split("/")[-1]
    if last_segment.endswith(".md"):
        last_segment = last_segment[:-3]
    return last_segment.strip()


def _resolve_wikilink_to_node_id(
    wikilink_target: str,
    nodes_by_id: dict[str, dict[str, Any]],
    note_paths: dict[str, str],
    vault_root: Path,
) -> str | None:
    """Risolve wikilink target -> node ID (esistente o nuovo).

    Strategy:
    1. Estrai slug "naive" da target.
    2. Se slug è già nodes_by_id -> ritorna slug (match entity/cliente/scadenza).
    3. Se slug è in note_paths -> ritorna note-id.
    4. Se path-like (contiene /), prova a costruire note-id basato su path.
    5. Altrimenti ritorna slug naive (placeholder se non esiste, creato dopo).
    """
    naive_slug = _extract_target_slug(wikilink_target)
    if not naive_slug:
        return None

    # Match diretto: entity/cliente/scadenza/note già esistente.
    if naive_slug in nodes_by_id:
        return naive_slug

    # Match nodi note esistenti (path lookup).
    target_clean = wikilink_target.strip()
    if target_clean.startswith("[["):
        target_clean = target_clean[2:]
    if target_clean.endswith("]]"):
        target_clean = target_clean[:-2]
    if "|" in target_clean:
        target_clean = target_clean.split("|", 1)[0]
    target_clean = target_clean.strip()
    if target_clean.endswith(".md"):
        target_clean = target_clean[:-3]

    # Match path-based per nodi note.
    # Esempio: target_clean = "Giornaliero/2026-05/2026-05-25"
    # Lookup case-insensitive nel dict note_paths.
    target_norm = target_clean.replace("\\", "/").lower()
    if target_norm in note_paths:
        return note_paths[target_norm]

    return naive_slug


def _entity_to_node(doc: VaultDocument, slug: str, vault_root: Path) -> dict[str, Any]:
    """Serializza entity wiki come nodo grafo."""
    return {
        "id": slug,
        "label": doc.title or slug,
        "category": "entity",
        "entity_type": doc.entity_type or "",
        "entity_subtype": doc.entity_subtype or "",
        "ambito_canonico": doc.ambito_canonico or "",
        "status": doc.status or "active",
        "path": str(Path(doc.path).relative_to(vault_root))
        if vault_root in Path(doc.path).parents
        else doc.path,
    }


def _cliente_to_node(doc: VaultDocument, cliente_id: str, vault_root: Path) -> dict[str, Any]:
    """Serializza cliente business come nodo grafo."""
    category = "scadenza" if doc.entity_type == "scadenza" else "cliente"
    return {
        "id": cliente_id,
        "label": doc.title or cliente_id,
        "category": category,
        "entity_type": doc.entity_type or "",
        "entity_subtype": doc.entity_subtype or "",
        "ambito_canonico": doc.ambito_canonico or "",
        "status": doc.status or "active",
        "path": str(Path(doc.path).relative_to(vault_root))
        if vault_root in Path(doc.path).parents
        else doc.path,
    }


def _note_to_node(
    path: Path,
    note_id: str,
    vault_root: Path,
    doc: VaultDocument | None = None,
) -> dict[str, Any]:
    """Serializza file .md generico come nodo 'note'.

    Pattern: file .md che non sono entity/cliente/scadenza/source/concept/synthesis
    ma hanno wikilink nel body -> nodo categoria 'note' (grigio chiaro nel
    grafo, distinto da missing).
    """
    label = path.stem
    if doc and doc.title:
        label = doc.title
    try:
        rel_path = str(path.relative_to(vault_root))
    except ValueError:
        rel_path = str(path)
    return {
        "id": note_id,
        "label": label,
        "category": "note",
        "entity_type": "",
        "entity_subtype": "",
        "ambito_canonico": "",
        "status": "active",
        "path": rel_path,
    }


def _placeholder_node(slug: str) -> dict[str, Any]:
    """Crea nodo placeholder per wikilink target inesistente.

    Pattern Karpathy: visualizza gap conoscitivo. Frontend usa
    category='missing' per rendering grigio molto chiaro.
    """
    return {
        "id": slug,
        "label": slug,
        "category": "missing",
        "entity_type": "",
        "entity_subtype": "",
        "ambito_canonico": "",
        "status": "missing",
        "path": "",
    }


def _walk_body_wikilinks(
    vault_root: Path,
    nodes_by_id: dict[str, dict[str, Any]],
    note_paths: dict[str, str],
    *,
    include_notes: bool,
) -> tuple[list[dict[str, Any]], int]:
    """Walk completo vault per estrarre wikilink dal body markdown.

    Args:
        vault_root: root vault.
        nodes_by_id: dict nodi già emessi (entity/cliente/scadenza). Mutato:
            aggiungerà nodi 'note' e 'missing' on-demand.
        note_paths: dict path normalizzato (lower, posix) -> note_id. Mutato.
        include_notes: se True, emette nodi 'note' per file .md generici
            che hanno wikilink. Se False, emette solo gli edge ma droppa
            il nodo sorgente generico (mantiene solo entity/cliente come hub).

    Returns:
        tupla (lista edges body wikilink, stats: edges_emessi).

    Pattern: per ogni file .md vault (escluse dir nelle blacklist), estrai
    body markdown, strip code blocks, applica regex wikilink, emetti edge
    `{source: <file_node_id>, target: <wikilink_node_id>, category: 'wikilink'}`.

    Edge case:
        - File con wikilink ma sé stesso non è entity/cliente -> diventa
          nodo 'note' SE include_notes=True
        - Target wikilink che non corrisponde a nessun nodo -> resta come
          slug stringa, viene risolto a placeholder 'missing' in fase 4
    """
    edges_body: list[dict[str, Any]] = []
    edges_count = 0

    # Pass 1: censire tutti i file .md del vault (escluse dir blacklist) per
    # popolare note_paths (lookup case-insensitive per wikilink target match).
    md_files: list[Path] = []
    for md_path in vault_root.rglob("*.md"):
        try:
            rel = md_path.relative_to(vault_root)
        except ValueError:
            continue
        if _is_excluded_path(rel):
            continue
        md_files.append(md_path)

    # Pre-popola note_paths per i file NON già nodi entity/cliente/scadenza.
    for md_path in md_files:
        try:
            rel = md_path.relative_to(vault_root)
        except ValueError:
            continue
        rel_norm = rel.with_suffix("").as_posix().lower()

        # Skip se è già un nodo entity/cliente/scadenza censito.
        # Test 1: filename stem corrisponde a un nodo entity esistente?
        stem = md_path.stem.lower()
        if stem in nodes_by_id:
            # È già censito come entity. Mappa anche il path completo
            # al medesimo node id (per matching wikilink path-based).
            note_paths[rel_norm] = stem
            continue

        # Test 2: è un _index.md cliente?
        # Genera cliente_id e verifica se è già nei nodes.
        if md_path.name == "_index.md":
            potential_cliente_id = _cliente_id_from_path(md_path)
            if potential_cliente_id in nodes_by_id:
                note_paths[rel_norm] = potential_cliente_id
                continue

        # Altrimenti, è un file note generico: pre-alloca note_id per matching.
        note_id = _note_id_from_path(md_path, vault_root)
        note_paths[rel_norm] = note_id
        # Mappa anche solo lo stem (es. "2026-05-25") per matching short-form
        # wikilink che non includono il path completo.
        # Solo se non collide con un nodo entity esistente.
        if stem and stem not in note_paths:
            note_paths[stem] = note_id

    # Pass 2: walk + extract wikilink dal body.
    for md_path in md_files:
        try:
            rel = md_path.relative_to(vault_root)
        except ValueError:
            continue

        # Determina il source node ID di questo file.
        stem = md_path.stem.lower()
        source_node_id: str | None = None

        if stem in nodes_by_id:
            source_node_id = stem
        elif md_path.name == "_index.md":
            potential_cliente_id = _cliente_id_from_path(md_path)
            if potential_cliente_id in nodes_by_id:
                source_node_id = potential_cliente_id

        if source_node_id is None:
            # File note generico.
            if not include_notes:
                # Salta il file: non emettiamo edge se include_notes=False
                # e il file non è entity/cliente.
                continue
            note_id = _note_id_from_path(md_path, vault_root)
            source_node_id = note_id

        # Leggi body.
        try:
            content = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning(
                "graph_builder.read_md_failed",
                extra={"path": str(md_path), "error": str(exc)},
            )
            continue

        # Strip frontmatter.
        if content.startswith("---"):
            match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)$", content, re.DOTALL)
            if match:
                body = match.group(1)
            else:
                body = content
        else:
            body = content

        # Strip code blocks (fenced + inline).
        body_clean = _strip_code_blocks(body)

        # Estrai wikilink.
        wikilinks_in_body = set()
        for match in _WIKILINK_RE.finditer(body_clean):
            target_raw = match.group(1).strip()
            if not target_raw:
                continue
            wikilinks_in_body.add(target_raw)

        # Per ogni wikilink unico nel body, emetti edge.
        for wikilink_target in wikilinks_in_body:
            target_id = _resolve_wikilink_to_node_id(
                wikilink_target,
                nodes_by_id,
                note_paths,
                vault_root,
            )
            if not target_id:
                continue
            # Self-edge: skip (a -> a non aggiunge valore al grafo).
            if target_id == source_node_id:
                continue
            # Se source_node_id è un note non ancora in nodes_by_id, crealo.
            if source_node_id not in nodes_by_id:
                # Source è un file note che dobbiamo materializzare.
                try:
                    src_doc = parse_vault_file(md_path)
                except Exception:
                    src_doc = None
                nodes_by_id[source_node_id] = _note_to_node(
                    md_path, source_node_id, vault_root, src_doc
                )

            edges_body.append(
                {
                    "source": source_node_id,
                    "target": target_id,
                    "type": "menzione",
                    "category": "wikilink",
                    "note": "",
                }
            )
            edges_count += 1

    return edges_body, edges_count


def build_vault_graph(
    vault_root: Path,
    *,
    include_clienti: bool = True,
    include_orphans: bool = True,
    include_body_wikilinks: bool = True,
    include_notes: bool = True,
    entity_type_filter: str | None = None,
    ambito_canonico_filter: str | None = None,
) -> dict[str, Any]:
    """Costruisce grafo del vault SCO: nodi + edges + stats.

    Args:
        vault_root: path radice vault (deve esistere ed essere directory).
        include_clienti: includi nodi cliente da Business/*/clienti/*/_index.md.
        include_orphans: includi nodi placeholder per wikilink target inesistenti.
        include_body_wikilinks: parsa wikilink nel body markdown di tutti i file
            .md del vault (Phase 2 v0.12.1, fix grafo Obsidian-density).
            Default True per ottenere densità simile a Obsidian Graph View.
        include_notes: emetti nodi categoria 'note' per file .md generici
            (non entity/cliente/scadenza) che hanno wikilink nel body.
            Richiede include_body_wikilinks=True per avere effetto.
        entity_type_filter: filtra entity per entity_type (None = tutte).
        ambito_canonico_filter: filtra entity per ambito_canonico (None = tutte).

    Returns:
        dict shape stabile:
            {
                "nodes": [...],
                "edges": [...],
                "stats": {
                    "nodes_total": int,
                    "edges_total": int,
                    "by_entity_type": {<type>: int},
                    "by_ambito_canonico": {<ambito>: int},
                    "by_relationship_type": {<tipo>: int},
                    "by_category": {<entity|cliente|scadenza|note|missing>: int},
                    "by_edge_category": {<relationship|applica|wikilink>: int},
                },
                "vault_path": str
            }
    """
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    by_entity_type: dict[str, int] = {}
    by_ambito_canonico: dict[str, int] = {}
    by_relationship_type: dict[str, int] = {}

    wiki_entities_dir = vault_root / "wiki" / "entities"

    # ---- Fase 1: walk entity wiki ----
    if wiki_entities_dir.exists() and wiki_entities_dir.is_dir():
        for md_path in wiki_entities_dir.glob("*.md"):
            if md_path.name == "_index.md":
                continue
            try:
                doc = parse_vault_file(md_path)
            except Exception as exc:
                logger.warning(
                    "graph_builder.parse_entity_failed",
                    extra={"path": str(md_path), "error": str(exc)},
                )
                continue

            # Filtri opzionali.
            if entity_type_filter and doc.entity_type != entity_type_filter:
                continue
            if ambito_canonico_filter and doc.ambito_canonico != ambito_canonico_filter:
                continue

            slug = _slug_from_path(md_path)
            node = _entity_to_node(doc, slug, vault_root)
            nodes_by_id[slug] = node

            etype = doc.entity_type or "unknown"
            by_entity_type[etype] = by_entity_type.get(etype, 0) + 1
            ambito = doc.ambito_canonico or "unknown"
            by_ambito_canonico[ambito] = by_ambito_canonico.get(ambito, 0) + 1

            # Relationships (edge entity -> entity, category='relationship').
            for rel in doc.relationships:
                target_slug = _extract_target_slug(rel.target)
                if not target_slug:
                    continue
                edges.append(
                    {
                        "source": slug,
                        "target": target_slug,
                        "type": rel.tipo,
                        "category": "relationship",
                        "note": rel.note,
                    }
                )
                by_relationship_type[rel.tipo] = by_relationship_type.get(rel.tipo, 0) + 1

    # ---- Fase 2: walk wiki/scadenze/ se presente come dir separata ----
    wiki_scadenze_dir = vault_root / "wiki" / "scadenze"
    if wiki_scadenze_dir.exists() and wiki_scadenze_dir.is_dir():
        for md_path in wiki_scadenze_dir.glob("*.md"):
            if md_path.name == "_index.md":
                continue
            try:
                doc = parse_vault_file(md_path)
            except Exception as exc:
                logger.warning(
                    "graph_builder.parse_scadenza_failed",
                    extra={"path": str(md_path), "error": str(exc)},
                )
                continue
            slug = _slug_from_path(md_path)
            if slug in nodes_by_id:
                continue
            node = _entity_to_node(doc, slug, vault_root)
            # Force category scadenza.
            node["category"] = "scadenza"
            nodes_by_id[slug] = node
            etype = "scadenza"
            by_entity_type[etype] = by_entity_type.get(etype, 0) + 1

    # ---- Fase 3: walk clienti business (opzionale) ----
    if include_clienti:
        business_dir = vault_root / "Business"
        if business_dir.exists() and business_dir.is_dir():
            for index_md in business_dir.rglob("_index.md"):
                parts = list(index_md.relative_to(business_dir).parts)
                if len(parts) < 4:
                    continue
                if parts[1].lower() != "clienti":
                    continue

                try:
                    doc = parse_vault_file(index_md)
                except Exception as exc:
                    logger.warning(
                        "graph_builder.parse_cliente_failed",
                        extra={"path": str(index_md), "error": str(exc)},
                    )
                    continue

                if (
                    ambito_canonico_filter
                    and doc.ambito_canonico
                    and doc.ambito_canonico != ambito_canonico_filter
                ):
                    continue

                cliente_id = _cliente_id_from_path(index_md)
                node = _cliente_to_node(doc, cliente_id, vault_root)
                if cliente_id not in nodes_by_id:
                    nodes_by_id[cliente_id] = node

                # Edge applica_entity cliente -> entity (Dim. 5, category='applica').
                for app in doc.applica_entity:
                    target_slug = _extract_target_slug(app.entity)
                    if not target_slug:
                        continue
                    edges.append(
                        {
                            "source": cliente_id,
                            "target": target_slug,
                            "type": app.ruolo,
                            "category": "applica",
                            "note": app.note,
                        }
                    )

    # ---- Fase 4: body wikilink parsing (Phase 2 v0.12.1) ----
    # Walk completo vault per estrarre wikilink dal body markdown.
    # Emette nodi 'note' generici + edge categoria 'wikilink'.
    note_paths: dict[str, str] = {}
    if include_body_wikilinks:
        body_edges, _body_edges_count = _walk_body_wikilinks(
            vault_root,
            nodes_by_id,
            note_paths,
            include_notes=include_notes,
        )
        edges.extend(body_edges)

    # ---- Fase 5: orphan handling ----
    # Wikilink target che non corrispondono a nodi concreti -> placeholder.
    if include_orphans:
        target_ids_needed: set[str] = {e["target"] for e in edges}
        for target_id in target_ids_needed:
            if target_id not in nodes_by_id:
                nodes_by_id[target_id] = _placeholder_node(target_id)
    else:
        edges = [e for e in edges if e["target"] in nodes_by_id]

    nodes = list(nodes_by_id.values())

    # Stats by_category + by_edge_category.
    by_category: dict[str, int] = {}
    for n in nodes:
        cat = n.get("category", "entity")
        by_category[cat] = by_category.get(cat, 0) + 1

    by_edge_category: dict[str, int] = {}
    for e in edges:
        cat = e.get("category", "relationship")
        by_edge_category[cat] = by_edge_category.get(cat, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodes_total": len(nodes),
            "edges_total": len(edges),
            "by_entity_type": by_entity_type,
            "by_ambito_canonico": by_ambito_canonico,
            "by_relationship_type": by_relationship_type,
            "by_category": by_category,
            "by_edge_category": by_edge_category,
        },
        "vault_path": str(vault_root),
    }
