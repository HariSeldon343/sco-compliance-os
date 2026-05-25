# Comandi Rapidi — RiskManager-Agent

Ogni comando include CoVe integrato. Output formali in .docx.

---

## Risk Assessment

### `/risk [area/processo]`
Risk assessment per area o processo specifico. Output: registro rischi con codice, descrizione, cause, conseguenze, probabilità, impatto (multidimensionale), rischio inerente, controlli, rischio residuo, confronto con soglia, piano trattamento.

### `/erm [scope]`
Assessment ERM completo o per perimetro. Copre tutte le categorie di rischio. Include analisi contesto, mappatura, valutazione, prioritizzazione, top risk.

### `/bia [processo]`
Business Impact Analysis. Output: processi critici con MTPD, RTO, RPO, risorse necessarie, impatto nel tempo, classificazione criticità.

### `/stress-test [scenario]`
Definizione scenari di stress test (storico, predittivo, multi-factor). Include impatto stimato e azioni di mitigazione.

### `/esg-risk`
Assessment rischi ESG (Environmental, Social, Governance) con metriche, rating, integrazione in processi decisionali.

---

## Documentazione

### `/registro`
Genera o aggiorna il registro dei rischi. Struttura: ID, Categoria, Descrizione, Cause, Conseguenze, Probabilità, Impatto, Rischio inerente, Controlli, Rischio residuo, Risk owner, Trattamento, KRI, Stato.

### `/matrice`
Matrice probabilità × impatto con heat map. Posizionamento di tutti i rischi dal registro. Distinzione inerente/residuo.

### `/trattamento [rischio]`
Piano di trattamento per rischio specifico o per tutti i rischi sopra soglia. Azione, owner, scadenza, risorse, KRI, stato.

### `/kri [area]`
Set di Key Risk Indicators per area. Include: indicatore, definizione, fonte dati, frequenza, soglia warning/critica, owner.

### `/appetite`
Framework risk appetite con soglie per categoria di rischio. Include risk appetite statement, tolerance per rischio, capacity.

### `/3lod`
Modello Three Lines of Defense personalizzato per l'organizzazione. Ruoli, responsabilità, flussi informativi.

---

## Policy e procedure

### `/policy [tema]`
Bozza policy: politica gestione rischi, politica risk appetite, politica continuità operativa, politica rischio cyber, politica ESG risk.

### `/procedura [tema]`
Bozza procedura: risk assessment, gestione incidenti, BIA, escalation, monitoraggio KRI, reporting rischi, Monte Carlo operativo.

---

## Report

### `/report [tipo]`
Report rischi differenziato:
- `cda` → Report annuale per Consiglio di Amministrazione
- `comitato` → Report per Comitato Controllo e Rischi
- `management` → Report operativo per management
- `esg` → Rendicontazione rischi ESG
- `top-risk` → Focus sui rischi a priorità critica/elevata

---

## Audit

### `/nc [descrizione]`
Formulazione rilievo audit con classificazione, clausola/riferimento, evidenze, analisi cause.

---

## CoVe

| `/cove` | Report CoVe completo |
| `/cove-check [claim]` | Verifica singolo claim |
| `/cove-report` | Report sintetico |

---

## Note operative

1. **Scala**: usa SEMPRE la scala dell'organizzazione. Se non disponibile, proponi scala default dichiarandola provvisoria
2. **Knowledge base**: analizza documenti caricati PRIMA dell'output
3. **Template**: se esiste nella KB, usalo preservando layout
4. **Risk owner**: ogni rischio sopra soglia DEVE avere un risk owner
5. **Coerenza**: registro ↔ matrice ↔ piano trattamento ↔ KRI ↔ report
6. **Segnaposti**: `[DA INSERIRE — ...]` per dati mancanti; `[DA VERIFICARE — ...]` per claim non verificabili
