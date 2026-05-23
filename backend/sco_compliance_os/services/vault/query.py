"""Query layer cross-cliente sul vault Karpathy.

Funzioni di interrogazione tipiche del lavoro consulenziale:
    - clients_applying_entity: chi applica una norma?
    - client_entities_by_role: per un cliente, quali entity ha con ruolo X?
    - pertinenze_in_verifica_open: cruscotto finding aperti (Conv. 30 Ondata 4)
    - suppliers_of: chi fornisce X (Dimensione 8 Ondata 4)
    - entities_by_ambito: cataloga entity per dominio normativo
    - entities_with_relationships: graph traversal relationships

Pattern Karpathy "single-source-of-truth": le query leggono SOLO dall'index
SQLite popolato da scanner.py, mai dal filesystem direttamente, per coerenza
performance + caching transparente.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import aiosqlite

from .parser import AppliedEntity, Relationship
from .scanner import default_db_path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClientHit:
    """Cliente che applica una specifica entity (per query reverse)."""

    path: str
    title: str
    ruolo: str
    note: str


@dataclass(slots=True)
class EntityHit:
    """Entity wiki risultato di query."""

    path: str
    title: str
    entity_type: str | None
    entity_subtype: str | None
    ambito_canonico: str | None
    status: str


@dataclass(slots=True)
class PertinenzaOpenHit:
    """Finding aperto pertinenza_in_verifica (cruscotto O.8)."""

    cliente_path: str
    cliente_title: str
    entity: str
    motivo: str
    data_ipotesi: str
    days_in_stasis: int


@dataclass(slots=True)
class SupplierHit:
    """Fornitore di un cliente (cruscotto O.9 reverse)."""

    supplier_path: str
    supplier_title: str
    tipo_servizio: str
    rilevanza_compliance: list[str]
    note: str


def _parse_entity_link(wikilink: str) -> str:
    """Normalizza wikilink in slug entity (es. [[wiki/entities/foo]] → 'foo')."""
    return wikilink.replace("[[", "").replace("]]", "").split("/")[-1].split("|")[0].strip()


async def clients_applying_entity(
    entity_slug: str,
    db_path: Path | None = None,
) -> list[ClientHit]:
    """Lista clienti che hanno entity_slug in applica_entity (Dimensione 5).

    Args:
        entity_slug: slug entity (es. 'd-lgs-138-2024') o wikilink completo.

    Returns:
        Lista ClientHit con cliente + ruolo + note dell'edge.
    """
    target_slug = _parse_entity_link(entity_slug)
    path = db_path or default_db_path()
    hits: list[ClientHit] = []

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT path, title, applica_entity FROM vault_documents WHERE type='cliente'"
        ) as cur:
            async for row in cur:
                edges = json.loads(row["applica_entity"])
                for edge in edges:
                    edge_slug = _parse_entity_link(edge.get("entity", ""))
                    if edge_slug == target_slug:
                        hits.append(
                            ClientHit(
                                path=row["path"],
                                title=row["title"],
                                ruolo=edge.get("ruolo", ""),
                                note=edge.get("note", ""),
                            )
                        )
    return hits


async def client_entities_by_role(
    client_path: str,
    ruolo: str | None = None,
    db_path: Path | None = None,
) -> list[AppliedEntity]:
    """Per un cliente, ritorna le applica_entity filtrate opzionalmente per ruolo."""
    path = db_path or default_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT applica_entity FROM vault_documents WHERE path = ?", (client_path,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return []
            edges_raw = json.loads(row["applica_entity"])

    out: list[AppliedEntity] = []
    for edge in edges_raw:
        if ruolo and edge.get("ruolo") != ruolo:
            continue
        out.append(
            AppliedEntity(
                entity=edge.get("entity", ""),
                ruolo=edge.get("ruolo", ""),
                note=edge.get("note", ""),
            )
        )
    return out


async def pertinenze_in_verifica_open(
    db_path: Path | None = None,
) -> list[PertinenzaOpenHit]:
    """Cruscotto finding aperti (Conv. 30 Ondata 4, cruscotto O.8).

    Ordina per days_in_stasis DESC (finding più vecchi in alto).
    """
    path = db_path or default_db_path()
    hits: list[PertinenzaOpenHit] = []
    today = date.today()

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT path, title, pertinenza_in_verifica FROM vault_documents WHERE type='cliente'"
        ) as cur:
            async for row in cur:
                pertinenze = json.loads(row["pertinenza_in_verifica"])
                for p in pertinenze:
                    data_str = p.get("data_ipotesi", "")
                    days = 0
                    if data_str:
                        try:
                            data_ip = datetime.fromisoformat(data_str).date()
                            days = (today - data_ip).days
                        except (ValueError, TypeError):
                            days = 0
                    hits.append(
                        PertinenzaOpenHit(
                            cliente_path=row["path"],
                            cliente_title=row["title"],
                            entity=p.get("entity", ""),
                            motivo=p.get("motivo", ""),
                            data_ipotesi=data_str,
                            days_in_stasis=days,
                        )
                    )
    hits.sort(key=lambda h: h.days_in_stasis, reverse=True)
    return hits


async def suppliers_of(
    client_path: str,
    db_path: Path | None = None,
) -> list[SupplierHit]:
    """Reverse query Dimensione 8: chi sono i fornitori del cliente X?

    Pattern asimmetrico Conv. 31 Ondata 4: l'edge vive lato fornitore in
    fornitore_di[]. La query inversa scansiona tutti i clienti e filtra
    quelli che dichiarano X come servito.
    """
    path = db_path or default_db_path()
    hits: list[SupplierHit] = []

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT path, title, fornitore_di FROM vault_documents "
            "WHERE type='cliente' AND fornitore_di != '[]'"
        ) as cur:
            async for row in cur:
                fdi = json.loads(row["fornitore_di"])
                for entry in fdi:
                    if entry.get("cliente", "").strip().lower() in client_path.lower():
                        hits.append(
                            SupplierHit(
                                supplier_path=row["path"],
                                supplier_title=row["title"],
                                tipo_servizio=entry.get("tipo_servizio", ""),
                                rilevanza_compliance=entry.get("rilevanza_compliance", []),
                                note=entry.get("note", ""),
                            )
                        )
    return hits


async def entities_by_ambito(
    ambito: str,
    db_path: Path | None = None,
) -> list[EntityHit]:
    """Lista entity wiki per ambito_canonico (es. 'cybersicurezza')."""
    path = db_path or default_db_path()
    hits: list[EntityHit] = []

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT path, title, entity_type, entity_subtype, ambito_canonico, status
               FROM vault_documents
               WHERE type='entity' AND ambito_canonico = ?
               ORDER BY title ASC""",
            (ambito,),
        ) as cur:
            async for row in cur:
                hits.append(
                    EntityHit(
                        path=row["path"],
                        title=row["title"],
                        entity_type=row["entity_type"],
                        entity_subtype=row["entity_subtype"],
                        ambito_canonico=row["ambito_canonico"],
                        status=row["status"],
                    )
                )
    return hits


async def entities_with_relationships(
    entity_slug: str,
    rel_type: str | None = None,
    db_path: Path | None = None,
) -> list[Relationship]:
    """Per un'entity, ritorna relationships eventualmente filtrate per tipo."""
    path = db_path or default_db_path()
    target_slug = _parse_entity_link(entity_slug)

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT relationships FROM vault_documents WHERE type='entity' AND path LIKE ?",
            (f"%{target_slug}%",),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return []
            rels_raw = json.loads(row["relationships"])

    out: list[Relationship] = []
    for r in rels_raw:
        if rel_type and r.get("tipo") != rel_type:
            continue
        out.append(
            Relationship(
                tipo=r.get("tipo", ""),
                target=r.get("target", ""),
                note=r.get("note", ""),
            )
        )
    return out
