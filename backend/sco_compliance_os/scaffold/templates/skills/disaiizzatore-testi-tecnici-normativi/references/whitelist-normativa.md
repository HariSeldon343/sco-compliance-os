# Whitelist normativa — cosa NON toccare mai

Lista di elementi testuali che la skill `disaiizzatore-testi-tecnici-normativi` **non deve mai modificare, parafrasare, riformulare o "umanizzare"**, anche quando appaiono dentro paragrafi che vengono altrimenti riscritti. Questi elementi sono inviolabili perché alterarli può:

- introdurre inesattezze normative
- compromettere il valore probatorio del documento (perizie CTU)
- attenuare un rilievo di audit
- alterare la gravità di una non conformità
- creare incoerenza con sistemi di certificazione

---

## 1. Riferimenti normativi puntuali

**Mai parafrasare o riformulare**:

- Articoli, commi, lettere di legge: `Art. 21, comma 2, lett. b) del D.Lgs. 138/2024`
- Allegati di legge: `Allegato I, punto 3.2 del D.Lgs. 138/2024`
- Decreti ministeriali, leggi: `D.Lgs. 81/2008`, `Legge 90/2024`, `Legge 24/2017 (Gelli-Bianco)`, `D.P.R. 14/1/1997`
- Regolamenti UE: `Reg. (UE) 2024/2690`, `GDPR (Reg. UE 2016/679)`, `AI Act (Reg. UE 2024/1689)`, `CRA (Reg. UE 2024/2847)`
- Direttive UE: `Dir. (UE) 2022/2555`, `Dir. (UE) 2022/2557`
- Standard ISO/IEC: `ISO/IEC 27001:2022`, `ISO 9001:2015`, `ISO/IEC 42001:2023`, `ISO/IEC 20000-1:2018`, `ISO 31000:2018`, `ISO 22301:2019`, `ISO 14067:2018`, `UNI EN 15224:2017`
- Numerazione di clausole: `clausola 6.1.2`, `clausola 9.3`, `Annex A controllo 5.15`, `A.5.17`, `A.8.16`
- Determinazioni e linee guida: `Determinazione ACN n. 379907/2025`, `Linee Guida AgID`, `UNI/PdR 174:2024`
- Framework e identificatori: `NIST CSF 2.0 — Funzione PR.AC-01`, `MITRE ATT&CK T1078`

**Esempio di errore da evitare**:
- Originale: *"L'Art. 21 del D.Lgs. 138/2024 stabilisce le misure di gestione del rischio."*
- ❌ Parafrasi sbagliata: *"Il decreto NIS2 italiano disciplina le misure di gestione del rischio nel suo articolo 21."*
- ✅ Lasciare invariata la formula puntuale.

---

## 2. Definizioni standard ISO e normative

Le definizioni tratte dagli standard hanno valore tecnico-formale e non vanno parafrasate:

- "*Il rischio è l'effetto dell'incertezza sugli obiettivi*" (ISO 31000:2018)
- "*Sistema di gestione: insieme di elementi correlati o interagenti…*" (Annex SL)
- "*Non conformità: mancato soddisfacimento di un requisito*" (ISO 9000:2015)
- "*Audit: processo sistematico, indipendente e documentato…*" (ISO 19011:2018)
- "*Incidente di sicurezza: evento che compromette effettivamente o potenzialmente…*"
- "*Soggetto essenziale / Soggetto importante*" (NIS2)
- Definizioni di SLA, OLA, RTO, RPO, MTPD, MAO da ISO 22301 / ITIL

Quando una definizione standard appare nel testo, mantenerla **alla lettera**. Se viene introdotta da una formula come "ai sensi di ISO 31000:2018, il rischio è...", quella formula è anch'essa whitelist.

---

## 3. Formule tipizzate dei documenti di audit

Il linguaggio degli audit di terza parte ha formule consolidate che hanno valore tecnico riconosciuto e che gli auditor leggono come "marcatori di registro". Sono whitelist:

- *"Non risulta evidenza di…"*
- *"Si rileva che…"*
- *"L'evidenza documentale conferma…"*
- *"Non è stato possibile verificare…"*
- *"L'organizzazione ha dimostrato di…"*
- *"Si raccomanda di…"*
- *"NC_I (Non Conformità Maggiore)"*, *"NC_II (Non Conformità Minore)"*, *"SM (Suggerimento di Miglioramento)"*, *"Osservazione"*
- *"In sede di audit"*, *"Durante la verifica ispettiva"*
- *"Ai fini del proseguimento dell'iter certificativo"*

Queste formule **non sono** tell AI: sono formule di registro auditoriale italiano. Lasciarle invariate.

---

## 4. Formule processuali e peritali (CTU)

Per le perizie CTU, le formule processuali sono inviolabili:

- *"Ai sensi e per gli effetti di…"*
- *"Ai sensi dell'art. 220 c.p.p."*, *"ex art. 61 c.p.c."*
- *"Il sottoscritto perito incaricato"*
- *"In risposta al quesito posto dall'Ill.mo Magistrato"*
- *"Operazioni peritali svolte in contraddittorio con…"*
- *"Si dà atto che…"*
- *"Tutto ciò premesso e considerato"*
- *"Il presente elaborato peritale viene depositato in formato digitale firmato"*
- *"Letto, confermato e sottoscritto"*
- Identificazione del procedimento: numero RG, nome del Magistrato, parti processuali, luoghi e date

Anche se queste formule "sembrano" stilisticamente datate, sono **vincolate dalla forma processuale**. Mai modificarle.

---

## 5. Dati numerici, identificatori, riferimenti tabellari

**Mai modificare**:
- Numeri (cifre, percentuali, importi)
- Date in qualsiasi formato
- ID di gap, ticket, controlli, rilievi, procedure, registri
- RTO, RPO, MTPD, MAO espressi in ore/giorni
- Coordinate, indirizzi IP, hash, fingerprint
- Versioni software, build, codici prodotto
- Numerazione di tabelle, figure, allegati
- Riferimenti incrociati interni al documento ("vedi §4.2", "cfr. tabella 7")

---

## 6. Citazioni dirette da fonti

Qualunque cosa appaia tra virgolette come citazione diretta da una fonte (legge, sentenza, report, articolo) è whitelist. Se la citazione è veramente tale, va lasciata identica. Se invece le virgolette sono usate impropriamente per enfatizzare ("approccio 'olistico' alla sicurezza"), allora le virgolette stesse sono un tell AI e vanno rimosse insieme alla parola enfatizzata.

---

## 7. Termini tecnici consolidati

I termini tecnici inglesi entrati nell'uso italiano consolidato non vanno italianizzati né spiegati ridondantemente:

`backup`, `patching`, `hardening`, `vulnerability assessment`, `penetration test`, `incident response`, `business impact analysis (BIA)`, `disaster recovery (DR)`, `single point of failure (SPOF)`, `man-in-the-middle`, `phishing`, `ransomware`, `endpoint detection and response (EDR)`, `security operations center (SOC)`, `change management`, `configuration management database (CMDB)`, `service level agreement (SLA)`, `statement of applicability (SoA)`, `chief information security officer (CISO)`, `data protection officer (DPO)`.

L'introduzione di queste sigle (es. *"Single Point of Failure (SPOF)"*) è ammessa la prima volta nel documento. Successivamente si usa la sigla.

---

## 8. Strutture documentali standard

Quando un documento segue una struttura prevista da una norma o da un template di certificazione, **la struttura stessa è whitelist**:

- **Procedure ISO**: Scopo, Campo di applicazione, Riferimenti normativi, Definizioni, Responsabilità, Modalità operative, Registrazioni, Riesame
- **Statement of Applicability (SoA)**: ID controllo, descrizione, applicabilità, motivazione esclusione, stato implementazione
- **Registro rischi**: ID, asset, minaccia, vulnerabilità, probabilità, impatto, livello rischio, trattamento, owner
- **Verbale di riesame della Direzione**: input → analisi → decisioni → azioni
- **DDV (CSQA)**: dati audit, perimetro, conformità, rilievi, conclusioni
- **Perizia CTU**: premessa, quesito, metodologia, operazioni peritali, risposta al quesito, conclusioni

L'ordine delle sezioni e le intestazioni non si modificano.

---

## 9. Acronimi normativi e di settore

Mai sciogliere o riformulare acronimi consolidati: `SGSI`, `SGQ`, `SGA`, `SGSL`, `SMS`, `SGAI`, `BCMS`, `ISMS`, `QMS`, `EMS`, `OHSMS`, `PDCA`, `RACI`, `CIA` (Confidentiality/Integrity/Availability), `MFA`, `2FA`, `IAM`, `PAM`, `SIEM`, `SOAR`, `NIST CSF`, `DORA`, `CRA`, `NIS2`, `GDPR`, `DPIA`, `LIA`, `TIA`.

---

## 10. Quando in dubbio: lascia stare

Il principio di prudenza: **se non sei sicuro che un elemento sia tell AI o whitelist, lascia stare**. Una skill di deaiizzazione che modifica troppo è peggio di una che modifica poco. L'integrità tecnica del documento prevale sempre sull'estetica stilistica.
