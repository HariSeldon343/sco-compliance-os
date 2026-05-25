"""Graph builder vault SCO — costruisce grafo navigabile entity + clienti.

Produce nodi + edges per visualizzazione force-directed 2D (frontend
react-force-graph-2d). Walk completo del vault, lettura YAML frontmatter
via parse_vault_file esistente (Conv. 47 single source of truth: schema
del parser tipizzato services/vault/parser.py).

Nodi:
    - entity wiki (wiki/entities/*.md) tipizzate (entity_type, subtype,
      ambito_canonico, status)
    - clienti business (Business/*/clienti/*/_index.md) con ruolo
      cliente nel grafo
    - placeholder per wikilink target inesistenti (status: missing) ->
      rendering grafico evidenzia gap conoscitivo del vault

Edges:
    - relationships fra entity (Dimensione 4 Ondata 3): recepisce, attua,
      abroga, modifica, supersedes, correlato-a, richiama, vigilato-da
    - applica_entity cliente -> entity (Dimensione 5 Ondata 3) con ruolo
      come label/type dell'arco

Edge case coperti:
    - regex wikilink: `[[wiki/entities/slug]]` o `[[slug]]` con alias `|...`
    - slug nodo cliente sicuro (lowercase + dash, no spazi/accenti) via
      stem path + prefix "cliente-" per disambiguazione
    - target wikilink che non esiste come nodo concreto -> emette
      placeholder con status "missing"
    - YAML malformato (gestito da _parse_yaml_safe del parser): skip
      silenzioso con log warning, non blocca walk

Pattern Karpathy "no hallucination": il graph builder non inferisce
relationships dal body markdown (NO body wikilink parsing). Lavora solo
sul frontmatter strutturato. Phase 2 fuori MVP.
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
# Cattura: gruppo 1 = path/slug completo, alias (dopo |) viene scartato.
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")

# Pattern per estrarre slug finale da wikilink target.
# Supporta:
#   wiki/entities/d-lgs-138-2024 -> d-lgs-138-2024
#   Business/CSQA-SIET/clienti/Don_Calabria_Negrar -> uses entity_id mapping
#   solo-slug -> solo-slug (raw)
_SLUG_SAFE_RE = re.compile(r"[a-z0-9._-]+")


def _slug_from_path(path: Path) -> str:
    """Normalizza filename in slug ASCII-safe."""
    return path.stem


def _cliente_id_from_path(path: Path) -> str:
    """Genera ID nodo cliente da path _index.md.

    Pattern: cliente-<slug-normalizzato> per evitare collisioni con
    slug entity wiki. Lowercase + dash, no accenti, no spazi.
    """
    # Il filename e' "_index.md" — usa la cartella parent come nome cliente.
    parent_name = path.parent.name
    # Normalize: lowercase + replace spazi/underscore con dash + togli accenti basici.
    normalized = parent_name.lower().replace("_", "-").replace(" ", "-")
    # Strip caratteri non ASCII-safe (Apple/Italian accents et al).
    normalized = re.sub(r"[^a-z0-9.-]", "", normalized)
    if not normalized:
        normalized = "unknown"
    return f"cliente-{normalized}"


def _extract_target_slug(wikilink_target: str) -> str:
    """Estrae slug finale da wikilink target arbitrario.

    Esempi:
        [[wiki/entities/d-lgs-138-2024]] -> d-lgs-138-2024
        wiki/entities/d-lgs-138-2024 -> d-lgs-138-2024
        d-lgs-138-2024 -> d-lgs-138-2024
        [[Business/CSQA-SIET/clienti/Don_Calabria_Negrar]] -> cliente-don-calabria-negrar
        Business/CSQA-SIET/clienti/Don_Calabria_Negrar/_index -> cliente-don-calabria-negrar
        [[slug|alias]] -> slug
    """
    target = wikilink_target.strip()
    # Strip wikilink delimiters [[ e ]] (parser YAML li cattura come parte stringa).
    if target.startswith("[["):
        target = target[2:]
    if target.endswith("]]"):
        target = target[:-2]
    # Strip alias "|alias" finale.
    if "|" in target:
        target = target.split("|", 1)[0]
    target = target.strip()
    # Se inizia con "Business/" e contiene "/clienti/" -> nodo cliente.
    lower = target.lower().replace("\\", "/")
    if "business/" in lower and "/clienti/" in lower:
        # Estrai segmento dopo /clienti/ (skip eventuale /_index finale).
        # Esempio: "Business/CSQA-SIET/clienti/Don_Calabria_Negrar/_index"
        # -> segmenti[-1 oppure -2] a seconda della struttura.
        parts = target.replace("\\", "/").split("/")
        # Trova indice di "clienti" (case-insensitive).
        idx = -1
        for i, part in enumerate(parts):
            if part.lower() == "clienti":
                idx = i
                break
        if idx != -1 and idx + 1 < len(parts):
            cliente_name = parts[idx + 1]
            normalized = cliente_name.lower().replace("_", "-").replace(" ", "-")
            normalized = re.sub(r"[^a-z0-9.-]", "", normalized)
            if normalized:
                return f"cliente-{normalized}"
    # Default: ultimo segmento del path = slug.
    last_segment = target.replace("\\", "/").rstrip("/").split("/")[-1]
    # Strip eventuale .md.
    if last_segment.endswith(".md"):
        last_segment = last_segment[:-3]
    return last_segment.strip()


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


def _cliente_to_node(
    doc: VaultDocument, cliente_id: str, vault_root: Path
) -> dict[str, Any]:
    """Serializza cliente business come nodo grafo."""
    # Per categoria scadenza, usa entity_type=scadenza come marker.
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


def _placeholder_node(slug: str) -> dict[str, Any]:
    """Crea nodo placeholder per wikilink target inesistente.

    Pattern Karpathy: visualizza gap conoscitivo. Frontend usa
    status='missing' per rendering grigio/striped.
    """
    return {
        "id": slug,
        "label": slug,
        "category": "entity",
        "entity_type": "",
        "entity_subtype": "",
        "ambito_canonico": "",
        "status": "missing",
        "path": "",
    }


def build_vault_graph(
    vault_root: Path,
    *,
    include_clienti: bool = True,
    include_orphans: bool = True,
    entity_type_filter: str | None = None,
    ambito_canonico_filter: str | None = None,
) -> dict[str, Any]:
    """Costruisce grafo del vault SCO: nodi + edges + stats.

    Args:
        vault_root: path radice vault (deve esistere ed essere directory).
        include_clienti: includi nodi cliente da Business/*/clienti/*/_index.md.
        include_orphans: includi nodi placeholder per wikilink target inesistenti.
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

            # Stats.
            etype = doc.entity_type or "unknown"
            by_entity_type[etype] = by_entity_type.get(etype, 0) + 1
            ambito = doc.ambito_canonico or "unknown"
            by_ambito_canonico[ambito] = by_ambito_canonico.get(ambito, 0) + 1

            # Relationships (edge entity -> entity).
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

    # ---- Fase 2: walk clienti business (opzionale) ----
    if include_clienti:
        business_dir = vault_root / "Business"
        if business_dir.exists() and business_dir.is_dir():
            for index_md in business_dir.rglob("_index.md"):
                # Filtra solo i clienti (Business/<area>/clienti/<cliente>/_index.md).
                # Salta _index.md di area (Business/Consulenza/_index.md) e sops.
                parts = list(index_md.relative_to(business_dir).parts)
                # Pattern atteso: ['<area>', 'clienti', '<cliente>', '_index.md'].
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

                # Filtri opzionali (ambito_canonico applicabile anche ai clienti).
                if (
                    ambito_canonico_filter
                    and doc.ambito_canonico
                    and doc.ambito_canonico != ambito_canonico_filter
                ):
                    continue

                cliente_id = _cliente_id_from_path(index_md)
                node = _cliente_to_node(doc, cliente_id, vault_root)
                # Non sovrascrivere se collision improbabile con entity slug.
                if cliente_id not in nodes_by_id:
                    nodes_by_id[cliente_id] = node

                # Edge applica_entity cliente -> entity (Dimensione 5).
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

    # ---- Fase 3: orphan handling ----
    # Wikilink target che non corrispondono a nodi concreti -> placeholder
    # se include_orphans, altrimenti drop edge silente.
    if include_orphans:
        target_ids_needed: set[str] = {e["target"] for e in edges}
        for target_id in target_ids_needed:
            if target_id not in nodes_by_id:
                nodes_by_id[target_id] = _placeholder_node(target_id)
    else:
        # Drop edges con target inesistente.
        edges = [e for e in edges if e["target"] in nodes_by_id]

    nodes = list(nodes_by_id.values())

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodes_total": len(nodes),
            "edges_total": len(edges),
            "by_entity_type": by_entity_type,
            "by_ambito_canonico": by_ambito_canonico,
            "by_relationship_type": by_relationship_type,
        },
        "vault_path": str(vault_root),
    }
