# Classification Rules

## Document Type Detection (TIPOLOGIA)

### Filename keyword patterns

| Type | Code | Filename keywords (IT) | Filename keywords (EN) |
|------|------|----------------------|----------------------|
| Policy | POL | policy, politica, principi, indirizzo | policy, principles, directive |
| Processo | PRC | processo, workflow, flusso | process, workflow, flow |
| Procedura | PRO | procedura, modalità operative, istruzioni | procedure, SOP, instructions |
| Linea Guida | LG | linea guida, guida, raccomandazioni, best practice | guideline, guide, best practice |
| Istruzione Operativa | IO | istruzione operativa, step-by-step, how-to | operating instruction, how-to |
| Manuale | MAN | manuale, handbook, manual | manual, handbook |
| Playbook | PLB | playbook, runbook, response plan | playbook, runbook |
| Piano | PIA | piano, plan, programma, roadmap | plan, program, roadmap |
| Registro | REG | registro, inventario, catalogo, elenco, log | register, inventory, catalog, log |
| Report | REP | report, relazione, dashboard, KPI | report, dashboard, summary |
| Documento | DOC | documento, statement, dichiarazione, org | document, statement, charter |

### Content structure indicators

- **Policy**: Short (5-15 pages), declarative tone, "l'organizzazione si impegna", approved by board/management
- **Processo**: Flowcharts, RACI matrices, swim lanes, input/output definitions
- **Procedura**: Numbered steps, "chi fa cosa quando", operational detail, checklists
- **Linea Guida**: Advisory tone, "si raccomanda", "è consigliabile", optional measures
- **Playbook**: Scenario-based, decision trees, escalation paths, "in caso di"
- **Piano**: Timeline, milestones, budget, resource allocation, Gantt-like structures
- **Registro**: Tabular data, inventories, lists with status fields, date columns
- **Report**: Metrics, charts, period references, "nel periodo", findings, recommendations

## Process Area Detection (PROCESSO)

### Keyword-to-process mapping

| Process Area | Key terms in content |
|-------------|---------------------|
| 01. GOVERNANCE E STRATEGIA | governance, comitato sicurezza, direzione, organizzazione, ruoli, stakeholder, strategia |
| 02. GESTIONE DEL RISCHIO | risk assessment, analisi rischio, trattamento rischio, BIA, impatto, probabilità, SoA |
| 03. GESTIONE DEGLI ASSET | asset, inventario, CMDB, hardware, software, servizi ICT, classificazione informazioni |
| 04. CONTROLLO DEGLI ACCESSI | accesso, autenticazione, autorizzazione, MFA, password, privileged, IAM, RBAC |
| 05. PROTEZIONE DEI DATI | crittografia, cifratura, backup, DLP, data loss, protezione dati, mascheramento |
| 06. SICUREZZA DELLE RETI | rete, network, firewall, segmentazione, VPN, DMZ, IDS, IPS, WiFi, perimetro |
| 07. SICUREZZA ENDPOINT | endpoint, antivirus, EDR, patching, hardening, configurazione sicura, BYOD |
| 08. GESTIONE VULNERABILITÀ | vulnerabilità, vulnerability, scanning, penetration test, CVE, patch, remediation |
| 09. CHANGE MANAGEMENT | change management, cambiamento, rilascio, deploy, configurazione, baseline |
| 10. SICUREZZA APPLICATIVA | applicazione, software development, SDLC, SAST, DAST, code review, DevSecOps, API |
| 11. SICUREZZA FISICA | fisica, accesso fisico, videosorveglianza, CED, data center, ambientale, incendio |
| 12. MONITORAGGIO E DETECTION | monitoraggio, SIEM, SOC, logging, detection, allarme, correlazione, anomalia |
| 13. INCIDENT MANAGEMENT | incidente, incident, breach, contenimento, eradicazione, risposta, notifica, forensic |
| 14. CONTINUITÀ OPERATIVA | continuità, BCP, DR, disaster recovery, RPO, RTO, failover, crisi |
| 15. THREAT INTELLIGENCE | threat intelligence, minaccia, IoC, feed, TTP, MITRE, CTI |
| 16. FORMAZIONE E AWARENESS | formazione, awareness, sensibilizzazione, training, phishing simulation, e-learning |
| 17. GESTIONE FORNITORI | fornitore, terza parte, supply chain, SLA, contratto, outsourcing, subappalto |
| 18. COMPLIANCE E AUDIT | audit, compliance, conformità, riesame, non conformità, azione correttiva, certificazione |
| 19. RISORSE UMANE | risorse umane, onboarding, offboarding, NDA, disciplinare, screening, cessazione |
| 20. MIGLIORAMENTO CONTINUO | miglioramento, PDCA, KPI, obiettivi, documentazione, lessons learned, riesame direzione |

## FNCS Function Detection

| Function | Indicators |
|----------|-----------|
| GV (Govern) | governance, policy, ruoli, organizzazione, strategia, compliance, audit, miglioramento |
| ID (Identify) | asset, rischio, inventario, classificazione, vulnerabilità, valutazione |
| PR (Protect) | protezione, controllo accessi, crittografia, formazione, sicurezza fisica, hardening |
| DE (Detect) | monitoraggio, detection, SIEM, logging, anomalia, allarme |
| RS (Respond) | risposta, incidente, contenimento, analisi, comunicazione, notifica |
| RC (Recover) | ripristino, recovery, continuità, disaster recovery, lessons learned |

## Normative Reference Patterns (regex)

```
ISO\s*27001[:.]?\s*([\d.]+|A\.\d+\.\d+)
NIS\s*2[:.]?\s*Art\.?\s*(\d+)
FNCS[:.]?\s*(GV|ID|PR|DE|RS|RC)[.\-]
ACN[-\s]*DET[:.]?\s*([A-Z]{2}\.[A-Z]{2}[-\d]*)
GDPR[:.]?\s*Art\.?\s*(\d+)
AgID[-\s]*MM[:.]?\s*ABSC\s*(\d+)
L\.?\s*90/2024[:.]?\s*Art\.?\s*(\d+)
D\.?\s*Lgs\.?\s*138/2024
```

## Confidence Score Calculation

Aggregate signals with weights:

| Signal | Weight |
|--------|--------|
| Filename match | 0.20 |
| Folder path match | 0.10 |
| Content semantic match | 0.40 |
| Normative reference match | 0.20 |
| Metadata match | 0.10 |

Final score = weighted sum of individual signal scores (each 0.0–1.0).

If content extraction fails (encrypted/corrupted), fall back to filename+path only (max achievable confidence: 0.30).

## Disambiguation Rules

1. When a document matches multiple process areas, prefer the area where the primary topic appears first and most frequently
2. When tipologia is ambiguous between POL and PRO, check document length: <15 pages and declarative = POL, >15 pages and operational = PRO
3. When cod_doc is ambiguous, prefer the code with higher PRIORITA (ALTA > MEDIA > BASSA)
4. If a document clearly belongs to a process area but matches no specific COD_DOC, classify as ORPHAN within that process area
5. Multi-language documents: prefer Italian title/content for classification
