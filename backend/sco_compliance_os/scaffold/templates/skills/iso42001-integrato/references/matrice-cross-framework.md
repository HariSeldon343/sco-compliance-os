# Reference — Matrice cross-framework

Matrice di riferimento centralizzata. Usata da `/mapping`, `/gap`, `/soa`, `/audit`.

## Framework considerati

| Sigla | Framework | Natura |
|-------|-----------|--------|
| **V (ISO 42001)** | ISO/IEC 42001:2023 — AIMS | Volontario, certificabile |
| **U (AI Act)** | Reg. (UE) 2024/1689 | Cogente UE |
| **N (Legge 132)** | L. 132/2025 italiana | Cogente nazionale |
| **27001** | ISO/IEC 27001:2022 — SGSI | Volontario, certificabile |
| **GDPR** | Reg. (UE) 2016/679 | Cogente UE |
| **NIS2** | D.Lgs. 138/2024 | Cogente nazionale (recepimento UE) |
| **23894** | ISO/IEC 23894:2023 | Volontario (linee guida) |
| **38507** | ISO/IEC 38507:2022 | Volontario (governance CdA) |

## Matrice tematica espansa

### Governance e politiche
| Tema | 42001 | AI Act | L. 132 | 27001 | GDPR | NIS2 | 38507 |
|------|-------|--------|--------|-------|------|------|-------|
| Politica AI | 5.2, A.2.2-A.2.4 | Art. 17 | Art. 3, Art. 19 | 5.2 | — | — | 5.1 |
| Ruoli e responsabilità | 5.3, A.3.2-A.3.3 | Art. 3 ruoli | Art. 20 | 5.3, A.5.2 | Art. 24, 26, 28, 37-39 | Art. 20-21 | 5.2 |
| Risorse | 7.1, A.4.2-A.4.6 | Art. 17 lett. c | — | 7.1, A.6.1 | — | Art. 21 | — |

### Rischio e impatti
| Tema | 42001 | AI Act | L. 132 | 27001 | GDPR | NIS2 |
|------|-------|--------|--------|-------|------|------|
| Risk assessment IA | 6.1.2, A.5.2 | Art. 9 | Art. 3 | 6.1.2, 8.2 | Art. 35 DPIA | Art. 21 |
| Trattamento rischi | 6.1.3 (SoA punto d) | Art. 9 c. 5 | — | 6.1.3 | Art. 35-36 | Art. 21 |
| AIIA | 6.1.4, A.5.2-A.5.5 | — (copre indirettamente) | Art. 3 lett. b | — | Art. 35 (DPIA separata) | — |
| FRIA | — | Art. 27 | Art. 7-15 settori | — | Art. 35 overlap | — |
| Appetito al rischio | 5.2 politica | — | — | 6.1.2, 5.2 | — | Art. 20 |

### Ciclo di vita IA
| Tema | 42001 | AI Act | L. 132 | 27001 | GDPR |
|------|-------|--------|--------|-------|------|
| Obiettivi sviluppo responsabile | A.6.1.2-A.6.1.3 | — | Art. 3 | A.8.25 | Privacy by design Art. 25 |
| Requisiti e specifiche | A.6.2.2 | Art. 11 + All. IV | — | A.8.26 | Art. 25 |
| Design e sviluppo | A.6.2.3 | Art. 10 data governance | — | A.8.27 | Art. 25 |
| V&V | A.6.2.4 | Art. 15 accuratezza | — | A.8.29 | — |
| Deployment | A.6.2.5 | Art. 16 fornitore | — | A.8.31 | — |
| Esercizio e monitoraggio | A.6.2.6 | Art. 72 PMM | — | A.8.16 | Art. 32 |
| Documentazione tecnica | A.6.2.7, A.8.2 | Art. 11 + All. IV | — | A.5.37 | Art. 30 |
| Log | A.6.2.8 | Art. 12 | — | A.8.15 | Art. 30 |

### Dati
| Tema | 42001 | AI Act | L. 132 | GDPR |
|------|-------|--------|--------|------|
| Dati sviluppo e miglioramento | A.7.2 | Art. 10 | Art. 3 | Art. 5, 6, 9, 10 |
| Acquisizione | A.7.3 | Art. 10 c. 2 | Art. 3 | Art. 6, 13-14 |
| Qualità | A.7.4 | Art. 10 c. 3 | Art. 3 | Art. 5 |
| Provenienza | A.7.5 | Art. 10 c. 4 | — | Art. 13-14 |
| Preparazione | A.7.6 | Art. 10 c. 5 | — | Art. 25 |

### Trasparenza e parti interessate
| Tema | 42001 | AI Act | L. 132 | GDPR |
|------|-------|--------|--------|------|
| Documentazione di sistema | A.8.2 | Art. 11 + All. IV | — | Art. 30 |
| Informazioni agli utenti | A.8.3 | Art. 13 istruzioni d'uso | Art. 7-15 settori | Art. 13-14 |
| Segnalazione incidenti esterni | A.8.4 | Art. 73 | Art. 19-20 | Art. 33-34 |
| Comunicazione interessati | A.8.5 | Art. 26 c. 11 | Art. 9, 11, 14 | Art. 13-14 |
| Etichettatura deepfake | — | Art. 50 c. 4 | — | — |
| Chatbot transparency | — | Art. 50 c. 1 | — | — |

### Uso responsabile
| Tema | 42001 | AI Act | L. 132 | GDPR |
|------|-------|--------|--------|------|
| Processi uso responsabile | A.9.2 | Art. 26 | Art. 7-15 | Art. 5 liceità |
| Obiettivi uso responsabile | A.9.3 | Art. 26 c. 1 | — | — |
| Uso previsto (intended use) | A.9.4 | Art. 13 c. 3 | — | — |

### Terze parti
| Tema | 42001 | AI Act | 27001 | GDPR | NIS2 |
|------|-------|--------|-------|------|------|
| Allocazione responsabilità catena | A.10.2 | Art. 25 | A.5.19 | Art. 26 | Art. 21.2 lett. d |
| Fornitori | A.10.3 | Art. 25 | A.5.20-A.5.22 | Art. 28 DPA | Art. 21.2 lett. d |
| Clienti | A.10.4 | Art. 13, 16 lett. l | A.5.23 | Art. 28 | — |

### Ciclo PDCA e miglioramento
| Tema | 42001 | AI Act | 27001 | NIS2 |
|------|-------|--------|-------|------|
| Audit interno | 9.2 | Art. 16 lett. f | 9.2 | Art. 21 |
| Riesame direzione | 9.3 | Art. 17 | 9.3 | — |
| Non conformità e azioni correttive | 10.2 | Art. 20 | 10.2 | — |
| Miglioramento continuo | 10.1 | — | 10.1 | — |

### Incidenti e PMM
| Tema | 42001 | AI Act | GDPR | NIS2 | Legge 90 |
|------|-------|--------|------|------|----------|
| Post-market monitoring | A.6.2.6 | Art. 72 | — | Art. 23 | — |
| Incidenti gravi | A.8.4 | Art. 73 (15gg / 2gg / 10gg) | Art. 33-34 (72h) | Art. 23 (24h/72h) | PA notifiche |
| Data breach | — | — | Art. 33-34 | Art. 23 | — |

### Sanzioni
| Framework | Massimo |
|-----------|---------|
| AI Act — pratiche vietate | 35M€ o 7% fatturato |
| AI Act — obblighi alto rischio/GPAI/trasparenza | 15M€ o 3% |
| AI Act — informazioni false | 7,5M€ o 1% |
| GDPR | 20M€ o 4% (gravi) |
| NIS2 — essenziali | 10M€ o 2% |
| NIS2 — importanti | 7M€ o 1,4% |
| Legge 90/2024 — PA | 25-125k€ |

## Note di lettura

- Il mapping non è 1:1: un controllo 42001 può intercettare più articoli di AI Act e viceversa.
- GDPR e AI Act si applicano **cumulativamente** quando il sistema IA tratta dati personali.
- NIS2 e AI Act si intersecano per cybersecurity sui soggetti essenziali/importanti.
- Legge 132 non duplica: **rafforza** settori strategici italiani con obblighi specifici.
