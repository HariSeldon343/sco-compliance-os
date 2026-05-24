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

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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
    subtype_line = (
        f"entity_subtype: {seed.entity_subtype}\n" if seed.entity_subtype else ""
    )
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
        raise ValueError(
            f"Template '{template}' non ammesso. Valori: {VALID_TEMPLATES}"
        )
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
    for rel in _BASE_DIRECTORIES:
        target = vault_path / rel
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
_OPT_IN_FOLDERS: frozenset[str] = frozenset(
    {"Contesto", "Business", "raw", "wiki", "CLAUDE.md"}
)


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
            "missing_auto": [
                f for f in _CANONICAL_ROOT_FOLDERS if f in _AUTO_CREATE_FOLDERS
            ],
            "missing_opt_in": [
                f for f in _CANONICAL_ROOT_FOLDERS if f in _OPT_IN_FOLDERS
            ],
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

    is_sco_structure = (
        not missing_folders and has_claude_md and has_log_dir
    )

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
    missing_before = tuple(inspect["missing_folders"])  # type: ignore[arg-type]

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
    auto_to_create: list[str] = list(inspect["missing_auto"])  # type: ignore[arg-type]
    opt_in_to_create: list[str] = (
        list(inspect["missing_opt_in"]) if include_opt_in else []  # type: ignore[arg-type]
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
