---
description: "Classificazione rischio AI Act"
---

# /rischio-regolatorio — Classificazione rischio AI Act

## Uso
`/rischio-regolatorio [sistema]`

## Quando
Task rapido per classificare un sistema IA nei 4 livelli di rischio previsti dall'AI Act. Output diretto, senza CoV completa.

## I 4 livelli di rischio

| Livello | Fonte AI Act | Conseguenza |
|---------|--------------|-------------|
| **Inaccettabile** | Art. 5 | Sistema vietato: immissione sul mercato, messa in servizio e uso proibiti. |
| **Alto rischio** | Art. 6 + Allegato I (sistemi di sicurezza di prodotti regolamentati) + Allegato III (8 aree) | Intero capo sui requisiti tecnici (Art. 8-15), obblighi fornitore (Art. 16-17), obblighi deployer (Art. 26-27), CE marking, registrazione EUDB, valutazione di conformità. |
| **Limitato** | Art. 50 | Obblighi di trasparenza: informare l'utente che sta interagendo con un sistema IA; etichettare contenuti sintetici/deepfake; informare soggetti esposti a emotion recognition o categorizzazione biometrica. |
| **Minimo** | — | Nessun obbligo specifico. Resta l'applicabilità di altre norme (GDPR, Codice del Consumo, Direttiva prodotti difettosi). |

## Tassonomia pratiche vietate (Art. 5)

- Manipolazione subliminale o tecniche ingannevoli che distorcono il comportamento causando danno.
- Sfruttamento di vulnerabilità (età, disabilità, situazione socioeconomica).
- Social scoring generalizzato da parte di autorità pubbliche o per loro conto.
- Valutazione o previsione del rischio di reato di una persona basata su profilazione (con eccezioni per attività investigative su reato commesso).
- Scraping non mirato di immagini facciali per costruire banche dati di riconoscimento.
- Riconoscimento delle emozioni in ambiente di lavoro e istruzione (eccezioni mediche/sicurezza).
- Categorizzazione biometrica per dedurre dati sensibili (razza, opinioni politiche, orientamento sessuale, ecc.).
- Identificazione biometrica remota in tempo reale in spazi accessibili al pubblico per law enforcement (con eccezioni tassative e autorizzazione).

## 8 aree dell'Allegato III (sistemi ad alto rischio)

1. Biometria (identificazione remota, categorizzazione biometrica, emotion recognition).
2. Infrastrutture critiche (gestione reti energia, acqua, traffico, gas, calore).
3. Istruzione e formazione professionale (ammissione, valutazione, assegnazione).
4. Occupazione e gestione dei lavoratori (reclutamento, selezione, valutazione, licenziamento).
5. Accesso a servizi essenziali pubblici e privati (credit scoring, assistenza, emergenze, assicurazione vita e salute).
6. Law enforcement (valutazione rischio reiterazione, valutazione prove, profilazione).
7. Migrazione, asilo, controllo frontiere.
8. Amministrazione della giustizia e processi democratici.

## Deroga Art. 6 c. 3

Anche se il sistema ricade in una delle 8 aree, può NON essere considerato ad alto rischio se svolge solo attività strumentali, non sostitutive del processo decisionale umano (es. task procedurale limitato, miglioramento risultato attività umana, rilevamento pattern senza sostituzione decisionale, task preparatorio). La deroga NON si applica se il sistema profila persone fisiche.

## Output

Scheda sintetica:

- **Livello di rischio**: [inaccettabile / alto / limitato / minimo].
- **Fondamento normativo**: [Art. 5 lett. X / Art. 6 + Allegato III area Y / Art. 50 lett. Z / nessuno].
- **Motivazione**: 3-5 righe che spiegano la classificazione con riferimento ai criteri normativi.
- **Deroga Art. 6 c. 3 applicabile?**: SÌ/NO con motivazione.
- **Obblighi conseguenti**: elenco puntato.
- **Scadenza applicativa**: [02/02/2025 divieti / 02/08/2025 GPAI / 02/08/2026 alto rischio / 02/08/2027 sistemi incorporati].
- **Sanzione massima in caso di violazione**: [35 M€ / 7% fatturato — 15 M€ / 3% — 7,5 M€ / 1%].
