---
description: "Analisi esposizione sanzionatoria"
---

# /sanzioni — Analisi esposizione sanzionatoria

## Uso
`/sanzioni [organizzazione|violazione]`

## Quando
Per quantificare l'esposizione sanzionatoria di un'organizzazione in relazione ad AI Act, Legge 132/2025, GDPR, NIS2, e per supportare la prioritizzazione del piano di adeguamento.

## Fonti normative sanzionatorie

### AI Act Art. 99

| Violazione | Sanzione massima |
|-----------|------------------|
| Pratiche vietate Art. 5 | 35.000.000 € o **7%** del fatturato mondiale annuo (il maggiore) |
| Violazione obblighi sistemi alto rischio (Art. 16 fornitore, Art. 26 deployer), GPAI, trasparenza Art. 50, organismi notificati, valutazione conformità | 15.000.000 € o **3%** del fatturato mondiale annuo |
| Informazioni false/incomplete ad autorità | 7.500.000 € o **1%** |

Per PMI e startup: il minore tra l'importo forfettario e la percentuale (regime più mite).

### AI Act Art. 101 — Sanzioni GPAI

Per fornitori di GPAI: fino a 15.000.000 € o 3% del fatturato mondiale annuo per violazione di obblighi Art. 53-55.

### Legge 132/2025

Non introduce un regime sanzionatorio autonomo uniforme (rinvia ai regimi settoriali). Sanzioni applicabili:
- Settore lavoro: sanzioni D.Lgs. 152/1997 + Statuto Lavoratori.
- Settore sanitario: responsabilità Gelli-Bianco.
- PA: responsabilità amministrativa e disciplinare.
- Professioni: sanzioni deontologiche degli ordini.
- Penale: possibile rilevanza ex artt. 615-quater e seguenti c.p. e reati informatici.

### GDPR Art. 83

| Violazione | Sanzione massima |
|-----------|------------------|
| Violazioni di base (registri, DPO, data breach procedure) | 10.000.000 € o 2% fatturato mondiale |
| Violazioni gravi (principi, diritti interessati, trasferimenti) | 20.000.000 € o 4% fatturato mondiale |

### NIS2 (D.Lgs. 138/2024)

| Soggetto | Sanzione massima |
|----------|------------------|
| Soggetto essenziale | 10.000.000 € o 2% fatturato mondiale |
| Soggetto importante | 7.000.000 € o 1,4% fatturato mondiale |

### Legge 90/2024 (PA)

Sanzioni da 25.000 a 125.000 € per referenti PA + responsabilità dirigenziale.

## Principi di applicazione

- **Cumulabilità**: le sanzioni di diversi regimi possono sommarsi se le condotte violano framework distinti (es. sistema IA che viola sia AI Act sia GDPR → due sanzioni).
- **Ne bis in idem**: un'autorità non può sanzionare due volte lo stesso fatto nello stesso regime. Se due autorità sanzionano lo stesso fatto ai sensi di norme distinte (AI Act + GDPR), va verificato caso per caso.
- **Principio di proporzionalità**: l'autorità considera natura, gravità, durata, dolo/colpa, misure adottate per mitigare, precedenti, cooperazione, grado di danno.
- **Soglie progressive**: la sanzione massima è il tetto; l'autorità applica la sanzione concreta graduatamente.

## Output

Scheda:

1. **Organizzazione**: denominazione, fatturato mondiale annuo (per calcolo percentuale).
2. **Violazioni ipotizzate o rilevate**:
   - Tipologia (pratica vietata / alto rischio / GPAI / trasparenza / altro).
   - Fonte normativa (articolo puntuale).
3. **Esposizione teorica massima**:
   - Calcolo importo assoluto vs percentuale (il maggiore).
   - Cumuli potenziali con GDPR/NIS2.
4. **Fattori attenuanti presenti**:
   - AIMS implementato (ISO 42001).
   - SoA completa.
   - AIIA/FRIA eseguite.
   - Cooperazione con autorità.
   - Misure adottate spontaneamente.
5. **Fattori aggravanti**:
   - Recidiva.
   - Dolo.
   - Dimensione del danno.
   - Mancata notifica incidente.
6. **Stima ragionevole**: non valore certo ma range plausibile.
7. **Raccomandazioni**: priorità di remediation.

## Regole operative

- **Mai presentare la sanzione come certa**: è sempre un'ipotesi, l'entità effettiva dipende dall'autorità.
- Comunicare l'esposizione massima è utile per allocare risorse e far comprendere al top management il rischio regolatorio.
- Usare `/sanzioni` come input per l'executive summary di `/gap` e `/roadmap`.
- Includere sempre la stringa: "Stima indicativa a fini di pianificazione. L'entità concreta è determinata dall'autorità competente in base ai criteri di proporzionalità."
- Per le startup, ricordare il regime mitigato Art. 99 c. 6 AI Act (sanzione minima tra valore assoluto e percentuale).

## Documenti collegati

- `../references/ai-act-2024.md` (Art. 99, 101)
- `../references/legge-132-2025.md`
