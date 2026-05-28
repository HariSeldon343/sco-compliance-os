"""Vault scaffolder — crea struttura SCO completa per vault vuoti o nuovi.

v1.0.0 DEV-VAULT-SCAFFOLD-FRESH: gestisce il caso "vault path vuoto" o "crea
nuovo da template" del Vault Picker. Crea cartelle + file iniziali + entity
seed dipendenti dal template scelto.

5 template:
    - vuoto    : struttura minima (cartelle + _index.md placeholder)
    - cyber    : NIS 2 + ISO 27001 + Legge 90 + ACN + CSIRT-Italia (5 entity)
    - sanita   : accreditamento istituzionale + ISO 9001 sanita + D.Lgs. 81/2008 (5 entity)
    - qualita  : ISO 9001 generico per industria e servizi (3 entity)
    - integrato: cyber + sanita + qualita merged (entity seed di tutti e tre)

DEV-OPTIMIZER-AUTO (v1.0.0 stesso branch): aggiunto ``complete_missing_structure()``
per scaffold incrementale di vault esistenti che hanno struttura SCO INCOMPLETA
(es. cartella selezionata con solo CLAUDE.md ma senza wiki/raw/Contesto/...).
Riusato da POST /api/vault/{id}/complete-structure e proposto dalla skill
auto-trigger ``os-ottimizzatore`` quando vault.is_sco_structure=False.

Pattern Conv. 47 single source of truth: tutti i template vivono in questo
modulo (no duplicazione fra backend e frontend). Il frontend chiama
POST /api/vault/scaffold passando il template id, riceve files_created count.

Pattern Conv. 41 tracciatura: ogni file scritto loggato con path + size.

Pattern Conv. 39 three-layer SCO preservation: raw/ + wiki/ + CLAUDE.md +
Contesto/ + Giornaliero/ + Libreria/ + Skill/ + Team/ + Progetti/ rispettando
le 9 cartelle del vault SCO.

Idempotente: se vault path contiene gia un CLAUDE.md, ritorna
``{scaffolded: False, reason: "already_exists"}`` senza sovrascrivere nulla.
``complete_missing_structure()`` invece NON salta su CLAUDE.md esistente:
crea solo le cartelle/file MANCANTI lasciando intoccato il resto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from sco_compliance_os.core.logging_setup import get_logger

logger = get_logger(__name__)


TemplateKind = Literal["vuoto", "cyber", "sanita", "qualita", "integrato"]

VALID_TEMPLATES: tuple[TemplateKind, ...] = (
    "vuoto",
    "cyber",
    "sanita",
    "qualita",
    "integrato",
)


# ----- Struttura cartelle base SCO (9 cartelle del vault) -----


_BASE_DIRECTORIES: tuple[str, ...] = (
    "Contesto",
    "Business",
    "Giornaliero",
    "Libreria",
    "Skill",
    "Team",
    "Progetti",
    "wiki",
    "wiki/entities",
    "wiki/concepts",
    "wiki/sources",
    "wiki/synthesis",
    "wiki/glossari",
    "raw",
    "raw/normativa",
    "raw/linee-guida",
    "raw/audit",
    "raw/client-evidence",
    "log",
)


# ----- Template entity seed -----


@dataclass(frozen=True)
class EntitySeed:
    """Definizione entity seed per popolare wiki/entities/ in fase scaffold."""

    slug: str
    title: str
    entity_type: str
    entity_subtype: str | None
    ambito_canonico: str
    sintesi: str
    tags: tuple[str, ...]


_SEED_CYBER: tuple[EntitySeed, ...] = (
    EntitySeed(
        slug="d-lgs-138-2024",
        title="D.Lgs. 138/2024 — Recepimento NIS 2",
        entity_type="atto-normativo",
        entity_subtype="decreto-legislativo",
        ambito_canonico="cybersicurezza",
        sintesi=(
            "Decreto legislativo di recepimento della Direttiva (UE) 2022/2555 (NIS 2) "
            "nell'ordinamento italiano. Individua soggetti essenziali e importanti, "
            "obblighi di gestione del rischio, notifica incidenti significativi a "
            "CSIRT-Italia entro finestre temporali (24h pre-notifica, 72h notifica, "
            "1 mese relazione finale), registrazione su portale ACN. Vigilanza e "
            "sanzioni attribuite ad ACN come autorita nazionale competente NIS unica."
        ),
        tags=("entity", "atto-normativo", "nis2", "cybersicurezza"),
    ),
    EntitySeed(
        slug="iso-iec-27001-2022",
        title="ISO/IEC 27001:2022 — Sistema di gestione della sicurezza delle informazioni",
        entity_type="standard-tecnico",
        entity_subtype="iso-iec",
        ambito_canonico="cybersicurezza",
        sintesi=(
            "Standard internazionale per la progettazione, implementazione e "
            "manutenzione di un Sistema di Gestione della Sicurezza delle "
            "Informazioni (SGSI). Edizione 2022 in vigore, con Annex A a 93 "
            "controlli organizzati in 4 temi (organizzativi, persone, fisici, "
            "tecnologici). Certificabile da Organismo di Certificazione "
            "accreditato. Adottato come riferimento volontario in richiamo "
            "dell'Art. 24 del D.Lgs. 138/2024 e in molti capitolati di gara PA."
        ),
        tags=("entity", "standard-tecnico", "iso-iec", "cybersicurezza"),
    ),
    EntitySeed(
        slug="legge-90-2024",
        title="Legge 90/2024 — Disposizioni in materia di cybersicurezza",
        entity_type="atto-normativo",
        entity_subtype="legge-statale",
        ambito_canonico="cybersicurezza",
        sintesi=(
            "Legge che introduce il rafforzamento della cybersicurezza nazionale "
            "con focus su pubbliche amministrazioni, infrastrutture critiche e "
            "supply chain ICT verso la PA. Istituisce la figura del referente "
            "cybersicurezza nei soggetti pubblici (Art. 8) e regola i contratti "
            "ICT verso PA (Art. 14). Vigilanza primaria attribuita ad ACN."
        ),
        tags=("entity", "atto-normativo", "legge-statale", "cybersicurezza"),
    ),
    EntitySeed(
        slug="acn",
        title="ACN — Agenzia per la Cybersicurezza Nazionale",
        entity_type="autorita",
        entity_subtype="autorita-amministrativa",
        ambito_canonico="cybersicurezza",
        sintesi=(
            "Autorita nazionale di cybersicurezza istituita con D.L. 82/2021, "
            "competente per la strategia di sicurezza cibernetica e per il "
            "raccordo dei Computer Security Incident Response Team (CSIRT). "
            "Designata autorita nazionale competente NIS unica dal D.Lgs. "
            "138/2024 (NIS 2). Riceve notifiche di incidenti significativi via "
            "portale dedicato. Emette determinazioni di natura normativa con "
            "valore vincolante settoriale."
        ),
        tags=("entity", "autorita", "cybersicurezza"),
    ),
    EntitySeed(
        slug="csirt-italia",
        title="CSIRT-Italia — Computer Security Incident Response Team",
        entity_type="autorita",
        entity_subtype="organismo-operativo",
        ambito_canonico="cybersicurezza",
        sintesi=(
            "Organismo operativo nazionale per la risposta agli incidenti "
            "informatici. Riceve le notifiche di incidenti significativi NIS 2 "
            "(pre-notifica 24h, notifica 72h, relazione finale 1 mese). Opera "
            "in raccordo con ACN come autorita nazionale competente. Coordina "
            "lo scambio info con la rete europea ENISA-CSIRTs."
        ),
        tags=("entity", "autorita", "organismo-operativo", "cybersicurezza"),
    ),
)


_SEED_SANITA: tuple[EntitySeed, ...] = (
    EntitySeed(
        slug="dpr-14-gennaio-1997",
        title="DPR 14 gennaio 1997 — Requisiti strutturali, tecnologici e organizzativi minimi sanitari",
        entity_type="atto-normativo",
        entity_subtype="dpr",
        ambito_canonico="accreditamento-sanitario",
        sintesi=(
            "Decreto del Presidente della Repubblica che individua i requisiti "
            "minimi strutturali, tecnologici e organizzativi per l'esercizio "
            "delle attivita sanitarie da parte delle strutture pubbliche e "
            "private. Base normativa per l'accreditamento istituzionale "
            "regionale. Recepito e specificato da normativa regionale (es. "
            "D.A. Sicilia 741/2023 testo coordinato, Manuale MAO-SRO)."
        ),
        tags=("entity", "atto-normativo", "dpr", "accreditamento-sanitario"),
    ),
    EntitySeed(
        slug="dm-70-2015",
        title="DM 70/2015 — Standard qualitativi, strutturali, tecnologici e quantitativi dell'assistenza ospedaliera",
        entity_type="atto-normativo",
        entity_subtype="dm",
        ambito_canonico="accreditamento-sanitario",
        sintesi=(
            "Decreto ministeriale che fissa gli standard qualitativi, "
            "strutturali, tecnologici e quantitativi relativi all'assistenza "
            "ospedaliera. Riferimento per la pianificazione della rete "
            "ospedaliera regionale e per i bacini di utenza minimi per "
            "disciplina specialistica."
        ),
        tags=("entity", "atto-normativo", "dm", "accreditamento-sanitario"),
    ),
    EntitySeed(
        slug="iso-9001-2015",
        title="ISO 9001:2015 — Sistema di gestione per la qualita",
        entity_type="standard-tecnico",
        entity_subtype="iso",
        ambito_canonico="accreditamento-sanitario",
        sintesi=(
            "Standard internazionale per la progettazione e implementazione di "
            "un Sistema di Gestione della Qualita (SGQ). In sanita applicato "
            "in funzione del rafforzamento dell'accreditamento istituzionale "
            "regionale e in capitolati di gara per servizi sanitari. "
            "Certificabile da Organismo di Certificazione accreditato."
        ),
        tags=("entity", "standard-tecnico", "iso", "accreditamento-sanitario"),
    ),
    EntitySeed(
        slug="d-lgs-81-2008",
        title="D.Lgs. 81/2008 — Testo Unico sulla salute e sicurezza sul lavoro",
        entity_type="atto-normativo",
        entity_subtype="decreto-legislativo",
        ambito_canonico="sicurezza-lavoro",
        sintesi=(
            "Decreto legislativo di consolidamento della normativa in materia "
            "di tutela della salute e della sicurezza nei luoghi di lavoro. "
            "Si applica a tutte le strutture sanitarie come datore di lavoro. "
            "Obblighi DVR, designazione RSPP / ASPP / RLS, formazione "
            "lavoratori secondo ASR 21/12/2011 e 17/04/2025."
        ),
        tags=("entity", "atto-normativo", "decreto-legislativo", "sicurezza-lavoro"),
    ),
    EntitySeed(
        slug="legge-24-2017-gelli-bianco",
        title="Legge 24/2017 — Legge Gelli-Bianco sulla responsabilita professionale sanitaria",
        entity_type="atto-normativo",
        entity_subtype="legge-statale",
        ambito_canonico="accreditamento-sanitario",
        sintesi=(
            "Legge sulla sicurezza delle cure e la responsabilita "
            "professionale degli esercenti le professioni sanitarie. Istituisce "
            "il Centro per la gestione del rischio sanitario e la sicurezza "
            "del paziente in ogni regione. Introduce il sistema dual-track "
            "responsabilita civile e penale. Riferimento centrale per il clinical "
            "risk management e l'incident reporting."
        ),
        tags=("entity", "atto-normativo", "legge-statale", "accreditamento-sanitario"),
    ),
)


_SEED_QUALITA: tuple[EntitySeed, ...] = (
    EntitySeed(
        slug="iso-9001-2015",
        title="ISO 9001:2015 — Sistema di gestione per la qualita",
        entity_type="standard-tecnico",
        entity_subtype="iso",
        ambito_canonico="qualita-sgq",
        sintesi=(
            "Standard internazionale per la progettazione e implementazione di "
            "un Sistema di Gestione della Qualita (SGQ). Applicabile a "
            "organizzazioni di qualsiasi dimensione e settore industriale o "
            "dei servizi. Certificabile da Organismo di Certificazione "
            "accreditato. Struttura HLS Annex SL (High Level Structure) "
            "comune a tutti gli standard ISO MSS."
        ),
        tags=("entity", "standard-tecnico", "iso", "qualita-sgq"),
    ),
    EntitySeed(
        slug="iso-19011-2018",
        title="ISO 19011:2018 — Linee guida per audit di sistemi di gestione",
        entity_type="standard-tecnico",
        entity_subtype="iso",
        ambito_canonico="qualita-sgq",
        sintesi=(
            "Linee guida internazionali per pianificazione, conduzione e "
            "gestione di audit di sistemi di gestione (qualita, ambiente, "
            "sicurezza, energia). Definisce i principi dell'auditing, le "
            "competenze degli auditor, le tipologie di audit (interno, "
            "fornitore, terza parte). Riferimento operativo per Lead Auditor."
        ),
        tags=("entity", "standard-tecnico", "iso", "qualita-sgq"),
    ),
    EntitySeed(
        slug="iso-14001-2015",
        title="ISO 14001:2015 — Sistema di gestione ambientale",
        entity_type="standard-tecnico",
        entity_subtype="iso",
        ambito_canonico="gestione-ambientale",
        sintesi=(
            "Standard internazionale per la progettazione e implementazione di "
            "un Sistema di Gestione Ambientale (SGA). Struttura HLS Annex SL "
            "integrabile con ISO 9001 in sistemi integrati. Certificabile da "
            "Organismo di Certificazione accreditato. Riferimento per la "
            "compliance ambientale e la sostenibilita."
        ),
        tags=("entity", "standard-tecnico", "iso", "gestione-ambientale"),
    ),
)


def _seed_for_template(template: TemplateKind) -> tuple[EntitySeed, ...]:
    """Ritorna le entity seed per il template scelto.

    Per ``integrato`` merge dei seed cyber + sanita + qualita rimuovendo
    duplicati per slug (caso iso-9001-2015 presente sia in sanita che in
    qualita: il seed sanitario ha precedenza per ambito_canonico).
    """
    if template == "vuoto":
        return ()
    if template == "cyber":
        return _SEED_CYBER
    if template == "sanita":
        return _SEED_SANITA
    if template == "qualita":
        return _SEED_QUALITA
    if template == "integrato":
        seen_slugs: set[str] = set()
        merged: list[EntitySeed] = []
        for seed in (*_SEED_CYBER, *_SEED_SANITA, *_SEED_QUALITA):
            if seed.slug in seen_slugs:
                continue
            seen_slugs.add(seed.slug)
            merged.append(seed)
        return tuple(merged)
    return ()


# ----- Generatori contenuti file -----


def _render_claude_md(vault_name: str, template: TemplateKind) -> str:
    """Genera CLAUDE.md sostanziale con regole SCO base."""
    template_descr = {
        "vuoto": "struttura minima, nessun dominio preselezionato",
        "cyber": "cybersicurezza, NIS 2, ISO 27001, GDPR, Legge 90",
        "sanita": "accreditamento sanitario, ISO 9001 sanita, sicurezza lavoro",
        "qualita": "qualita ISO 9001 generico per industria e servizi",
        "integrato": "multi-dominio cyber + sanita + qualita",
    }[template]

    return f"""# {vault_name} — SCO Compliance OS

Vault di compliance SCO. Architettura three-layer SCO (raw/ + wiki/ + CLAUDE.md) per gestione strutturata di conoscenza normativa, dossier cliente e attivita consulenziali.

Template di partenza: **{template}** ({template_descr}).

## Le 9 cartelle del vault

| Cartella | Contiene |
|---|---|
| Contesto | Chi sei, ICP, voce, strategia, obiettivi, stack, workflow personali |
| Business | Lavoro operativo per area (clienti, SOP, deliverable) |
| Giornaliero | Log sessione + attivi + fatti |
| Libreria | Templates, framework, prompt, esempi, checklist, ricerca, decisioni, meeting |
| Skill | Catalogo skill Claude |
| Progetti | Progetti attivi discreti |
| Team | Persone, partner, collaboratori, AI agent |
| raw | Fonti immutabili (PDF normative, articoli, audit report, evidenze) |
| wiki | Knowledge layer derivato (entities, concepts, sources, synthesis, glossari) |

Inoltre alla root: **log/** (registro append-only attivita wiki spezzato per mese) e questo **CLAUDE.md**.

## Workflow LLM Wiki

Il vault adotta il pattern LLM Wiki: artefatto persistente che cresce nel tempo, dove ogni nuova fonte aggiorna le pagine di entita e di concetti senza riderivare la conoscenza ad ogni interazione.

### INGEST — aggiunta di una nuova fonte

1. L'utente deposita il file in raw/normativa/, raw/linee-guida/, raw/audit/, raw/client-evidence/.
2. Claude legge il file in raw/.
3. Discute key takeaways con l'utente prima di scrivere.
4. Crea wiki/sources/<slug>.md con riassunto strutturato.
5. Aggiorna wiki/entities/ e wiki/concepts/ pertinenti.
6. Append entry in log/YYYY-MM.md.

### QUERY — risposta consulenziale che usa il wiki

1. Claude legge prima wiki/_index.md come catalogo navigabile.
2. Apre solo le pagine wiki rilevanti.
3. Segue i backlink per recuperare contesto cross-standard.
4. Risponde con citazioni puntuali a pagine wiki e alle fonti raw originali.

## Convenzione di linking

Ogni file del vault ha:

- Frontmatter con `tags: [...]` (almeno il tag del compartimento) e `parent: "[[...]]"`
- Wiki-link `[[...]]` per ogni prima menzione di entita, persona, tool, file
- Footer `Part of [[parent-index]]`

Il vault deve diventare un grafo denso: centinaia di nodi connessi.

## Stato delle pagine wiki

- `stub` — pagina creata in fase seed, contiene identificazione + sintesi breve + struttura articolata + gap segnalati.
- `draft` — pagina in fase di sviluppo.
- `active` — pagina con tutte le sezioni canoniche compilate.
- `deprecated` — pagina che si riferisce ad atto abrogato.

## Pattern da evitare

- Non far scrivere Claude nelle fonti `raw/`. Sono immutabili.
- Non duplicare RAG e LLM Wiki.
- Non ingerire in batch senza supervisione iniziale.
"""


def _render_readme(vault_name: str, template: TemplateKind) -> str:
    """README sintetico per orientare nuovi operatori."""
    return f"""# {vault_name}

Vault SCO Compliance OS — template di partenza **{template}**.

## Come usare questo vault

1. Apri `CLAUDE.md` per le regole base.
2. Personalizza `Contesto/chi-sono.md` e `Contesto/strategia.md`.
3. Deposita le fonti normative in `raw/normativa/`.
4. Lascia che Claude popoli `wiki/entities/`, `wiki/sources/`, `wiki/synthesis/`.
5. Le attivita di giornata vanno in `Giornaliero/attivi.md`.

## Struttura

- `Contesto/` — chi sei, cosa fai, come lavori
- `Business/` — clienti e attivita operative
- `Giornaliero/` — log sessione + attivi
- `Libreria/` — templates, framework, ricerche, decisioni
- `Skill/` — catalogo skill Claude
- `Progetti/` — progetti discreti
- `Team/` — persone e partner
- `wiki/` — knowledge layer derivato (curato da Claude)
- `raw/` — fonti immutabili (curato dall'umano)
- `log/` — registro append-only attivita
"""


def _render_index(folder: str, vault_name: str) -> str:
    """Crea _index.md generico per una cartella del vault."""
    title = folder.replace("/", " — ").title()
    return f"""---
tags: [{folder.split("/")[0]}]
parent: "[[CLAUDE]]"
---

# {title}

Indice della cartella `{folder}/` del vault **{vault_name}**.

## Contenuto

(Da popolare. Aggiungi qui i link wiki ai file della cartella man mano che li crei.)
"""


def _render_contesto_chi_sono() -> str:
    return """---
tags: [contesto]
parent: "[[Contesto/_index]]"
---

# Chi sono

(Placeholder. Inserisci qui la tua identita professionale: nome, ruolo, qualifiche, ambiti di competenza, anni di esperienza.)

## Cosa faccio

(Descrivi le attivita principali: consulenza, audit, perizie, formazione, gap analysis, ecc.)

## Per chi lavoro

(ICP: tipologia di cliente target, settori serviti, dimensioni aziendali, geografie.)

Part of [[Contesto/_index]]
"""


def _render_contesto_strategia() -> str:
    return """---
tags: [contesto]
parent: "[[Contesto/_index]]"
---

# Strategia

(Placeholder. Inserisci qui gli obiettivi strategici di breve e medio termine, le aree di focus, gli investimenti previsti.)

## Obiettivi 12 mesi

(Da definire.)

## Aree di focus

(Da definire.)

Part of [[Contesto/_index]]
"""


def _render_attivi() -> str:
    return """---
tags: [giornaliero]
parent: "[[Giornaliero/_index]]"
---

# Attivi — to-do list operativa

To-do list dei task aperti. Aggiornata in tempo reale durante le sessioni di lavoro.

## In corso

(Vuoto al momento.)

## Carry-over

(Vuoto al momento.)

Part of [[Giornaliero/_index]]
"""


def _render_entity_stub(seed: EntitySeed) -> str:
    """Crea wiki/entities/<slug>.md stub con frontmatter SCO tipizzato + sintesi."""
    tags_str = ", ".join(seed.tags)
    subtype_line = f"entity_subtype: {seed.entity_subtype}\n" if seed.entity_subtype else ""
    return f"""---
type: entity
entity_type: {seed.entity_type}
{subtype_line}ambito_canonico: {seed.ambito_canonico}
title: "{seed.title}"
status: stub
last_reviewed: null
sources: []
tags: [{tags_str}]
parent: "[[wiki/entities/_index]]"
---

# {seed.title}

## Sintesi

{seed.sintesi}

## Storia

(Da popolare in ingest successivo.)

## Relationships

(Da popolare con `relationships:` nel frontmatter post-ingest.)

## Pagine cliente che richiamano questa entity

(Query Dataview ricostruira lista da `applica_entity[]` lato cliente al popolamento.)

## Note

Entity creata come **stub seed** dallo scaffolder vault SCO. Da arricchire in ingest successivi via skill `os-setup` + `os-ottimizzatore`.

Part of [[wiki/entities/_index]]
"""


# ----- Risultato scaffold -----


@dataclass(frozen=True)
class ScaffoldResult:
    """Esito di scaffold_vault()."""

    scaffolded: bool
    template: str
    files_created: int
    directories_created: int
    entities_seeded: int
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "scaffolded": self.scaffolded,
            "template": self.template,
            "files_created": self.files_created,
            "directories_created": self.directories_created,
            "entities_seeded": self.entities_seeded,
        }
        if self.reason is not None:
            out["reason"] = self.reason
        return out


# ----- API pubblica -----


def scaffold_vault(
    vault_path: Path,
    template: TemplateKind = "vuoto",
    *,
    vault_name: str,
) -> ScaffoldResult:
    """Scaffold completo vault SCO a partire da template scelto.

    Args:
        vault_path: directory dove creare la struttura. Se non esiste, viene
            creata. Se esiste e contiene gia un CLAUDE.md, lo scaffold viene
            saltato (idempotenza).
        template: uno dei 5 template ammessi (vuoto, cyber, sanita, qualita,
            integrato).
        vault_name: nome leggibile del vault (usato in CLAUDE.md + README +
            footer wiki).

    Returns:
        ScaffoldResult con counter file/dir creati + lista entity seeded.

    Raises:
        ValueError: se il template non e fra quelli ammessi, o se vault_name
            e vuoto/whitespace.
    """
    if template not in VALID_TEMPLATES:
        raise ValueError(f"Template '{template}' non ammesso. Valori: {VALID_TEMPLATES}")
    if not vault_name or not vault_name.strip():
        raise ValueError("vault_name non puo essere vuoto")

    vault_path = Path(vault_path).expanduser().resolve()

    # Idempotenza: se CLAUDE.md gia presente, non sovrascrivere nulla.
    claude_md = vault_path / "CLAUDE.md"
    if claude_md.exists():
        logger.info(
            "scaffold.skip_already_exists",
            path=str(vault_path),
            template=template,
        )
        return ScaffoldResult(
            scaffolded=False,
            template=template,
            files_created=0,
            directories_created=0,
            entities_seeded=0,
            reason="already_exists",
        )

    # Crea root + le 9 cartelle + sotto-cartelle wiki/raw.
    vault_path.mkdir(parents=True, exist_ok=True)
    directories_created = 0
    for base_dir in _BASE_DIRECTORIES:
        target = vault_path / base_dir
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            directories_created += 1
            logger.debug("scaffold.dir_created", path=str(target))

    files_created = 0

    # Root files: CLAUDE.md + README.md
    claude_md.write_text(
        _render_claude_md(vault_name, template),
        encoding="utf-8",
    )
    logger.info("scaffold.file_created", path=str(claude_md))
    files_created += 1

    readme_md = vault_path / "README.md"
    readme_md.write_text(_render_readme(vault_name, template), encoding="utf-8")
    logger.info("scaffold.file_created", path=str(readme_md))
    files_created += 1

    # _index.md per le 9 cartelle root (+ sotto-cartelle wiki + raw).
    for folder in _BASE_DIRECTORIES:
        index_file = vault_path / folder / "_index.md"
        if not index_file.exists():
            index_file.write_text(
                _render_index(folder, vault_name),
                encoding="utf-8",
            )
            files_created += 1
            logger.debug("scaffold.file_created", path=str(index_file))

    # Contesto: chi-sono + strategia placeholder.
    chi_sono = vault_path / "Contesto" / "chi-sono.md"
    chi_sono.write_text(_render_contesto_chi_sono(), encoding="utf-8")
    files_created += 1

    strategia = vault_path / "Contesto" / "strategia.md"
    strategia.write_text(_render_contesto_strategia(), encoding="utf-8")
    files_created += 1

    # Giornaliero: attivi.md operativo.
    attivi = vault_path / "Giornaliero" / "attivi.md"
    attivi.write_text(_render_attivi(), encoding="utf-8")
    files_created += 1

    # Entity seed da template.
    seeds = _seed_for_template(template)
    entities_seeded = 0
    for seed in seeds:
        entity_file = vault_path / "wiki" / "entities" / f"{seed.slug}.md"
        entity_file.write_text(_render_entity_stub(seed), encoding="utf-8")
        files_created += 1
        entities_seeded += 1
        logger.info(
            "scaffold.entity_seeded",
            slug=seed.slug,
            ambito=seed.ambito_canonico,
        )

    logger.info(
        "scaffold.complete",
        path=str(vault_path),
        template=template,
        vault_name=vault_name,
        files_created=files_created,
        directories_created=directories_created,
        entities_seeded=entities_seeded,
    )

    return ScaffoldResult(
        scaffolded=True,
        template=template,
        files_created=files_created,
        directories_created=directories_created,
        entities_seeded=entities_seeded,
    )


# ----- DEV-OPTIMIZER-AUTO: complete missing structure per vault esistenti -----


# Le 9 cartelle obbligatorie root vault SCO (fonte: CLAUDE.md vault Second
# Brain "Le 9 cartelle del vault"). Coincidono con cartelle root in
# ``_BASE_DIRECTORIES`` ma esplicitate qui per chiarezza dell'audit.
_CANONICAL_ROOT_FOLDERS: tuple[str, ...] = (
    "Contesto",
    "Business",
    "Giornaliero",
    "Libreria",
    "Skill",
    "Progetti",
    "Team",
    "raw",
    "wiki",
)


# Cartelle "auto-create" (scheletro vuoto OK senza chiedere).
# Razionale: non contengono dati semanticamente personali / cliente.
_AUTO_CREATE_FOLDERS: frozenset[str] = frozenset(
    {"Giornaliero", "Libreria", "Skill", "Progetti", "Team", "log"}
)


# Cartelle "opt-in utente" (chiedere prima di toccare).
# Razionale: dati personali / cliente / generati incrementalmente.
_OPT_IN_FOLDERS: frozenset[str] = frozenset({"Contesto", "Business", "raw", "wiki", "CLAUDE.md"})


@dataclass(frozen=True)
class CompleteStructureResult:
    """Esito di ``complete_missing_structure()``.

    Attributes:
        completed: True se almeno un file/cartella creato, False se vault gia
            completo o errore bloccante.
        files_created: lista path relativi creati (POSIX-style anche su Win).
        files_skipped: lista path gia presenti (NON sovrascritti).
        missing_before: lista cartelle mancanti PRIMA dell'operazione.
        errors: lista messaggi errore non bloccanti.
    """

    completed: bool
    files_created: tuple[str, ...]
    files_skipped: tuple[str, ...]
    missing_before: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "completed": self.completed,
            "files_created": list(self.files_created),
            "files_skipped": list(self.files_skipped),
            "missing_before": list(self.missing_before),
            "errors": list(self.errors),
        }


def inspect_missing_components(vault_root: Path) -> dict[str, object]:
    """Snapshot struttura SCO + classificazione mancanti (auto vs opt-in).

    Pure function: solo listdir + exists + is_dir. No write.

    Args:
        vault_root: path radice vault da ispezionare.

    Returns:
        dict con chiavi:
            - vault_exists: bool (path esiste come directory)
            - is_sco_structure: bool (tutte 9 cartelle + CLAUDE.md + log/ presenti)
            - present_folders: list[str] cartelle canoniche presenti
            - missing_folders: list[str] cartelle canoniche mancanti
            - missing_auto: list[str] sub-set mancanti auto-creabili senza chiedere
            - missing_opt_in: list[str] sub-set mancanti che richiedono opt-in
            - has_claude_md: bool
            - has_log_dir: bool
    """
    if not vault_root.exists() or not vault_root.is_dir():
        return {
            "vault_exists": False,
            "is_sco_structure": False,
            "present_folders": [],
            "missing_folders": list(_CANONICAL_ROOT_FOLDERS),
            "missing_auto": [f for f in _CANONICAL_ROOT_FOLDERS if f in _AUTO_CREATE_FOLDERS],
            "missing_opt_in": [f for f in _CANONICAL_ROOT_FOLDERS if f in _OPT_IN_FOLDERS],
            "has_claude_md": False,
            "has_log_dir": False,
        }

    present_folders: list[str] = []
    missing_folders: list[str] = []
    for folder in _CANONICAL_ROOT_FOLDERS:
        if (vault_root / folder).is_dir():
            present_folders.append(folder)
        else:
            missing_folders.append(folder)

    has_claude_md = (vault_root / "CLAUDE.md").exists()
    has_log_dir = (vault_root / "log").is_dir()

    missing_auto = [f for f in missing_folders if f in _AUTO_CREATE_FOLDERS]
    missing_opt_in = [f for f in missing_folders if f in _OPT_IN_FOLDERS]

    # log/ rientra in missing_auto se mancante.
    if not has_log_dir:
        missing_auto.append("log")
    # CLAUDE.md rientra in opt-in (DNA prescrittivo, va personalizzato).
    if not has_claude_md:
        missing_opt_in.append("CLAUDE.md")

    is_sco_structure = not missing_folders and has_claude_md and has_log_dir

    return {
        "vault_exists": True,
        "is_sco_structure": is_sco_structure,
        "present_folders": present_folders,
        "missing_folders": missing_folders,
        "missing_auto": missing_auto,
        "missing_opt_in": missing_opt_in,
        "has_claude_md": has_claude_md,
        "has_log_dir": has_log_dir,
    }


def complete_missing_structure(
    vault_path: Path,
    *,
    vault_name: str | None = None,
    include_opt_in: bool = False,
) -> CompleteStructureResult:
    """Crea SOLO cartelle/file mancanti nella struttura SCO senza sovrascrivere.

    Differenza con ``scaffold_vault()``:
        - ``scaffold_vault(mode="vuoto"|...)`` salta se CLAUDE.md esiste gia (idempotenza fresh).
        - ``complete_missing_structure()`` NON salta su CLAUDE.md: completa
          le cartelle/file mancanti lasciando intoccato il resto.

    Args:
        vault_path: directory esistente del vault da completare.
        vault_name: nome leggibile per CLAUDE.md stub (default ``vault_path.name``).
        include_opt_in: se True, crea anche cartelle/file "opt-in" (Contesto/,
            Business/, raw/, wiki/, CLAUDE.md). Se False (default), crea solo
            "auto-create" (Giornaliero/, Libreria/, Skill/, Progetti/, Team/, log/).

    Returns:
        ``CompleteStructureResult`` con files_created + completed + errors.

    Note:
        - Pattern SCO "no edit retroattivo" (Conv. 39): MAI sovrascrive file esistenti.
        - Pattern Conv. 41 tracciatura: ogni mkdir/write loggato + result audit.
        - Idempotent: chiamata ripetuta produce 0 files_created se gia completo.
        - Crea anche sotto-cartelle wiki/ (concepts/entities/sources/synthesis/glossari)
          e raw/ (normativa/linee-guida/audit/client-evidence) se le parent vengono create.
    """
    vault_path = Path(vault_path).expanduser().resolve()

    if not vault_path.exists() or not vault_path.is_dir():
        return CompleteStructureResult(
            completed=False,
            files_created=(),
            files_skipped=(),
            missing_before=(),
            errors=(f"vault_path {vault_path} non esiste o non e' directory",),
        )

    inspect = inspect_missing_components(vault_path)
    missing_before: tuple[str, ...] = tuple(cast(list[str], inspect["missing_folders"]))

    if inspect["is_sco_structure"] and not include_opt_in:
        # Vault gia completo: nessuna azione necessaria.
        logger.info(
            "scaffold.complete_missing.already_complete",
            path=str(vault_path),
        )
        return CompleteStructureResult(
            completed=False,
            files_created=(),
            files_skipped=(),
            missing_before=(),
            errors=(),
        )

    effective_vault_name = (vault_name or vault_path.name).strip() or vault_path.name

    files_created: list[str] = []
    files_skipped: list[str] = []
    errors: list[str] = []

    # 1. Crea cartelle root mancanti (sempre auto-create; opt-in solo se richiesto)
    auto_to_create: list[str] = list(cast(list[str], inspect["missing_auto"]))
    opt_in_to_create: list[str] = (
        list(cast(list[str], inspect["missing_opt_in"])) if include_opt_in else []
    )

    for folder in auto_to_create + opt_in_to_create:
        if folder == "CLAUDE.md":
            # CLAUDE.md gestito sotto come file
            continue
        target = vault_path / folder
        if target.exists():
            files_skipped.append(f"{folder}/")
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            files_created.append(f"{folder}/")
            logger.info(
                "scaffold.complete_missing.folder_created",
                path=str(target),
            )
        except OSError as exc:
            err_msg = f"mkdir {folder}/ failed: {exc}"
            errors.append(err_msg)
            logger.warning(
                "scaffold.complete_missing.folder_create_failed",
                folder=folder,
                error=str(exc),
            )

    # 2. Sotto-cartelle wiki/ se wiki/ stato creato (o gia presente con include_opt_in)
    if "wiki" in auto_to_create + opt_in_to_create or (
        include_opt_in and (vault_path / "wiki").is_dir()
    ):
        for sub in ("concepts", "entities", "sources", "synthesis", "glossari"):
            sub_path = vault_path / "wiki" / sub
            if sub_path.exists():
                files_skipped.append(f"wiki/{sub}/")
                continue
            try:
                sub_path.mkdir(parents=True, exist_ok=True)
                files_created.append(f"wiki/{sub}/")
            except OSError as exc:
                errors.append(f"mkdir wiki/{sub}/ failed: {exc}")

    # 3. Sotto-cartelle raw/ se raw/ stato creato (o gia presente con include_opt_in)
    if "raw" in auto_to_create + opt_in_to_create or (
        include_opt_in and (vault_path / "raw").is_dir()
    ):
        for sub in ("normativa", "linee-guida", "audit", "client-evidence", "inbox"):
            sub_path = vault_path / "raw" / sub
            if sub_path.exists():
                files_skipped.append(f"raw/{sub}/")
                continue
            try:
                sub_path.mkdir(parents=True, exist_ok=True)
                files_created.append(f"raw/{sub}/")
            except OSError as exc:
                errors.append(f"mkdir raw/{sub}/ failed: {exc}")

    # 4. _index.md placeholder per ogni cartella appena creata (idempotente).
    for folder in auto_to_create + opt_in_to_create:
        if folder == "CLAUDE.md":
            continue
        index_path = vault_path / folder / "_index.md"
        if index_path.exists():
            files_skipped.append(f"{folder}/_index.md")
            continue
        try:
            index_path.write_text(
                _render_index(folder, effective_vault_name),
                encoding="utf-8",
            )
            files_created.append(f"{folder}/_index.md")
        except OSError as exc:
            errors.append(f"write {folder}/_index.md failed: {exc}")

    # 5. CLAUDE.md: solo se include_opt_in (e' file opt-in).
    if include_opt_in:
        claude_md_path = vault_path / "CLAUDE.md"
        if not claude_md_path.exists():
            try:
                claude_md_path.write_text(
                    _render_claude_md(effective_vault_name, "vuoto"),
                    encoding="utf-8",
                )
                files_created.append("CLAUDE.md")
                logger.info(
                    "scaffold.complete_missing.claude_md_created",
                    path=str(claude_md_path),
                )
            except OSError as exc:
                errors.append(f"write CLAUDE.md failed: {exc}")
        else:
            files_skipped.append("CLAUDE.md")

    completed = bool(files_created)

    logger.info(
        "scaffold.complete_missing.result",
        path=str(vault_path),
        include_opt_in=include_opt_in,
        files_created_count=len(files_created),
        files_skipped_count=len(files_skipped),
        errors_count=len(errors),
        missing_before_count=len(missing_before),
    )

    return CompleteStructureResult(
        completed=completed,
        files_created=tuple(files_created),
        files_skipped=tuple(files_skipped),
        missing_before=missing_before,
        errors=tuple(errors),
    )


# ----- DEV-AUTO-SCAFFOLD v1.0.2: auto-organize completo per vault qualsiasi -----
#
# Convenzione 41 tracciatura + Conv. 44 lesson 1 CircuitBreaker su file ops +
# Conv. 47 single source of truth (riusa _BASE_DIRECTORIES + _seed_for_template).
#
# Differenza con complete_missing_structure():
#   - complete_missing_structure(): crea SOLO cartelle/file mancanti, niente
#     re-classify dei file esistenti, niente seed entity/concepts/glossario.
#   - auto_organize_vault(): operazione COMPLETA. Esegue 5 fasi:
#       1. Backup file esistenti (lazy, solo se subiranno spostamento) in
#          _archivio_pre_v1.0.2/<filename>
#       2. Crea TUTTE le cartelle canoniche + sotto-cartelle wiki/raw + log/
#       3. Re-classify file .md esistenti con mapping cartelle non-SCO -> SCO
#          (Context->Contesto, Daily->Giornaliero/YYYY-MM/, Resources->Libreria/,
#           Projects->Progetti/, Intelligence->Libreria/ricerca/, Skills->Skill/)
#          o per frontmatter type:source/entity/concept/synthesis/cliente
#       4. Crea AGENTS.md template + README.md welcome (idempotent, no overwrite)
#       5. Popola entity seed (8 normative italiane comuni) + 4 concepts comuni +
#          glossario tabellare 35+ sigle in wiki/glossari/_index.md
#   - Idempotente: chiamata ripetuta su vault gia auto-organizzato non
#     ri-crea file gia presenti, non ri-sposta file gia in posizione SCO.


# Mapping cartelle non-SCO -> SCO (chiavi: source folder name root vault,
# valori: destination folder name relative to vault root).
# Pattern Conv. 47: il mapping vive in un solo posto, non duplicato.
_NON_SCO_FOLDER_MAP: dict[str, str] = {
    "Context": "Contesto",
    "Daily": "Giornaliero",
    "Resources": "Libreria",
    "Projects": "Progetti",
    "Intelligence": "Libreria/ricerca",
    "Skills": "Skill",
}


# Pattern regex semplice per identificare file daily YYYY-MM-DD.md (Conv. 35
# verifica fonti vault: pattern noto del session-lifecycle SCO).
_DAILY_FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")


# Entity seed addizionali per popolamento completo SOC vault (3 oltre i 5 cyber)
_EXTRA_SEED_AUTO_ORGANIZE: tuple[EntitySeed, ...] = (
    EntitySeed(
        slug="reg-ue-2016-679-gdpr",
        title="Reg. UE 2016/679 — GDPR",
        entity_type="atto-normativo",
        entity_subtype="regolamento-ue",
        ambito_canonico="privacy-protezione-dati",
        sintesi=(
            "Regolamento generale sulla protezione dei dati personali, "
            "applicabile direttamente in tutti gli Stati membri dal "
            "25 maggio 2018. Definisce diritti dell'interessato, obblighi "
            "del titolare e del responsabile del trattamento, principi di "
            "trattamento (liceita, correttezza, trasparenza, minimizzazione, "
            "limitazione conservazione, integrita e riservatezza, "
            "accountability). Designa il Garante Privacy come autorita "
            "nazionale italiana. Sanzioni fino al 4% del fatturato annuo "
            "globale o 20 milioni EUR."
        ),
        tags=("entity", "atto-normativo", "regolamento-ue", "privacy-protezione-dati"),
    ),
    EntitySeed(
        slug="iso-9001-2015",
        title="ISO 9001:2015 — Sistema di gestione per la qualita",
        entity_type="standard-tecnico",
        entity_subtype="iso",
        ambito_canonico="qualita-sgq",
        sintesi=(
            "Standard internazionale per la progettazione e implementazione di "
            "un Sistema di Gestione della Qualita (SGQ). Applicabile a "
            "organizzazioni di qualsiasi dimensione e settore industriale o "
            "dei servizi. Certificabile da Organismo di Certificazione "
            "accreditato. Struttura HLS Annex SL (High Level Structure) "
            "comune a tutti gli standard ISO MSS, integrabile con ISO 14001 "
            "e ISO 45001 in sistemi integrati."
        ),
        tags=("entity", "standard-tecnico", "iso", "qualita-sgq"),
    ),
    EntitySeed(
        slug="reg-ue-2024-1689-ai-act",
        title="Reg. UE 2024/1689 — AI Act",
        entity_type="atto-normativo",
        entity_subtype="regolamento-ue",
        ambito_canonico="governance-ai",
        sintesi=(
            "Regolamento europeo sull'intelligenza artificiale (AI Act), "
            "primo quadro normativo organico al mondo. Applicabilita "
            "progressiva: 02/02/2025 pratiche vietate Art. 5, "
            "02/08/2025 GPAI + governance, 02/08/2026 sistemi alto rischio "
            "Allegato III, 02/08/2027 sistemi alto rischio Allegato I. "
            "Classifica i sistemi IA in 4 categorie di rischio (vietato, "
            "alto, limitato, minimo) con obblighi differenziati per "
            "provider e deployer. AGENAS designata autorita di vigilanza "
            "per IA sanitaria in Italia."
        ),
        tags=("entity", "atto-normativo", "regolamento-ue", "governance-ai"),
    ),
)


# Concept seed — pagine wiki/concepts/ comuni cross-standard.
@dataclass(frozen=True)
class ConceptSeed:
    """Definizione concept seed cross-standard."""

    slug: str
    title: str
    sintesi: str
    related_entities: tuple[str, ...]
    tags: tuple[str, ...]


_CONCEPT_SEEDS: tuple[ConceptSeed, ...] = (
    ConceptSeed(
        slug="analisi-dei-rischi",
        title="Analisi dei rischi",
        sintesi=(
            "Processo sistematico di identificazione, analisi e valutazione "
            "dei rischi che possono compromettere il raggiungimento degli "
            "obiettivi dell'organizzazione. In ambito SGSI segue ISO/IEC "
            "27005:2022 + ISO 31000:2018. In ambito qualita segue il "
            "principio del risk-based thinking di ISO 9001:2015 cap. 6.1. "
            "In ambito NIS 2 e' obbligo esplicito Art. 24 c. 2 lett. a del "
            "D.Lgs. 138/2024. Output tipici: registro rischi, matrice "
            "probabilita-impatto, piano di trattamento dei rischi."
        ),
        related_entities=(
            "iso-iec-27001-2022",
            "iso-9001-2015",
            "d-lgs-138-2024",
        ),
        tags=("concept", "risk-management", "cross-standard"),
    ),
    ConceptSeed(
        slug="audit-interno",
        title="Audit interno",
        sintesi=(
            "Processo sistematico, indipendente e documentato per ottenere "
            "evidenze di audit e valutarle oggettivamente al fine di "
            "stabilire in che misura sono soddisfatti i criteri di audit. "
            "Riferimento normativo: ISO 19011:2018 (linee guida audit "
            "sistemi di gestione) + clausola 9.2 ISO 9001/27001/14001/42001. "
            "Pianificato annualmente nel Programma di Audit con copertura "
            "dei processi su un ciclo triennale. Output tipici: piano "
            "audit, lista di riscontro, rapporto di audit, NC e SM "
            "riscontrate."
        ),
        related_entities=(
            "iso-iec-27001-2022",
            "iso-9001-2015",
        ),
        tags=("concept", "audit", "cross-standard"),
    ),
    ConceptSeed(
        slug="riesame-direzione",
        title="Riesame della direzione",
        sintesi=(
            "Riesame periodico (tipicamente annuale) del sistema di "
            "gestione da parte dell'alta direzione per assicurare la sua "
            "continua idoneita, adeguatezza ed efficacia. Riferimento "
            "normativo: clausola 9.3 ISO 9001/27001/14001/42001/20000-1. "
            "Input obbligatori: esiti audit interni, feedback parti "
            "interessate, performance dei processi, conformita prodotti/"
            "servizi, stato azioni correttive, esito riesame precedente, "
            "cambiamenti contestuali. Output: decisioni su miglioramento "
            "+ risorse + cambiamenti del sistema."
        ),
        related_entities=(
            "iso-iec-27001-2022",
            "iso-9001-2015",
        ),
        tags=("concept", "governance", "cross-standard"),
    ),
    ConceptSeed(
        slug="non-conformita",
        title="Non conformita",
        sintesi=(
            "Mancato soddisfacimento di un requisito (definizione ISO "
            "9000:2015). Classificata per gravita: NC Maggiore (NC_E "
            "esterna o NC_I interna) implica assenza o carenza grave nel "
            "sistema; NC Minore (NC) implica deviazione puntuale gestibile "
            "con azione correttiva; Spunto di Miglioramento (SM) e' "
            "osservazione non vincolante. Trattamento: registrazione, "
            "analisi cause radice (5 Why, Ishikawa, FMEA), pianificazione "
            "azione correttiva, verifica efficacia. Riferimento: ISO "
            "9001 cl. 10.2, ISO/IEC 27001 cl. 10.2."
        ),
        related_entities=(
            "iso-iec-27001-2022",
            "iso-9001-2015",
        ),
        tags=("concept", "non-conformita", "azione-correttiva"),
    ),
    ConceptSeed(
        slug="trattamento-dei-rischi",
        title="Trattamento dei rischi",
        sintesi=(
            "Fase del processo di gestione del rischio in cui si "
            "selezionano e implementano le opzioni per modificare il "
            "rischio. Quattro opzioni canoniche: evitare il rischio "
            "(eliminare la fonte), modificare il rischio (mitigare con "
            "controlli), trasferire il rischio (assicurazione, contratto), "
            "accettare il rischio (residuo entro soglia di tollerabilita). "
            "Per ciascun controllo selezionato deve essere documentato in "
            "SoA (Statement of Applicability) la giustificazione e lo "
            "stato di implementazione. Riferimento ISO/IEC 27001 cl. 6.1.3."
        ),
        related_entities=(
            "iso-iec-27001-2022",
            "d-lgs-138-2024",
        ),
        tags=("concept", "risk-treatment", "soa"),
    ),
)


def _render_concept_stub(seed: ConceptSeed) -> str:
    """Crea wiki/concepts/<slug>.md stub con sintesi + related entities."""
    tags_str = ", ".join(seed.tags)
    related_block = (
        "\n".join(f"- [[wiki/entities/{slug}]]" for slug in seed.related_entities)
        or "(da popolare)"
    )
    return f"""---
type: concept
title: "{seed.title}"
status: stub
last_reviewed: null
related_entities: [{", ".join(seed.related_entities)}]
tags: [{tags_str}]
parent: "[[wiki/concepts/_index]]"
---

# {seed.title}

## Sintesi

{seed.sintesi}

## Entity correlate

{related_block}

## Note

Concept creato come **stub seed** dallo scaffolder vault SCO (auto-organize v1.0.2). Da arricchire in ingest successivi.

Part of [[wiki/concepts/_index]]
"""


# Glossario seed: 35+ sigle canoniche SCO (cyber + sanita + privacy + lavoro
# + qualita). Pattern Conv. 29 SOP "consulta-glossario-prima-di-espandere-sigla".
_GLOSSARIO_SEED_ROWS: tuple[tuple[str, str, str], ...] = (
    # (sigla, espansione canonica, dominio)
    ("ACN", "Agenzia per la Cybersicurezza Nazionale", "cyber"),
    ("AgID", "Agenzia per l'Italia Digitale", "cyber"),
    ("AGENAS", "Agenzia Nazionale per i Servizi Sanitari Regionali", "sanita"),
    ("AI Act", "Reg. UE 2024/1689 — Artificial Intelligence Act", "governance-ai"),
    ("ASR", "Accordo Stato-Regioni", "lavoro"),
    ("BIA", "Business Impact Analysis", "cyber"),
    ("BCP", "Business Continuity Plan", "cyber"),
    ("CSIRT", "Computer Security Incident Response Team", "cyber"),
    ("DPO", "Data Protection Officer", "privacy"),
    ("DPIA", "Data Protection Impact Assessment", "privacy"),
    ("DRP", "Disaster Recovery Plan", "cyber"),
    ("DVR", "Documento di Valutazione dei Rischi", "lavoro"),
    ("DUVRI", "Documento Unico di Valutazione dei Rischi Interferenziali", "lavoro"),
    ("ECM", "Educazione Continua in Medicina", "sanita"),
    ("ENISA", "European Union Agency for Cybersecurity", "cyber"),
    ("GDPR", "General Data Protection Regulation — Reg. UE 2016/679", "privacy"),
    ("IRCCS", "Istituto di Ricovero e Cura a Carattere Scientifico", "sanita"),
    ("ISO 9001", "Standard internazionale Sistema Gestione Qualita", "qualita"),
    ("ISO 14001", "Standard internazionale Sistema Gestione Ambientale", "gestione-ambientale"),
    ("ISO/IEC 27001", "Standard internazionale Sistema Gestione Sicurezza Informazioni", "cyber"),
    (
        "ISO/IEC 42001",
        "Standard internazionale Sistema Gestione Intelligenza Artificiale",
        "governance-ai",
    ),
    ("LG", "Linee Guida", "cross"),
    ("MFA", "Multi Factor Authentication", "cyber"),
    ("NC", "Non Conformita", "qualita"),
    ("NC_E", "Non Conformita Maggiore Esterna", "qualita"),
    ("NC_I", "Non Conformita Maggiore Interna", "qualita"),
    (
        "NIS 2",
        "Direttiva 2022/2555 + D.Lgs. 138/2024 — Network and Information Security 2",
        "cyber",
    ),
    ("OdC", "Organismo di Certificazione", "qualita"),
    ("RPD", "Responsabile della Protezione dei Dati (DPO in italiano)", "privacy"),
    ("RSPP", "Responsabile del Servizio di Prevenzione e Protezione", "lavoro"),
    ("RLS", "Rappresentante dei Lavoratori per la Sicurezza", "lavoro"),
    ("SGSI", "Sistema di Gestione della Sicurezza delle Informazioni", "cyber"),
    ("SGQ", "Sistema di Gestione per la Qualita", "qualita"),
    ("SM", "Spunto di Miglioramento", "qualita"),
    ("SOA", "Statement of Applicability (SGSI 27001)", "cyber"),
    ("SOC", "Security Operations Center", "cyber"),
    ("VAR", "Valutazione Audit di Ricertificazione", "qualita"),
)


def _render_glossario_index(vault_name: str) -> str:
    """Crea wiki/glossari/_index.md con tabella sigle canoniche."""
    rows_md = "\n".join(
        f"| {sigla} | {espansione} | {dominio} |"
        for sigla, espansione, dominio in _GLOSSARIO_SEED_ROWS
    )
    return f"""---
type: glossario
title: "Glossario canonico SCO — sigle aziendali e di settore"
status: active
last_reviewed: null
tags: [wiki, glossari, glossario, canonical]
parent: "[[wiki/_index]]"
---

# Glossario canonico SCO — {vault_name}

Glossario unico tabellare di sigle aziendali e di settore. Pattern Conv. 29 SOP "consulta-glossario-prima-di-espandere-sigla": quando si esplicita una sigla, **prima** consultare questa tabella per usare l'espansione canonica registrata. Mai inferire dal modello di linguaggio.

## Tabella sigle

| Sigla | Espansione canonica | Dominio |
|-------|---------------------|---------|
{rows_md}

## Estensioni

Quando emerge una sigla non glossata, Claude **dichiara in chat** "sigla X non glossata, suggerisco verifica con utente" e propone l'aggiunta via `AskUserQuestion` prima di esplicitare l'espansione. Mai inferire l'espansione dal modello di linguaggio.

Part of [[wiki/_index]]
"""


def _render_agents_md(vault_name: str) -> str:
    """Crea AGENTS.md charter QI 190 + 9 modalita operative SCO."""
    return f"""---
tags: [agents, charter]
parent: "[[CLAUDE]]"
---

# AGENTS.md — Charter operativo agenti SCO per vault {vault_name}

## Postura cognitiva — QI 190 baseline

Ogni interazione con agenti AI in questo vault DEVE rispettare la postura QI 190 minima cristallizzata in CLAUDE.md sezione "QI 190 BASELINE". Doppio enforcement cerimoniale:

1. **Apertura sessione**: blocco `[Postura QI 190 — apertura sessione <data>]` con 3-5 punti di prova osservabile (anticipazione edge case + correzione ipotesi imprecise + distinzione fatto/ipotesi/opinione + tassonomia coerente + anticipazione criticita normativa/tecnica/operativa).
2. **Chiusura sessione**: blocco `[Postura QI 190 — chiusura sessione <data>]` con 3-5 punti di prova osservabile sulla sessione conclusa (scelta tecnica controintuitiva + ipotesi smentita o riformulata + edge case anticipato + decisione di trade-off + correlazione cross-cliente o cross-framework scoperta in corsa).

## Le 9 modalita operative SCO

| Modalita | Trigger | Descrittore breve |
|----------|---------|-------------------|
| INGEST | utente deposita file in raw/ | Lettura fonte raw -> sintesi -> creazione wiki/sources/ + aggiornamento entities/concepts. Max 15 file modificati per ingest, no batch senza supervisione. |
| QUERY | utente chiede risposta consulenziale | Lettura wiki/_index.md -> apertura pagine rilevanti -> risposta con citazioni puntuali a wiki + raw. Logging in log/YYYY-MM.md per query >10 min o richiamo >=3 entity. |
| LINT | domenica O su richiesta esplicita | Audit settimanale: pagine orfane + contraddizioni + claim stale + concetti senza pagina + cross-reference mancanti + gap stub + entity active senza fonte raw. |
| SCAFFOLD | nuovo vault da template OR cartelle SCO mancanti | Materializza struttura SCO (9 cartelle + sotto-cartelle wiki/raw + entity seed) o completa incrementale senza overwrite. |
| AUTO-ORGANIZE | vault esistente con struttura non-SCO | Backup pre-operazione + re-classify file esistenti con mapping cartelle non-SCO -> SCO + seed entity/concepts/glossario. Idempotente. |
| OPTIMIZE | utente chiede miglioramento vault | Skill os-ottimizzatore: profilo + analisi + raccomandazioni. Opera sul context vault_inspect del payload runtime. |
| AUDIT-DRIFT | sigla aziendale rilevata in deliverable | Pattern Conv. 38 fix-it-once: catturato drift su 1 file -> audit massiva sulla filiera documentale impattata + fix coerente cross-file. |
| MULTI-AGENT | richiesta esplicita "subagent paralleli" | Pattern Conv. 33+34: research subagents in parallelo + main agent per write + spot check obbligatorio post-multi-agent (fact-check + vocabolario chiuso + dichiarazione incertezza). |
| VERIFY-OR-REDO | dopo ogni fix/cambio sostantivo | Pattern VERIFY-OR-REDO LOOP: 1.Understand 2.Execute 3.Verify like the user would 4.Loop until pass 5.Only then confirm. Anti-pattern proofreading != verifying. |

## Regole permanenti applicate in questo vault

- Conv. 29 SOP consulta-glossario-prima-di-espandere-sigla
- Conv. 35 verifica fonti vault + WebSearch istituzionali
- Conv. 38 sigle aziendali drift fix-it-once
- Conv. 39 three-layer SCO preservation
- Conv. 41 PROTOCOLLO TRACCIATURA SESSIONE (skill + passi + assunzioni vs verifiche)
- Conv. 46 SMOKE TEST E2E PRIMA DEL TAG (per software e deliverable)
- Conv. 47 single source of truth (per costanti version e schema)
- Convenzioni tipografiche permanenti 03/05/2026 (humanizer + virgolette dritte + "al punto" + font uniforme + grassetto preciso + placeholder italiano professionale)

Per il dettaglio completo delle regole consulta `CLAUDE.md`.

Part of [[CLAUDE]]
"""


# Cartelle target del re-classify (per ognuna serve _archivio_pre_v1.0.2/
# come backup pre-operazione).
_BACKUP_DIR_NAME = "_archivio_pre_v1.0.2"


@dataclass(frozen=True)
class AutoOrganizeResult:
    """Esito di ``auto_organize_vault()``.

    Attributes:
        organized: True se almeno un file/cartella creato o spostato.
        directories_created: lista cartelle nuove create.
        files_created: lista file nuovi (entity seed, concepts, glossario, AGENTS.md).
        files_moved: lista (src, dest) coppie file spostati nel re-classify.
        files_backed_up: lista path backup creati in _archivio_pre_v1.0.2/.
        files_skipped: lista path saltati (gia in posizione, no overwrite).
        errors: lista errori non bloccanti.
    """

    organized: bool
    directories_created: tuple[str, ...]
    files_created: tuple[str, ...]
    files_moved: tuple[tuple[str, str], ...]
    files_backed_up: tuple[str, ...]
    files_skipped: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "organized": self.organized,
            "directories_created": list(self.directories_created),
            "files_created": list(self.files_created),
            "files_moved": [{"src": src, "dest": dest} for src, dest in self.files_moved],
            "files_backed_up": list(self.files_backed_up),
            "files_skipped": list(self.files_skipped),
            "errors": list(self.errors),
        }


def _read_frontmatter_type(md_path: Path) -> str | None:
    """Legge frontmatter YAML di un file .md e ritorna il campo ``type`` se presente.

    Pure function: solo open + read primi 4 KiB. Robusto a errori di parsing
    YAML (ritorna None senza sollevare). Pattern Conv. 44 lesson 1: errori
    file ops isolati, non bloccano il caller.
    """
    try:
        with md_path.open("r", encoding="utf-8") as f:
            head = f.read(4096)
    except (OSError, UnicodeDecodeError):
        return None

    if not head.startswith("---"):
        return None

    # Estrai blocco frontmatter (tra primi due delimitatori ---).
    lines = head.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return None

    frontmatter_text = "\n".join(lines[1:end_idx])
    # Parsing minimale linea-per-linea per evitare dipendenza yaml qui (gia
    # importata dal loader.py ma teniamo questa funzione self-contained).
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if line.startswith("type:"):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            return value or None
    return None


def _classify_md_for_reorganize(
    md_path: Path,
    vault_root: Path,
) -> Path | None:
    """Determina destinazione SCO per un file .md esistente.

    Pure function: NO IO write, solo lettura frontmatter eventuale.

    Strategia:
        1. Se il file e' nella root del vault -> resta in root (es. CLAUDE.md).
        2. Se il file e' gia dentro una cartella SCO canonica -> resta (skip).
        3. Filename pattern YYYY-MM-DD.md -> Giornaliero/YYYY-MM/YYYY-MM-DD.md
           (anche se gia in Giornaliero/ ma non in sub YYYY-MM/).
        4. Frontmatter type:source -> wiki/sources/<basename>
        5. Frontmatter type:entity -> wiki/entities/<basename>
        6. Frontmatter type:concept -> wiki/concepts/<basename>
        7. Frontmatter type:synthesis -> wiki/synthesis/<basename>
        8. Frontmatter type:cliente -> Business/clienti/<basename>
        9. Parent folder name in _NON_SCO_FOLDER_MAP -> map[parent] / <basename>
           (es. Context/identity.md -> Contesto/identity.md)
        10. Altrimenti None (lascia in posizione corrente).

    Args:
        md_path: file .md da classificare.
        vault_root: radice vault.

    Returns:
        Path destinazione assoluta nuova, oppure None se il file va lasciato
        in posizione corrente.
    """
    try:
        rel = md_path.relative_to(vault_root)
    except ValueError:
        return None

    parts = rel.parts
    basename = md_path.name

    # 1. File in root vault -> resta (es. CLAUDE.md, README.md, AGENTS.md).
    if len(parts) == 1:
        return None

    # 2. Skip file in cartelle SCO canoniche gia (e relative sotto-cartelle).
    sco_canonical_roots = {
        "Contesto",
        "Business",
        "Giornaliero",
        "Libreria",
        "Skill",
        "Progetti",
        "Team",
        "raw",
        "wiki",
        "log",
        ".claude",
        ".obsidian",
        _BACKUP_DIR_NAME,
    }
    if parts[0] in sco_canonical_roots:
        # 3. Filename daily pattern: se in Giornaliero/ ma NON in sub YYYY-MM/
        # -> sposta in sub YYYY-MM/.
        if parts[0] == "Giornaliero" and _DAILY_FILENAME_RE.match(basename):
            year, month, _day = _DAILY_FILENAME_RE.match(basename).groups()  # type: ignore[union-attr]
            target_rel = Path("Giornaliero") / f"{year}-{month}" / basename
            target_abs = vault_root / target_rel
            if target_abs == md_path:
                return None
            return target_abs
        # Altrimenti file gia in cartella SCO: skip.
        return None

    # 3. Filename daily pattern (es. 2026-05-19.md in cartella Daily) -> Giornaliero/YYYY-MM/
    daily_match = _DAILY_FILENAME_RE.match(basename)
    if daily_match:
        year, month, _day = daily_match.groups()
        return vault_root / "Giornaliero" / f"{year}-{month}" / basename

    # 4-8. Frontmatter type-based routing.
    fm_type = _read_frontmatter_type(md_path)
    type_to_folder: dict[str, str] = {
        "source": "wiki/sources",
        "entity": "wiki/entities",
        "concept": "wiki/concepts",
        "synthesis": "wiki/synthesis",
        "cliente": "Business/clienti",
    }
    if fm_type in type_to_folder:
        return vault_root / type_to_folder[fm_type] / basename

    # 9. Parent folder name in _NON_SCO_FOLDER_MAP -> map[parent] / <basename>.
    parent_root = parts[0]
    if parent_root in _NON_SCO_FOLDER_MAP:
        sco_folder = _NON_SCO_FOLDER_MAP[parent_root]
        # Preserva l'eventuale sub-path successivo (es. Resources/templates/x.md
        # -> Libreria/templates/x.md).
        sub_rel = Path(*parts[1:]) if len(parts) > 1 else Path(basename)
        return vault_root / sco_folder / sub_rel

    # 10. Default: nessuno spostamento.
    return None


def auto_organize_vault(
    vault_path: Path,
    *,
    vault_name: str | None = None,
    auto_apply: bool = True,
) -> AutoOrganizeResult:
    """Auto-completa struttura SCO + re-classify file esistenti + popola seed.

    Cinque fasi sequenziali (con CircuitBreaker per fase, Conv. 44 lesson 1):
        1. Crea TUTTE le cartelle canoniche SCO (riusa scaffold_vault logic).
        2. Backup file in posizione di spostamento -> _archivio_pre_v1.0.2/.
        3. Re-classify file .md esistenti (mapping non-SCO -> SCO o per
           frontmatter type:...).
        4. Crea AGENTS.md + README.md template + _index.md per cartelle nuove.
        5. Popola entity seed (8 normative italiane comuni) + 5 concepts + glossario
           tabellare 35+ sigle.

    Idempotente: chiamata ripetuta non ri-sposta file gia in posizione SCO,
    non ri-crea entity gia presenti, non ri-fa backup.

    Args:
        vault_path: directory esistente del vault da organizzare.
        vault_name: nome leggibile per CLAUDE.md/README/AGENTS.md
            (default ``vault_path.name``).
        auto_apply: se True (default), applica realmente le modifiche.
            Se False, ritorna lo stesso AutoOrganizeResult ma in dry-run
            (zero IO write, solo simulazione). Utile per audit pre-conferma.

    Returns:
        AutoOrganizeResult con counters e liste di operazioni eseguite.

    Note:
        - Pattern Conv. 41 tracciatura: log dettagliato di ogni fase + ogni
          file backup/spostato/creato.
        - Pattern Conv. 44 lesson 1 CircuitBreaker: errori file ops isolati
          per fase, non bloccano fasi successive.
        - Pattern Conv. 47 single source of truth: riusa _BASE_DIRECTORIES +
          _seed_for_template + _render_index per coerenza con scaffold_vault.
        - Pattern SCO "no edit retroattivo" (Conv. 39): MAI sovrascrive file
          esistenti, sempre backup pre-spostamento.
    """
    import shutil

    vault_path = Path(vault_path).expanduser().resolve()

    if not vault_path.exists() or not vault_path.is_dir():
        return AutoOrganizeResult(
            organized=False,
            directories_created=(),
            files_created=(),
            files_moved=(),
            files_backed_up=(),
            files_skipped=(),
            errors=(f"vault_path {vault_path} non esiste o non e' directory",),
        )

    effective_vault_name = (vault_name or vault_path.name).strip() or vault_path.name

    directories_created: list[str] = []
    files_created: list[str] = []
    files_moved: list[tuple[str, str]] = []
    files_backed_up: list[str] = []
    files_skipped: list[str] = []
    errors: list[str] = []

    logger.info(
        "auto_organize.start",
        path=str(vault_path),
        vault_name=effective_vault_name,
        auto_apply=auto_apply,
    )

    # ----- FASE 1: Crea cartelle canoniche SCO -----
    # CircuitBreaker: errori in mkdir loggati ma non bloccano fasi successive.
    for base_dir in _BASE_DIRECTORIES:
        target = vault_path / base_dir
        if target.exists():
            continue
        if not auto_apply:
            directories_created.append(f"{base_dir}/")
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            directories_created.append(f"{base_dir}/")
            logger.debug("auto_organize.dir_created", path=str(target))
        except OSError as exc:
            err = f"FASE 1 mkdir {base_dir}/ failed: {exc}"
            errors.append(err)
            logger.warning("auto_organize.dir_create_failed", folder=base_dir, error=str(exc))

    # ----- FASE 2 + 3: Re-classify file esistenti con backup -----
    # CircuitBreaker per file: ogni errore singolo non blocca gli altri.
    # Iteriamo SOLO file .md (raw fonti immutabili non vengono toccate per Conv. 39).
    backup_dir = vault_path / _BACKUP_DIR_NAME
    candidate_files: list[Path] = []
    try:
        for md_file in vault_path.rglob("*.md"):
            # Skip file gia nel backup dir, .claude, .obsidian.
            try:
                rel_path: Path = md_file.relative_to(vault_path)
            except ValueError:
                continue
            if rel_path.parts and rel_path.parts[0] in {
                _BACKUP_DIR_NAME,
                ".claude",
                ".obsidian",
                ".git",
            }:
                continue
            candidate_files.append(md_file)
    except OSError as exc:
        err = f"FASE 2 rglob *.md failed: {exc}"
        errors.append(err)
        logger.error("auto_organize.rglob_failed", error=str(exc))

    for md_file in candidate_files:
        try:
            dest = _classify_md_for_reorganize(md_file, vault_path)
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"FASE 3 classify {md_file.name} failed: {exc}")
            continue
        if dest is None:
            continue
        # Se dest esiste gia: SKIP (no overwrite, Conv. 39).
        if dest.exists():
            try:
                files_skipped.append(str(dest.relative_to(vault_path)))
            except ValueError:
                files_skipped.append(str(dest))
            continue

        if not auto_apply:
            try:
                src_rel_str = str(md_file.relative_to(vault_path))
                dest_rel_str = str(dest.relative_to(vault_path))
            except ValueError:
                src_rel_str = str(md_file)
                dest_rel_str = str(dest)
            files_moved.append((src_rel_str, dest_rel_str))
            continue

        # Backup pre-spostamento (Conv. 39 + Conv. 42 backup PRE-REDAZIONE).
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            # Backup name include subpath per evitare collisioni
            # (Context/identity.md vs Identity.md altro percorso).
            try:
                src_rel_path: Path = md_file.relative_to(vault_path)
                backup_name = "__".join(src_rel_path.parts)
            except ValueError:
                backup_name = md_file.name
            backup_path = backup_dir / backup_name
            if not backup_path.exists():
                shutil.copy2(str(md_file), str(backup_path))
                files_backed_up.append(f"{_BACKUP_DIR_NAME}/{backup_name}")
                logger.info(
                    "auto_organize.backup_created",
                    src=str(md_file),
                    backup=str(backup_path),
                )
        except OSError as exc:
            errors.append(f"FASE 2 backup {md_file.name} failed: {exc}")
            # Non bloccare lo spostamento se backup fallisce — il file
            # rimane comunque sotto controllo di Git nel vault.

        # Spostamento.
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(md_file), str(dest))
            try:
                src_rel_str = str(md_file.relative_to(vault_path))
                dest_rel_str = str(dest.relative_to(vault_path))
            except ValueError:
                src_rel_str = str(md_file)
                dest_rel_str = str(dest)
            files_moved.append((src_rel_str, dest_rel_str))
            logger.info(
                "auto_organize.file_moved",
                src=str(md_file),
                dest=str(dest),
            )
        except (OSError, shutil.Error) as exc:
            errors.append(f"FASE 3 move {md_file.name} -> {dest.name} failed: {exc}")
            logger.warning(
                "auto_organize.move_failed",
                src=str(md_file),
                dest=str(dest),
                error=str(exc),
            )

    # ----- FASE 4: AGENTS.md + README.md + _index.md per cartelle nuove -----
    # AGENTS.md (idempotent, no overwrite).
    agents_md = vault_path / "AGENTS.md"
    if not agents_md.exists():
        if auto_apply:
            try:
                agents_md.write_text(
                    _render_agents_md(effective_vault_name),
                    encoding="utf-8",
                )
                files_created.append("AGENTS.md")
                logger.info("auto_organize.agents_md_created", path=str(agents_md))
            except OSError as exc:
                errors.append(f"FASE 4 write AGENTS.md failed: {exc}")
        else:
            files_created.append("AGENTS.md")

    # README.md (idempotent).
    readme_md = vault_path / "README.md"
    if not readme_md.exists():
        if auto_apply:
            try:
                readme_md.write_text(
                    _render_readme(effective_vault_name, "vuoto"),
                    encoding="utf-8",
                )
                files_created.append("README.md")
            except OSError as exc:
                errors.append(f"FASE 4 write README.md failed: {exc}")
        else:
            files_created.append("README.md")

    # _index.md per ogni cartella canonica (idempotent).
    for rel in _BASE_DIRECTORIES:
        index_path = vault_path / rel / "_index.md"
        if index_path.exists():
            continue
        if auto_apply:
            try:
                index_path.write_text(
                    _render_index(rel, effective_vault_name),
                    encoding="utf-8",
                )
                files_created.append(f"{rel}/_index.md")
            except OSError as exc:
                errors.append(f"FASE 4 write {rel}/_index.md failed: {exc}")
        else:
            files_created.append(f"{rel}/_index.md")

    # Contesto/chi-sono.md + strategia.md placeholder (idempotent).
    contesto_files = [
        ("Contesto/chi-sono.md", _render_contesto_chi_sono()),
        ("Contesto/strategia.md", _render_contesto_strategia()),
    ]
    for rel_str, content in contesto_files:
        target = vault_path / rel_str
        if target.exists():
            continue
        if auto_apply:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                files_created.append(rel_str)
            except OSError as exc:
                errors.append(f"FASE 4 write {rel_str} failed: {exc}")
        else:
            files_created.append(rel_str)

    # Giornaliero/attivi.md (idempotent).
    attivi = vault_path / "Giornaliero" / "attivi.md"
    if not attivi.exists():
        if auto_apply:
            try:
                attivi.parent.mkdir(parents=True, exist_ok=True)
                attivi.write_text(_render_attivi(), encoding="utf-8")
                files_created.append("Giornaliero/attivi.md")
            except OSError as exc:
                errors.append(f"FASE 4 write Giornaliero/attivi.md failed: {exc}")
        else:
            files_created.append("Giornaliero/attivi.md")

    # ----- FASE 5: Entity seed + Concepts + Glossario -----
    # Entity: merge cyber + sanita + extra (8+ entity totali, dedupe by slug).
    all_seed_entities: dict[str, EntitySeed] = {}
    for seed in (*_SEED_CYBER, *_EXTRA_SEED_AUTO_ORGANIZE):
        all_seed_entities.setdefault(seed.slug, seed)

    for slug, seed in all_seed_entities.items():
        entity_path = vault_path / "wiki" / "entities" / f"{slug}.md"
        if entity_path.exists():
            continue
        if auto_apply:
            try:
                entity_path.parent.mkdir(parents=True, exist_ok=True)
                entity_path.write_text(_render_entity_stub(seed), encoding="utf-8")
                files_created.append(f"wiki/entities/{slug}.md")
                logger.info(
                    "auto_organize.entity_seeded",
                    slug=slug,
                    ambito=seed.ambito_canonico,
                )
            except OSError as exc:
                errors.append(f"FASE 5 write wiki/entities/{slug}.md failed: {exc}")
        else:
            files_created.append(f"wiki/entities/{slug}.md")

    # Concepts seed.
    for concept in _CONCEPT_SEEDS:
        concept_path = vault_path / "wiki" / "concepts" / f"{concept.slug}.md"
        if concept_path.exists():
            continue
        if auto_apply:
            try:
                concept_path.parent.mkdir(parents=True, exist_ok=True)
                concept_path.write_text(_render_concept_stub(concept), encoding="utf-8")
                files_created.append(f"wiki/concepts/{concept.slug}.md")
            except OSError as exc:
                errors.append(f"FASE 5 write wiki/concepts/{concept.slug}.md failed: {exc}")
        else:
            files_created.append(f"wiki/concepts/{concept.slug}.md")

    # Glossario canonico (sovrascrive _index.md placeholder se gia creato vuoto
    # in FASE 4: Conv. 47 single source of truth = glossario sostantivo > placeholder).
    glossario_path = vault_path / "wiki" / "glossari" / "_index.md"
    glossario_content = _render_glossario_index(effective_vault_name)
    # Sovrascrivi SOLO se contenuto attuale e' il placeholder generico (linea
    # "Indice della cartella `wiki/glossari/`"). Altrimenti rispetta esistente.
    should_write_glossario = False
    if not glossario_path.exists():
        should_write_glossario = True
    else:
        try:
            current = glossario_path.read_text(encoding="utf-8")
            if "Indice della cartella `wiki/glossari/`" in current:
                should_write_glossario = True
        except (OSError, UnicodeDecodeError):
            pass

    if should_write_glossario:
        if auto_apply:
            try:
                glossario_path.parent.mkdir(parents=True, exist_ok=True)
                glossario_path.write_text(glossario_content, encoding="utf-8")
                files_created.append("wiki/glossari/_index.md")
                logger.info(
                    "auto_organize.glossario_created",
                    path=str(glossario_path),
                    rows=len(_GLOSSARIO_SEED_ROWS),
                )
            except OSError as exc:
                errors.append(f"FASE 5 write wiki/glossari/_index.md failed: {exc}")
        else:
            files_created.append("wiki/glossari/_index.md")

    organized = bool(directories_created or files_created or files_moved)

    logger.info(
        "auto_organize.complete",
        path=str(vault_path),
        organized=organized,
        directories_created_count=len(directories_created),
        files_created_count=len(files_created),
        files_moved_count=len(files_moved),
        files_backed_up_count=len(files_backed_up),
        files_skipped_count=len(files_skipped),
        errors_count=len(errors),
    )

    return AutoOrganizeResult(
        organized=organized,
        directories_created=tuple(directories_created),
        files_created=tuple(files_created),
        files_moved=tuple(files_moved),
        files_backed_up=tuple(files_backed_up),
        files_skipped=tuple(files_skipped),
        errors=tuple(errors),
    )
