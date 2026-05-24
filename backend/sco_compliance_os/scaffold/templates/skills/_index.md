---
type: skill-catalog
title: "Catalogo skill pre-installate SCO Compliance OS"
version: 1.0.0
language: it
tags: [catalog, skills, compliance, audit, consulenza]
---

# Catalogo skill pre-installate SCO Compliance OS

Skill di consulenza, audit, redazione documentale e stile pre-installate nel bundle di SCO Compliance OS. Sono replicate dal vault Antonio Amodeo (cybersecurity, qualità sanitaria, ingegneria clinica, compliance normativa) e disponibili out-of-the-box per ogni vault cliente registrato.

Le skill si attivano automaticamente in base al frontmatter `description` di ciascun SKILL.md (trigger keywords) oppure manualmente con la sintassi `/nome-skill`.

---

## Sistema (onboarding e ottimizzazione vault)

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[os-setup]] | Profilazione utente al primo register vault. Raccoglie ruolo, ambito di lavoro, clienti chiave e preferenze di stile per personalizzare l'agente. | `auto_trigger: vault_registered` |
| [[os-ottimizzatore]] | Ottimizza la struttura del vault SCO. Riorganizza file, propone refactoring, verifica coerenza con la filing rule. | `/ottimizza`, `/audit-vault` |

---

## Cybersecurity, SGSI, NIS 2

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[cybernis-sgsi-agent]] | Lead Auditor e consulente per cybersicurezza, audit ISO 27001+27017+27018, conformità NIS2/GDPR/Legge 90-2024/Legge 132-2025/AI Act. Redazione documentazione SGSI completa (policy, procedure, manuali, registri, SoA, RVE, PDV, PAC, PDA). | `/rve`, `/pdv`, `/nc`, `/sm`, `/checklist`, `/assessment`, `/gap`, `/policy`, `/procedura`, `/risk`, `/soa`, `/apertura`, `/chiusura`, `/pda` |
| [[cybernis-agent]] | Consulente NIS2 (D.Lgs. 138/2024), Legge 90/2024, UNI/PdR 174:2024, NIST CSF 2.0, ISO 22301, GDPR. Assessment NIS2, gap analysis Art. 21, BIA, BCP/DRP, gestione incidenti CSIRT, notifica ACN. | `/assessment`, `/gap`, `/audit`, `/risk`, `/checklist`, `/nc`, `/sm`, `/policy`, `/procedura`, `/piano`, `/soa`, `/bcp`, `/incidente`, `/riesame`, `/cove` |
| [[cybernis-integrato]] | Orchestratore senior per quesiti cross-framework ISO 27001 + ISO 20000-1 + NIS 2. Audit congiunti SGSI+SMS, gap analysis a tre framework, SoA estesa, procedure incidenti unificate, supplier management ICT integrato. | `/audit-congiunto`, `/gap-tre-framework`, `/soa-esteso-sms`, `/incidente-unificato`, `/continuita-integrata`, `/matrice-tre-framework`, `/riesame-integrato`, `/risk-integrato`, `/supplier-integrato`, `/policy-integrata`, `/procedura-integrata`, `/route` |
| [[ism-cybernis-agent]] | Lead Auditor e consulente senior per ISO/IEC 20000-1:2018 (ITSM), integrato con SGSI 27001 + NIS2. Service management, SLA/OLA/KPI, incident/problem/change/configuration management, CMDB, service continuity, supplier management ICT. | `/gap-sms`, `/gap-integrato`, `/assessment`, `/checklist-sms`, `/nc`, `/sm`, `/procedura`, `/sla`, `/catalogo-servizi`, `/cmdb`, `/incidente-integrato`, `/continuita-servizio`, `/matrice-sms`, `/kpi`, `/riesame-sms`, `/audit`, `/risk-sms`, `/policy`, `/rve`, `/soa`, `/cove` |
| [[iso42001-integrato]] | Lead Auditor AIMS ISO/IEC 42001:2023 + Reg. UE 2024/1689 (AI Act) + Legge 132/2025. Gap analysis, scoping sistema IA, classificazione rischio AI Act, pratiche vietate Art. 5, sistemi ad alto rischio Allegato III, obblighi fornitore/deployer, GPAI, post-market monitoring, AIIA, FRIA, SoA 39 controlli Appendice A. | `/scope`, `/rischio-regolatorio`, `/ruoli`, `/gap`, `/aiia`, `/fria`, `/soa`, `/mapping`, `/nc`, `/audit`, `/roadmap`, `/settori`, `/autorita`, `/sanzioni`, `/cove` |
| [[ict-doc-reorganizer]] | Riorganizza e classifica cartelle di documentazione ICT security secondo tassonomia standardizzata 137-documenti (20 process areas + 10 document types). Gap analysis copertura NIS2/ISO 27001/FNCS 2025/ACN/AgID/GDPR. | Trigger: "indice documentale", "riorganizzazione documentale", "sicurezza ICT", "gap analysis" |

---

## Qualità sanitaria e accreditamento

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[qualita-sanita-agent]] | Lead Auditor e consulente ISO 9001:2015 per il settore sanitario italiano. Audit, SGQ sanitario, accreditamento istituzionale, procedure/protocolli/istruzioni operative, manuali qualità, carte servizi, PDTA, risk management clinico, KPI sanitari, riesame direzione, ricerca linee guida SNLG. | `/rve`, `/pdv`, `/nc`, `/sm`, `/checklist`, `/procedura`, `/protocollo`, `/istruzione`, `/politica`, `/mappa-processi`, `/indicatori`, `/riesame`, `/risk`, `/gap`, `/audit-clinico`, `/linee-guida`, `/cove` |
| [[sgq-sanita-9001]] | SGQ sanitario, procedure ISO 9001 per ospedali, case di cura, RSA, poliambulatori, laboratori. Specializzata in redazione documentale (manuali, procedure, IO, registri, modulistica). | `/manuale`, `/procedura`, `/istruzione-operativa`, `/modulo`, `/registro` |
| [[sgq-rspp-sanita]] | Integrato qualità sanitaria + sicurezza sul lavoro D.Lgs. 81/2008 per strutture sanitarie. DVR settoriale, gestione rischio clinico + occupazionale unificata, procedure integrate. | `/dvr-sanitario`, `/procedure-integrate`, `/checklist-integrata`, `/gap-integrato` |

---

## Sicurezza sul lavoro

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[rspp-sanita-81]] | RSPP per strutture sanitarie. D.Lgs. 81/2008, valutazione rischi specifici sanitari (biologico, chimico, radiologico, MMC, ergonomico, stress), DVR, DUVRI, formazione lavoratori, sorveglianza sanitaria. | `/dvr`, `/duvri`, `/valutazione-rischio`, `/formazione`, `/sorveglianza`, `/checklist-81`, `/checklist-sanitario` |
| [[rivelazione-incendi-agent]] | Consulente progettazione IRAI (Impianti Rivelazione e Allarme Incendi) ai sensi UNI 9795:2013, EN 54, DM 1/9/2021 + DM 2/9/2021 + DM 3/9/2021 Codice PI. Verifica criteri rivelatori, architettura sistema, documentazione manutenzione. | `/progettazione-irai`, `/criteri-rivelatori`, `/architettura-irai`, `/uni-9795`, `/codice-pi` |

---

## Risk management

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[risk-manager-agent]] | Consulente e Risk Manager senior per Enterprise Risk Management (ISO 31000), cybersecurity risk (ISO 27005), rischio operativo, finanziario, ESG, compliance. COSO ERM, registro rischi, matrice probabilità-impatto, risk appetite, risk treatment, BIA, BCP/DRP. | `/risk`, `/erm`, `/bia`, `/registro`, `/matrice`, `/trattamento`, `/assessment`, `/stress-test`, `/policy`, `/procedura`, `/report`, `/cove` |

---

## Appalti pubblici

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[appalti-pubblici-agent]] | Consulente senior appalti pubblici D.Lgs. 36/2023 e D.Lgs. 209/2024. Bandi, disciplinari, capitolati, schemi contratto, CME, determine, verbali commissione, supporto RUP, OEPV, anomalia offerte, revisione atti gara, gap analysis, subappalto, avvalimento, RTI, clausole sociali, CAM, garanzie, stand-still, esecuzione contrattuale, penali, contenzioso TAR, ANAC bandi tipo. | `/bando`, `/disciplinare`, `/capitolato`, `/schema-contratto`, `/determina`, `/verbale`, `/cme`, `/rup`, `/commissione`, `/revisione-gara`, `/gap-appalti`, `/offerta`, `/anomalia`, `/subappalto`, `/penali`, `/contenzioso`, `/checklist-gara` |

---

## Redazione documentale e stile

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[amodeo-voice]] | Profilo stilistico consulente normativo italiano (registro formale/professionale-collegiale/formale leggero/formale fermo). Tono, lessico, struttura, principi trasversali per report, note tecniche, relazioni, email, policy, comunicazioni istituzionali, deliverable di audit. Layer stilistico integrabile con tutte le skill specialistiche. | `/voce`, `/stile`, `/amodeo-voice` |
| [[humanizer]] | Rimuove i pattern di scrittura AI-generated da testi (em-dash decorativo, rule of three, AI vocabulary, negative parallelism, inflated symbolism, "delve into", "leverage/sfruttare"). Base: Wikipedia "Signs of AI writing" guide. Pass automatico in chiusura di ogni deliverable lungo. | Trigger: editing testo, "rendi piu umano", "rimuovi pattern AI" |
| [[disaiizzatore-normativo]] | Variante severa di humanizer per testi italiani tecnico-normativi (procedure ISO, RVE/DDV/PDV, gap analysis, perizie CTU, note tecniche). Riscrive in chiaro + report sidecar separato di giustificazione modifiche, senza lasciare commenti o tracked changes nel documento finale. | `/disaiizza`, `/audit-aiizzazione` |
| [[creatore-perizia]] | Crea perizie tecniche e relazioni di consulenza tecnica in piena forma peritale (frontespizio, indice paginato, premessa e quesito, documentazione esaminata, accertamenti, conclusioni con risposta al quesito, riferimenti normativi). Multi-dominio: cybersecurity, digital forensics, compliance, GDPR, sanita, antincendio, qualita, sicurezza sul lavoro. Modalita white-label supportata. | `/perizia` |
| [[docx-style-cloner]] | Clona stile editoriale completo di un documento Word di riferimento (font, paragrafi, stili nominati, sezioni, margini, header/footer con immagini) per produrre un nuovo .docx con contenuto diverso ma identica veste grafica. Pipeline 6 step "template + body replacement" + Q&A pre-build + triple check zip integrity. | `/clona-stile`, `/clona-docx` |
| [[document-analyzer]] | Agente autonomo di analisi documentale ricorsiva. Scandaglia ogni file di una cartella master (incluse sottocartelle) e produce context-map.md (mappa contesto ultra-dettagliata) + evals.md (scheda autovalutazione 10 criteri). Supporta PDF, DOCX, XLSX, PPTX, immagini, TXT, CSV, JSON, XML, MD. | `/context-map`, `/analisi-cartella`, `/mappa-documenti`, `/document-scan` |

---

## Workflow e metodologia

| Skill | Scopo | Comandi/Trigger |
|---|---|---|
| [[gsd-workflow]] | Flusso di lavoro GSD ("Get Shit Done") a 5 fasi per OGNI cantiere non banale: (1) inquadramento e roadmap, (2) plan di fase, (3) esecuzione, (4) verifica con gate, (5) chiusura milestone e retrospettiva. Cornice operativa che orchestra le regole permanenti del vault SCO (GOAL, VERIFY-OR-REDO, ASK-USER, multi-agent on-demand, QI190, tracciatura Conv. 41, smoke Conv. 46). | `/gsd`, "imposta il cantiere", "roadmap" |

---

## Note operative

- **Strict first match**: una skill si attiva al primo trigger keyword corrispondente nella richiesta utente. Per disambiguare casi multi-dominio (es. quesito che intercetta sia `cybernis-sgsi-agent` sia `iso42001-integrato`), invoca esplicitamente con `/nome-skill`.
- **Layer stilistico trasversale**: `amodeo-voice` è chiamata automaticamente dalle skill specialistiche per il registro formale dei deliverable. `humanizer` e `disaiizzatore-normativo` sono pass di chiusura permanenti.
- **Integrazione cross-skill**: orchestratori come `cybernis-integrato` (3 framework cyber) e `sgq-rspp-sanita` (qualità + sicurezza sanitaria) compongono dinamicamente skill specialistiche per quesiti cross-dominio.
- **Riferimenti documentali**: ogni skill ha la propria cartella `references/`, `commands/`, `templates/`, `scripts/` con il materiale operativo. Consulta le sottocartelle della skill per dettagli.
- **Estensione catalogo**: nuove skill installate via `claude skills install <repo>` compaiono in `.claude/skills/<nome>/` e si auto-registrano nel runtime. Per aggiungerle a questo catalogo, aggiungi una riga nella categoria appropriata.

---

Part of [[Skill/_index]]
