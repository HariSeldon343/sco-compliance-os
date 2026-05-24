# Metodologie di Risk Assessment — Dettaglio Operativo

## 1. Matrice Probabilità × Impatto

### Scale di valutazione (default 4×4, adattabile)

**Probabilità**:

| Livello | Qualitativa | Quantitativa |
|---|---|---|
| 1 — Rara | <10% | <1 volta in arco di piano |
| 2 — Possibile | 10-40% | 1-2 volte in arco di piano |
| 3 — Probabile | 40-70% | 3-5 volte in arco di piano |
| 4 — Quasi certa | >70% | >5 volte in arco di piano |

**Impatto** (multidimensionale):

| Livello | Industriale/Business | Economico-Finanziario | Reputazionale | H&S | ESG |
|---|---|---|---|---|---|
| 1 — Basso | Impatto limitato su processi | <[soglia 1] | Notizia locale isolata | Infortuni lievi | Impatto trascurabile |
| 2 — Medio | Rallentamento processi | [soglia 1]-[soglia 2] | Copertura media locale | Infortuni con assenza | Impatto contenuto |
| 3 — Elevato | Interruzione parziale | [soglia 2]-[soglia 3] | Copertura nazionale | Infortuni gravi | Impatto significativo |
| 4 — Critico | Interruzione prolungata | >[soglia 3] | Copertura internazionale, crisi | Decessi | Impatto grave e duraturo |

Le soglie economiche vanno calibrate sulla dimensione dell'organizzazione.

### Matrice di priorità

| | Impatto 1 | Impatto 2 | Impatto 3 | Impatto 4 |
|---|---|---|---|---|
| **Prob 4** | Media | Elevata | Critica | Critica |
| **Prob 3** | Media | Elevata | Elevata | Critica |
| **Prob 2** | Bassa | Media | Elevata | Elevata |
| **Prob 1** | Bassa | Bassa | Media | Elevata |

---

## 2. Value at Risk (VaR) — Simulazione Storica

Modello per rischio di mercato. Utilizzato nel settore finanziario (es. Fondaco SGR).

**Approccio**: Historical Simulation on Risk Factors with Full Re-pricing
- Risk factors: equity prices, interest rate curves, credit spreads, FX rates, implied volatilities, fund prices
- Campione: 1-2 anni di dati giornalieri → 260-520 scenari
- Relazione asset-factor: one-to-one (equity, ETF, fondi) oppure pricing function (bond, derivati, strutturati)

**Intervallo di confidenza**: tipicamente 95% o 99%, 1 giorno
**Backtesting**: confronto VaR stimato vs. rendimento realizzato; max 4 breaches/anno al 99% CI

**Limiti del VaR**: non cattura rischi di coda estrema, assume distribuzione stabile, non efficace per Private Markets e Hedge Funds.

---

## 3. Stress Test

4 tipologie:
- **Historical**: replica scenari di crisi passata (es. Lehman 2008, COVID 2020). Correlazioni implicite.
- **Predictive** (single factor): shock a un singolo fattore (es. MSCI -10%)
- **Multi-Factor**: combinazione di shock su più fattori contemporaneamente
- **Default Rate**: variazione probabilità default emittenti

Per ogni stress test: analisi driver di P&L a livello di singolo titolo e aggregazioni successive.

---

## 4. Sensitivity Analysis

| Tipo | Misura | Calcolo |
|---|---|---|
| DV01 (Interest Rate) | Variazione PV per +1bp tassi interesse | Per bucket maturity × valuta |
| Credit PV01 | Variazione PV per +1bp spread | Per bucket rating × settore |
| Inflation PV01 | Variazione PV per +1bp inflation swap | Per bucket maturity × nazione |
| FX Sensitivity | Variazione PV per +1bp tassi cambio | Per valuta |

---

## 5. Liquidity Risk

### Per portafogli diretti
Differenza tra valore asset e prezzo realizzabile in vendita. Componenti:
- **Bid/Ask**: spread per strumenti quotati, Fair Value B/A per altri
- **Pricer**: premio illiquidità per natura strumento (plain vanilla > strutturato)
- **Market Cap**: premio per capitalizzazione (small cap > large cap)
- **Ownership**: premio per % possesso su capitalizzazione
- **Nominal**: premio per nozionale emissione obbligazionaria

3 scenari: Normale (ultimi 6 mesi), Stress (H1 2008), Elevato stress (set 2008 - mar 2009)

### Per fondi di fondi (liquidabilità)
Stima basata su termini contrattuali di rimborso sottostanti (notice period, redemption frequency, gate, lock-up). Stress test con haircut basati su complessità/illiquidità × correlazione con equity.

### Time-to-liquidate
Tempistica per disinvestire interamente il portafoglio, in condizioni Normal/Stressed/Highly Stressed.

---

## 6. Simulazione Monte Carlo (Rischi Operativi)

Approccio per quantificazione rischi operativi (es. modello Fondaco SGR):

1. **Mappatura**: identificazione coppie Area/Attività (es. Trading/Analisi controparti)
2. **Questionario autovalutazione**: responsabili funzione stimano per ogni rischio:
   - Probabilità accadimento (giornaliera)
   - Perdita minima, media, massima (€, giornaliera)
   - Perdita migliore/peggiore 2,5% e 25%/20%
3. **Data management**: verifica anomalie risposte
4. **Simulazione Monte Carlo**: ogni evento indipendente, generazione distribuzione perdita attesa
5. **Analisi risultati**: perdita attesa, VaR operativo al 97,5%, per area e aggregato
6. **Report**: evidenza principali rischi, proposta soluzioni a RIC/CdA

---

## 7. FMEA/FMECA (Failure Mode and Effects Analysis)

Analisi proattiva per processi critici:
1. Scomporre processo in fasi/attività
2. Per ogni fase: identificare modi di guasto potenziali
3. Per ogni modo di guasto: effetti, cause, controlli esistenti
4. Valutare: Gravità (S) × Probabilità occorrenza (O) × Rilevabilità (D)
5. Calcolare RPN (Risk Priority Number) = S × O × D
6. Prioritizzare azioni su RPN più elevati
7. Ricalcolare RPN dopo implementazione azioni

---

## 8. Root Cause Analysis (RCA)

Per eventi avversi significativi:
- **5 Perché**: iterazione domande "perché?" fino alla causa radice
- **Diagramma di Ishikawa**: cause organizzate per categoria (Persone, Processi, Tecnologia, Ambiente, Management)
- **Fault Tree Analysis**: albero logico delle cause con porte AND/OR
- **Timeline analysis**: ricostruzione cronologica dell'evento

---

## 9. Business Impact Analysis (BIA)

| Parametro | Definizione |
|---|---|
| **MTPD** | Maximum Tolerable Period of Disruption — tempo massimo tollerabile di interruzione |
| **RTO** | Recovery Time Objective — tempo entro cui ripristinare il processo |
| **RPO** | Recovery Point Objective — quantità massima di dati perdibili (in tempo) |
| **MBCO** | Minimum Business Continuity Objective — livello minimo accettabile di servizio |

Processo BIA:
1. Identificare processi/servizi critici
2. Per ciascuno: determinare MTPD, RTO, RPO
3. Identificare risorse necessarie (persone, tecnologia, fornitori, sedi)
4. Valutare impatto di interruzione nel tempo (finanziario, reputazionale, legale, operativo)
5. Classificare processi per criticità
6. Input per strategie di continuità e piani BCP/DRP

---

## 10. Bowtie Analysis

Visualizzazione strutturata:
```
CAUSE → [Barriere preventive] → EVENTO → [Barriere reattive] → CONSEGUENZE
```
Utile per comunicare rischi complessi al management non tecnico.

---

## 11. Strumenti di raccolta (IEC 31010)

24 tecniche riconosciute dalla norma, tra cui: brainstorming, interviste strutturate, Delphi, audit con checklist, PHA, HAZOP, HACCP, What If, analisi scenari, BIA, RCA, FMEA, albero errori/eventi, causa-conseguenze, LOPA, albero decisioni, HRA, Bowtie, Markov.
