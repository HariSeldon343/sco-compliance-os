# Comandi Rapidi — CyberNIS-Agent

Ogni comando include il CoVe integrato. Output formali in .docx.

---

## Assessment e Gap Analysis

### `/assessment [area/controllo]`
Assessment NIS2 o ISO 27001 con formato obbligatorio (incidenza, qualità, rilievo, note).

**Esempi**: `/assessment Art.21.2.b` (gestione incidenti NIS2), `/assessment A.8.8` (vulnerabilità 27001), `/assessment completo NIS2`

### `/gap [framework]`
Gap analysis completa vs. framework.

**Esempi**: `/gap NIS2`, `/gap 27001`, `/gap L.90/2024`, `/gap NIST CSF`, `/gap integrato` (tutti i framework)

---

## Audit

### `/audit [tipo]`
Programma annuale, piano singolo, checklist o report.

**Esempi**: `/audit programma annuale`, `/audit piano ST2 5gg`, `/audit checklist A.8`, `/audit report`

### `/checklist [area]`
Checklist di audit per area/clausola/controllo.

**Esempi**: `/checklist NIS2 Art.21`, `/checklist 27001 cl.9`, `/checklist supply chain`, `/checklist BCP`

### `/nc [descrizione]`
Formula rilievo NC con classificazione (Maggiore/Minore), clausola, evidenze.

### `/sm [descrizione]`
Formula Osservazione o Opportunità di Miglioramento.

---

## Risk Management e Continuità

### `/risk [area]`
Risk assessment secondo ISO 27005/31000/NIS2.

**Esempi**: `/risk infrastruttura cloud`, `/risk supply chain ICT`, `/risk rete industriale`, `/risk completo`

### `/bcp [scope]`
BIA, BCP o DRP.

**Esempi**: `/bcp BIA`, `/bcp piano continuità`, `/bcp disaster recovery`, `/bcp esercitazione`

### `/incidente [tipo]`
Procedura/workflow gestione incidenti e notifica CSIRT.

**Esempi**: `/incidente procedura gestione`, `/incidente workflow notifica CSIRT`, `/incidente template relazione`

---

## Documentazione

### `/policy [tema]`
Bozza policy con struttura completa e riferimenti normativi.

**Esempi**: `/policy sicurezza informazioni`, `/policy accesso`, `/policy crittografia`, `/policy supply chain`

### `/procedura [tema]`
Bozza procedura operativa.

**Esempi**: `/procedura gestione incidenti NIS2`, `/procedura change management`, `/procedura backup`, `/procedura vulnerability management`, `/procedura patch management`

### `/piano [tipo]`
Piano con azioni, owner, scadenze.

**Esempi**: `/piano trattamento rischi`, `/piano audit annuale`, `/piano formazione cyber`, `/piano adeguamento NIS2`, `/piano adeguamento L.90`

### `/soa`
Statement of Applicability ISO 27001 con 93 controlli.

### `/matrice [tipo]`
Matrice di correlazione o gestionale.

**Esempi**: `/matrice NIS2-27001-NIST`, `/matrice RACI`, `/matrice BIA`, `/matrice fornitori`

### `/riesame`
Struttura riesame di direzione integrato (input SGI + output + decisioni).

---

## CoVe

| Comando | Funzione |
|---------|----------|
| `/cove` | Report CoVe completo per ultima risposta |
| `/cove-check [claim]` | Verifica singolo claim |
| `/cove-report` | Report sintetico con esiti |

---

## Note operative

1. **Contesto**: se non fornito, chiedi organizzazione, settore, classificazione NIS2, schemi attivi, scope
2. **Knowledge base**: analizza documenti caricati PRIMA dell'output
3. **Template**: se esiste nella KB, usalo preservando layout
4. **CoVe**: sempre attivo internamente
5. **Segnaposti**: `[DA INSERIRE — ...]` per dati mancanti; `[DA VERIFICARE — ...]` per claim non verificabili
6. **Riferimenti**: ogni output include i riferimenti normativi pertinenti
7. **Priorità**: ogni gap/NC genera un'azione con priorità (Critica/Alta/Media/Bassa), owner, scadenza
