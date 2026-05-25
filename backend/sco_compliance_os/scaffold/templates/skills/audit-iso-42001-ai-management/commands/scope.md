---
description: "Scoping ISO 42001 + scoping regolatorio AI Act"
---

# /scope — Scoping ISO 42001 + scoping regolatorio AI Act

## Uso
`/scope [descrizione sistema o organizzazione]`

## Quando
Primo step obbligatorio di qualsiasi progetto AIMS. Determina contemporaneamente il perimetro del sistema di gestione (ISO 42001 cl. 4) e il perimetro regolatorio (AI Act Art. 2-3-5-6, Legge 132 Capo I).

## Output atteso

Scheda di scoping strutturata in sei blocchi:

1. **Perimetro AIMS (ISO 42001 cl. 4.1-4.4)**
   - Contesto interno/esterno.
   - Parti interessate e loro esigenze/aspettative.
   - Campo di applicazione AIMS (sistemi IA inclusi/esclusi, siti, funzioni).
   - Interfacce e dipendenze.

2. **Scoping regolatorio AI Act**
   - Rientra nella definizione di "sistema di IA" ex Art. 3 n. 1? [SÌ/NO + motivazione].
   - Pratiche vietate ex Art. 5? [SÌ/NO per ciascuna lettera].
   - Sistema ad alto rischio ex Art. 6 + Allegato III? [SÌ/NO + area Allegato III].
   - Obblighi di trasparenza Art. 50 attivati?
   - Modello GPAI (Art. 51) o GPAI a rischio sistemico (Art. 52)?
   - Esclusioni applicabili (Art. 2 paragrafi 3-6: sicurezza nazionale, difesa, ricerca)?

3. **Ruolo regolatorio ex AI Act Art. 3**
   - Fornitore? Deployer? Importatore? Distributore? Rappresentante autorizzato? Produttore del prodotto?
   - Se più ruoli simultanei, elencali tutti.

4. **Settori italiani rafforzati (Legge 132 Capo II)**
   - Sanità (Art. 7-10) → attivato?
   - Lavoro (Art. 11-12) → attivato?
   - Professioni intellettuali (Art. 13) → attivato?
   - Pubblica Amministrazione (Art. 14) → attivato?
   - Attività giudiziaria (Art. 15) → attivato?
   - Minori (consenso parentale <14 anni) → attivato?

5. **Autorità italiane competenti**
   - Default: AgID + ACN (Art. 20 Legge 132).
   - Aggiuntive: AGENAS (sanità), Garante Privacy (dati personali), autorità settoriali.

6. **Obblighi conseguenti**
   - Elenco ad alto livello degli obblighi attivati (es. sistema di gestione rischi Art. 9, data governance Art. 10, documentazione tecnica Art. 11 + Allegato IV, ecc.).
   - Applicabilità Appendice A ISO 42001 (quali obiettivi di controllo attivi).

## Regole operative

- Se Fase 1 identifica una pratica vietata → stop immediato, nessuna gap analysis utile, solo raccomandazione di dismissione o riprogettazione del sistema.
- Se il sistema è GPAI con rischio sistemico → applicare Art. 55 AI Act in aggiunta.
- La determinazione "sistema di IA sì/no" deve essere motivata citando gli elementi tecnici (autonomia, adattività, inferenza, tipi di output).
- Se il soggetto è simultaneamente fornitore e deployer, esplicitare i due fasci di obblighi.

## Input minimo richiesto all'utente

- Descrizione tecnica del sistema (modello base, finalità d'uso, dominio applicativo, dati di addestramento, tipo di output, deployment context).
- Attività dell'organizzazione e settore.
- Se l'organizzazione mette il sistema sul mercato / lo utilizza / lo importa / lo distribuisce.

## Documenti collegati

- `../references/ai-act-2024.md` (Art. 2, 3, 5, 6, 50, 51, 55; Allegato III)
- `../references/legge-132-2025.md` (Art. 1-6 principi; Art. 7-15 settori; Art. 20 autorità)
- `../references/iso42001-2023.md` (cl. 4.1-4.4)
- `../references/decision-tree-autorita.md`
