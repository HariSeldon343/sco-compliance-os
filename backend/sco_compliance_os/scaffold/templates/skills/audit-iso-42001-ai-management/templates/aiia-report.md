# Template — AI System Impact Assessment (AIIA)

> Template editabile conforme a ISO/IEC 42001 cl. 6.1.4 e controlli A.5.2-A.5.5.

---

# AIIA — [Denominazione sistema IA]

**Codice documento:** AIMS-AIIA-[progressivo]
**Versione:** [x.y]
**Data di emissione:** [gg/mm/aaaa]
**Data di revisione prevista:** [gg/mm/aaaa]
**Owner valutazione:** [Ruolo]
**Approvazione:** [AI Governance Lead] — firma e data

## 1. Identificazione del sistema

| Elemento | Dato |
|----------|------|
| Denominazione | [...] |
| Versione | [...] |
| Fornitore | [...] |
| Deployer | [...] |
| Finalità d'uso dichiarata | [...] |
| Contesto operativo | [...] |
| Utenti finali | [...] |
| Soggetti impattati | [...] |
| Classificazione rischio AI Act | [Inaccettabile / Alto / Limitato / Minimo] |
| Ruolo regolatorio | [Fornitore / Deployer / altro] |
| Settori Legge 132 attivati | [...] |
| Dati di addestramento (fonte, volume, qualità) | [...] |
| Modello base / pipeline | [...] |
| Integrazioni e API | [...] |

## 2. Analisi d'impatto

### 2.1 Impatti su individui

| Scenario | Probabilità (1-5) | Gravità (1-5) | Reversibilità | Scala |
|----------|-------------------|---------------|---------------|-------|
| Discriminazione indiretta | | | | individuale |
| Violazione privacy | | | | |
| Perdita di autonomia decisionale | | | | |
| Danno fisico / economico | | | | |
| Accesso ridotto a servizi | | | | |

### 2.2 Impatti su gruppi e società

| Scenario | Probabilità | Gravità | Reversibilità | Scala |
|----------|-------------|---------|---------------|-------|
| Discriminazione sistemica | | | | collettiva |
| Concentrazione informativa | | | | |
| Erosione fiducia | | | | |
| Impatto ambientale | | | | |

### 2.3 Impatti su organizzazione

| Scenario | Probabilità | Gravità | Reversibilità |
|----------|-------------|---------|---------------|
| Reputazione | | | |
| Non conformità / sanzioni | | | |
| Continuità operativa | | | |
| Responsabilità legale | | | |

## 3. Valutazione del rischio

### 3.1 Matrice probabilità × gravità

| | Gravità 1 | 2 | 3 | 4 | 5 |
|-|-----------|---|---|---|---|
| **Prob 5** | Medio | Alto | Critico | Critico | Critico |
| **4** | Medio | Medio | Alto | Critico | Critico |
| **3** | Basso | Medio | Medio | Alto | Critico |
| **2** | Basso | Basso | Medio | Medio | Alto |
| **1** | Basso | Basso | Basso | Medio | Medio |

### 3.2 Risultati

| ID | Impatto | Probabilità | Gravità | Livello | Soglia accettabilità | Esito |
|----|---------|-------------|---------|---------|----------------------|-------|
| R-01 | [...] | | | | | [Accettabile / Non accettabile — da trattare] |

## 4. Trattamento

| ID Rischio | Misura di mitigazione | Tipo (T/O/C) | Controllo A.x.y ISO 42001 | Articolo AI Act | Rischio residuo | Accettazione owner | Data |
|-----------|------------------------|-------------|---------------------------|-----------------|-----------------|-------------------|------|
| R-01 | [...] | Tecnica/Organizzativa/Contrattuale | | | | | |

Legenda tipo: T=Tecnica, O=Organizzativa, C=Contrattuale.

## 5. Documentazione e governance

### 5.1 Persone coinvolte

| Nome / Ruolo | Competenza | Conflitto di interesse dichiarato |
|--------------|------------|-----------------------------------|
| | | |

### 5.2 Fonti consultate

- Documentazione tecnica del sistema.
- Test e validazioni eseguite.
- Input da parti interessate (utenti, gruppi impattati).
- [altro].

### 5.3 Relazione con altre valutazioni

| Valutazione | Rinvio |
|-------------|--------|
| DPIA (GDPR Art. 35) | [rinvio] |
| FRIA (AI Act Art. 27) | [rinvio — se applicabile] |
| Risk assessment aziendale | [rinvio] |

### 5.4 Revisione

Trigger di aggiornamento:

- modifica sostanziale del sistema;
- nuova classificazione di rischio AI Act;
- incidente grave;
- cambio di contesto operativo;
- nuova evidenza di bias o danno;
- revisione periodica annuale.

**Prossima revisione prevista**: [gg/mm/aaaa].

## 6. Conclusioni

Sintesi della valutazione in 10-20 righe: livello di rischio complessivo, accettabilità, principali misure adottate, residui, raccomandazioni operative.

---

**Firma e data**

___________________________
[AI Governance Lead / Owner]
