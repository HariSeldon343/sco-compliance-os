# Reference — Decision tree autorità competenti

Schema operativo per individuare, in qualsiasi fattispecie, le autorità italiane ed europee competenti e i canali di notifica.

## Diagramma decisionale

```
START
  │
  ▼
 [Q1] Il sistema rientra nelle pratiche vietate Art. 5 AI Act?
  ├── SÌ → STOP operativo: divieto di immissione/uso.
  │         Notifica se già immesso: AgID + ACN. Sanzione potenziale: 35M€ o 7%.
  │
  └── NO → procedi a Q2
  
  ▼
 [Q2] Il sistema è GPAI (Art. 51) o GPAI con rischio sistemico (Art. 52)?
  ├── SÌ → Autorità primaria: AI Office (Commissione UE).
  │         Autorità nazionale di coordinamento: AgID.
  │         Notifica fornitore: AI Office tramite sistema dedicato.
  │         Se sistemico: obblighi Art. 55 (valutazione modello, incidenti, cybersecurity).
  │
  └── NO → procedi a Q3
  
  ▼
 [Q3] Il sistema è ad alto rischio ex Art. 6 + Allegato III?
  ├── SÌ → Registrazione EUDB (banca dati UE).
  │         Autorità di sorveglianza nazionale:
  │           • Default: AgID + ACN (Art. 20 Legge 132).
  │           • Settoriali aggiuntive in base al contesto (cfr. Q5-Q7).
  │         Obblighi: Art. 8-15 (requisiti), Art. 16-22 (fornitore), Art. 26-27 (deployer).
  │
  └── NO → procedi a Q4
  
  ▼
 [Q4] Sistema soggetto a obblighi trasparenza Art. 50?
  ├── SÌ → Autorità principale: AGCOM (per deepfake, contenuti sintetici, media).
  │         AgID + Garante Privacy se trattamento dati + chatbot.
  │
  └── NO → applicabilità diretta solo di norme generali (GDPR, consumo, ecc.)
  
  ▼
 [Q5] Il sistema tratta dati personali?
  ├── SÌ → Garante Privacy (autorità primaria per trattamento).
  │         Overlap con AI Act se trattamento ha finalità ad alto rischio.
  │         DPIA ex Art. 35 GDPR obbligatoria quando applicabile.
  │         Eventuale FRIA ex Art. 27 AI Act integrata.
  │
  └── NO → procedi a Q6
  
  ▼
 [Q6] Il sistema rientra in settore Legge 132 Capo II?
  ├── SANITÀ (Art. 7-10) → AGENAS + Regioni + Garante Privacy; registro IA sanità (Art. 8).
  │
  ├── LAVORO (Art. 11-12) → INL + INPS + Garante Privacy; informativa D.Lgs. 152/1997.
  │
  ├── PROFESSIONI (Art. 13) → Ordini professionali (CNF, CNDCEC, FNOMCeO, CNI, ecc.).
  │
  ├── PA (Art. 14) → AgID + PCM (Comitato); accreditamento sistemi; motivazione ex L. 241/1990.
  │
  ├── GIUSTIZIA (Art. 15) → Ministero Giustizia; CEPEJ come riferimento; limiti tassativi.
  │
  └── NO → procedi a Q7
  
  ▼
 [Q7] L'organizzazione è soggetto essenziale/importante NIS2 (D.Lgs. 138/2024)?
  ├── SÌ → Obblighi NIS2 parallali: ACN + CSIRT Italia.
  │         Notifiche incidenti significativi: early warning 24h, notifica 72h, finale 1 mese.
  │
  └── NO → procedi a Q8
  
  ▼
 [Q8] L'organizzazione è PA o fornitore PA?
  ├── SÌ → Obblighi Legge 90/2024: referente cybersicurezza; notifica CSIRT PA.
  │
  └── NO → nessun obbligo aggiuntivo
  
END
```

## Tabella sinottica autorità

| Autorità | Tipo | Ambito principale | Canale |
|----------|------|-------------------|--------|
| **AI Office** (Commissione UE) | UE | GPAI, rischio sistemico | Sistema dedicato |
| **European AI Board** | UE | Coordinamento | — |
| **AgID** | Italia | Sorveglianza generale AI Act, PA, standard | Portale AgID |
| **ACN** | Italia | Cybersecurity AI, alto rischio critico | Portale ACN / CSIRT |
| **Garante Privacy** | Italia | GDPR, trattamenti dati personali | Portale Garante |
| **AGCOM** | Italia | Deepfake, contenuti, media, trasparenza Art. 50 | Portale AGCOM |
| **AGENAS** | Italia | IA in sanità | Portale AGENAS |
| **INL / INPS** | Italia | IA nel lavoro | Portale rispettivi |
| **Banca d'Italia / IVASS / CONSOB** | Italia | IA bancario / assicurativo / finanziario | — |
| **Ordini professionali** | Italia | IA nelle professioni intellettuali | Portali ordini |
| **Ministero Giustizia** | Italia | IA giudiziaria | — |
| **Comitato PCM IA** | Italia | Coordinamento strategico | Presidenza CdM |

## Timing delle notifiche (casistica ricorrente)

| Evento | Norma | Termine | Destinatario |
|--------|-------|---------|--------------|
| Incidente grave IA Art. 3 n. 49 (danno a infrastrutture/diritti) | Art. 73 AI Act | 15 giorni | Autorità sorveglianza nazionale |
| Incidente grave con violazione diritti fondamentali | Art. 73 c. 3 | 2 giorni | Idem |
| Incidente grave con morte | Art. 73 c. 4 | 10 giorni | Idem |
| Data breach | GDPR Art. 33 | 72 ore | Garante Privacy |
| Incidente significativo NIS2 | D.Lgs. 138/2024 Art. 23 | 24 h early warning + 72 h notifica + 1 mese finale | ACN / CSIRT |
| Incidente PA Legge 90/2024 | Art. 1 c. 5 L. 90/2024 | Senza indugio | CSIRT / ACN |
| Non conformità sistema alto rischio rilevata da fornitore | AI Act Art. 20 | Senza ritardo | Autorità sorveglianza |

## Principi di coordinamento

- Un singolo incidente può attivare **più notifiche parallele** con termini diversi. Serve orchestrazione interna.
- Le autorità italiane cooperano tra loro e con la Commissione UE (Art. 70 AI Act + accordi italiani).
- In caso di dubbio su quale autorità, il fornitore/deployer può rivolgere richiesta di chiarimento ad AgID come punto di contatto primario.
- Per PMI e startup, AgID fornisce supporto facilitato (Art. 22 Legge 132).
