# Template — Serious Incident Report (AI Act Art. 73)

> Struttura coerente con Art. 73 AI Act e intersezioni con GDPR Art. 33, NIS2 Art. 23, Legge 90/2024.

---

# Segnalazione incidente grave — Sistema IA [Denominazione]

**Codice documento:** AIMS-INC-[aaaa]-[progressivo]
**Data di emissione report:** [gg/mm/aaaa hh:mm]
**Classificazione:** Interno / Riservato / Autorità
**Owner:** [AI Governance Lead]

## 1. Classificazione preliminare

### 1.1 Qualificazione come "incidente grave" ex AI Act Art. 3 n. 49

L'incidente ha causato (barrare ciò che si applica):

- ☐ Morte di una persona
- ☐ Grave danno alla salute
- ☐ Interruzione grave della gestione o del funzionamento di infrastrutture critiche
- ☐ Violazione degli obblighi in materia di diritti fondamentali
- ☐ Danno grave a cose o all'ambiente

### 1.2 Termini di notifica applicabili

| Tipologia | Termine Art. 73 | Data scadenza |
|-----------|-----------------|----------------|
| Incidente grave standard | 15 giorni dalla conoscenza | |
| Violazione diritti fondamentali | 2 giorni | |
| Morte di una persona | 10 giorni | |

### 1.3 Notifiche parallele

| Norma | Applicabile? | Termine | Autorità | Stato |
|-------|--------------|---------|----------|-------|
| GDPR Art. 33 (data breach) | Sì/No | 72h | Garante Privacy | |
| NIS2 D.Lgs. 138/2024 Art. 23 | Sì/No | 24h early warning + 72h notifica + 1 mese finale | ACN / CSIRT | |
| Legge 90/2024 (PA) | Sì/No | Senza indugio | CSIRT PA | |
| Altre (settoriali) | | | | |

## 2. Identificazione del sistema IA

| Elemento | Dato |
|----------|------|
| Denominazione | |
| Versione / release | |
| Fornitore | |
| Deployer | |
| Classificazione rischio AI Act | |
| Numero di registrazione EUDB | |
| Finalità d'uso dichiarata | |
| Rinvio AIIA / FRIA | |

## 3. Descrizione dell'incidente

### 3.1 Fatti

[Descrizione oggettiva in ordine cronologico: cosa è accaduto, quando, dove, chi è coinvolto, quali conseguenze osservate.]

### 3.2 Timeline

| Data / ora | Evento | Fonte |
|-----------|--------|-------|
| [T0] | | |
| [T0+X] | Rilevamento | |
| [T0+Y] | Contenimento | |
| [T0+Z] | Prima notifica interna | |
| [T0+K] | Notifica autorità | |

### 3.3 Soggetti impattati

| Categoria | Numero stimato | Natura impatto |
|-----------|----------------|----------------|
| Utenti finali | | |
| Lavoratori | | |
| Pazienti / cittadini | | |
| Minori | | |
| Altri gruppi vulnerabili | | |

## 4. Causa

### 4.1 Ipotesi di causa

[Prima ipotesi formulata sulla base delle evidenze raccolte.]

### 4.2 Analisi causa profonda (RCA) — preliminare

- Cause tecniche: [...]
- Cause organizzative: [...]
- Cause di processo: [...]
- Fattori contributivi esterni: [...]

(Analisi approfondita segue nel rapporto finale.)

## 5. Contenimento e mitigazione

### 5.1 Misure immediate

- [Sospensione del sistema / patch / rollback / comunicazione agli utenti / altro].

### 5.2 Misure in corso

- [...]

### 5.3 Misure pianificate

- [...]

## 6. Impatto

### 6.1 Impatto su persone

[Descrizione: danni fisici, psichici, economici, ai diritti.]

### 6.2 Impatto su organizzazione

- Reputazione: [...]
- Operativo: [...]
- Economico: [...]
- Legale / regolatorio: [...]

### 6.3 Impatto su infrastrutture e terzi

[...]

## 7. Comunicazione

### 7.1 Comunicazione interna

| Destinatario | Data | Mezzo |
|--------------|------|-------|
| AI Governance Lead | | |
| Direzione | | |
| CSIRT / Security | | |
| DPO | | |
| Legal | | |

### 7.2 Comunicazione ad autorità

| Autorità | Data | Protocollo / ricevuta |
|----------|------|------------------------|
| AgID / ACN | | |
| Garante Privacy (se data breach) | | |
| ACN / CSIRT (se NIS2) | | |
| Autorità settoriale | | |

### 7.3 Comunicazione a soggetti impattati

Quando, come, contenuti.

## 8. Responsabilità e governance

- Team di risposta all'incidente: [nomi, ruoli].
- Coordinamento con fornitore (se deployer).
- Coordinamento con deployer (se fornitore).
- Coinvolgimento terze parti (periti, consulenti).

## 9. Azioni correttive

(Coerenti con `/nc`.)

| ID | Azione | Owner | Scadenza | Efficacia attesa | KPI di verifica |
|----|--------|-------|----------|------------------|-----------------|
| | | | | | |

## 10. Aggiornamenti

| Versione | Data | Modifiche | Autore |
|----------|------|-----------|--------|
| 0.1 | | Prima emissione | |
| 0.2 | | Aggiornamento con esiti RCA | |
| 1.0 | | Rapporto finale | |

## 11. Allegati

- Log di sistema.
- Screenshot / evidenze.
- Comunicazioni ad autorità e ricevute.
- Rapporti tecnici.
- Verbali interventi.

---

**Firma**

___________________________
[AI Governance Lead / Direzione]
