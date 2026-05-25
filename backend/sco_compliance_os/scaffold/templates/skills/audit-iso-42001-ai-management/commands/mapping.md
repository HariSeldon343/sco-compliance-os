---
description: "Matrice cross-framework"
---

# /mapping — Matrice cross-framework

## Uso
`/mapping [tema|tutto]`

## Quando
Per disporre, su un tema o su tutto l'AIMS, dei rinvii incrociati tra ISO/IEC 42001, Reg. (UE) 2024/1689 (AI Act), Legge 132/2025, ISO/IEC 27001:2022, GDPR, NIS2 (D.Lgs. 138/2024). È lo strumento di riferimento per evitare duplicazioni in organizzazioni con più sistemi di gestione.

## Pre-requisiti

- Scoping regolatorio (`/scope`).
- Conoscenza dei framework già attivi nell'organizzazione (27001, GDPR, NIS2).

## Output

Tabella markdown + esportabile .xlsx. Riga per tema; colonna per framework.

### Temi coperti di default

1. **Governance e politiche**
2. **Ruoli e responsabilità**
3. **Risk assessment**
4. **Data governance**
5. **Documentazione tecnica**
6. **Log ed event tracking**
7. **Trasparenza verso utenti**
8. **Sorveglianza umana**
9. **Accuratezza, robustezza, cybersecurity**
10. **Gestione dei fornitori**
11. **Gestione degli incidenti**
12. **Post-market monitoring**
13. **Gestione delle non conformità**
14. **Audit interni e riesame direzione**
15. **Formazione e consapevolezza**

### Struttura della matrice

| Tema | ISO 42001 | AI Act | Legge 132 | ISO 27001 | GDPR | NIS2 |
|------|-----------|--------|-----------|-----------|------|------|
| Governance e politiche | 5.2, 5.3, A.2.2, A.3.2 | Art. 17 QMS | Art. 3 principi; Art. 19-20 autorità | 5.2, 5.3, A.5.1 | Art. 5(2), Art. 24 | Art. 20-21 |
| Risk assessment | 6.1.2, 6.1.3, A.5.2 | Art. 9 RMS | Art. 3 principi di proporzionalità | 6.1.2-3, A.8.2 | Art. 35 DPIA | Art. 21 |
| Data governance | A.7.2-A.7.6 | Art. 10 | Art. 3 lett. d trasparenza, tracciabilità | A.5.12, A.8.11 | Art. 5, 6, 9, 10, 24, 25 | Art. 21.2 lett. g |
| Documentazione tecnica | A.6.2.3, A.6.2.7, A.8.2 | Art. 11 + All. IV | Art. 3 (comprensibilità) | A.5.37 | Art. 30 registri | Art. 21.2 lett. i |
| Log / eventi | A.6.2.8 | Art. 12 | — | A.8.15 | Art. 30 | Art. 21.2 lett. j |
| Trasparenza | A.8.3 | Art. 13, 50 | Art. 3 lett. d; Art. 7-15 settori | A.5.13 | Art. 13-14 | — |
| Sorveglianza umana | A.9.2-A.9.4 | Art. 14 | Art. 3 lett. f | A.5.2 segregation | Art. 22 | — |
| Accuratezza/robustezza/cybersecurity | A.6.2.4, A.6.2.6 | Art. 15 | Art. 3 lett. g cybersecurity | Intera A.8 | Art. 32 | Art. 21.2 lett. a-l |
| Fornitori | A.10.2, A.10.3 | Art. 25 (AI Act) | — | A.5.19-A.5.23 | Art. 28 DPA | Art. 21.2 lett. d supply chain |
| Incidenti gravi | A.6.2.6, A.8.4 | Art. 73 | — | A.5.24-A.5.28 | Art. 33-34 | Art. 23 notifiche |
| Post-market | A.6.2.6 | Art. 72 | — | A.5.7 threat intel | — | Art. 23 monitoring |
| Non conformità | 10.2 | Art. 16 lett. j, Art. 20 | — | 10.2 | — | — |
| Audit interni | 9.2 | Art. 16 lett. f | — | 9.2 | — | Art. 21 |
| Riesame direzione | 9.3 | Art. 17 QMS | — | 9.3 | — | — |
| Formazione | A.4.6 | Art. 4 AI literacy | Art. 3 (informazione) | A.6.3 | Art. 39 DPO | Art. 20 responsabili e organo di gestione |

### Lettura della matrice

- Quando una cella ha rinvii in 27001/GDPR/NIS2, l'organizzazione può riutilizzare controlli esistenti aggiornandoli con i requisiti AIMS.
- Quando una cella è vuota in una colonna, quel framework non disciplina direttamente il tema.
- Il rinvio è puntuale: numero di articolo o numero di controllo/clausola.

## Regole operative

- La matrice va **personalizzata** per l'organizzazione: temi rilevanti, obblighi effettivi, settori attivati.
- I rinvii a Legge 132 sono principalmente di principio e di governance: i settori Art. 7-15 attivano obblighi aggiuntivi documentabili in una sezione dedicata.
- Non trattare i rinvii come sovrapposizione 1:1. Un articolo AI Act può attivare più controlli 42001 e viceversa.
- Quando emergono conflitti tra framework (es. retention log AI Act Art. 12 vs minimizzazione GDPR), risolverli sul piano normativo più stringente (es. retention prevale se fondata su base legale).

## Documenti collegati

- `../references/matrice-cross-framework.md`
- `../references/iso42001-2023.md`
- `../references/ai-act-2024.md`
- `../references/legge-132-2025.md`
