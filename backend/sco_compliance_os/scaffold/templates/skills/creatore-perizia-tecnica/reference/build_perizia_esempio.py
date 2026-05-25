# -*- coding: utf-8 -*-
"""PERIZIA TECNICA MAD v3 - forma peritale (frontespizio, indice, quesito, elenchi puntati).
Doppio passaggio: legge /tmp/pagemap.json per i numeri di pagina dell'indice."""
import json
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = "/sessions/exciting-youthful-heisenberg/mnt/outputs/MAD_Perizia_tecnica_Netalia_Tecnosys_Rev00.docx"
FONT = "Arial"
try:
    PAGE_MAP = json.load(open("/tmp/pagemap.json"))
except Exception:
    PAGE_MAP = {}

doc = Document()
normal = doc.styles["Normal"]
normal.font.name = FONT; normal.font.size = Pt(11); normal.font.color.rgb = RGBColor(0,0,0)
rpr = normal.element.get_or_add_rPr()
rf = rpr.find(qn("w:rFonts"))
if rf is None: rf = OxmlElement("w:rFonts"); rpr.append(rf)
for a in ("w:ascii","w:hAnsi","w:cs"): rf.set(qn(a), FONT)
pf = normal.paragraph_format; pf.space_after = Pt(6); pf.line_spacing = 1.15

def style_heading(name, size, before, after):
    st = doc.styles[name]; st.font.name = FONT; st.font.bold = True; st.font.size = Pt(size); st.font.color.rgb = RGBColor(0,0,0)
    rp = st.element.get_or_add_rPr(); r = rp.find(qn("w:rFonts"))
    if r is None: r = OxmlElement("w:rFonts"); rp.append(r)
    for a in ("w:ascii","w:hAnsi","w:cs"): r.set(qn(a), FONT)
    st.paragraph_format.space_before = Pt(before); st.paragraph_format.space_after = Pt(after); st.paragraph_format.keep_with_next = True
style_heading("Heading 1", 13, 14, 6); style_heading("Heading 2", 11.5, 10, 4)

sec = doc.sections[0]
sec.page_height = Twips(16838); sec.page_width = Twips(11906)
sec.top_margin = Cm(2.0); sec.bottom_margin = Cm(2.2); sec.left_margin = Cm(2.2); sec.right_margin = Cm(2.2)

def set_run(r, bold=False, italic=False, size=11, color=(0,0,0)):
    r.font.name = FONT; r.font.bold = bold; r.font.italic = italic; r.font.size = Pt(size); r.font.color.rgb = RGBColor(*color)
    rp = r._element.get_or_add_rPr(); x = rp.find(qn("w:rFonts"))
    if x is None: x = OxmlElement("w:rFonts"); rp.append(x)
    for a in ("w:ascii","w:hAnsi","w:cs"): x.set(qn(a), FONT)

def para(text="", align=None, bold=False, italic=False, size=11, space_after=6, color=(0,0,0)):
    p = doc.add_paragraph()
    if align is not None: p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        r = p.add_run(text); set_run(r, bold, italic, size, color)
    return p

def h(text, level=1):
    p = doc.add_heading(level=level); r = p.add_run(text); set_run(r, bold=True, size={1:13,2:11.5}[level]); return p

def bullet(text):
    p = doc.add_paragraph(style="List Bullet"); p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text); set_run(r); return p

def set_cell_border(cell):
    tcPr = cell._tc.get_or_add_tcPr(); b = OxmlElement("w:tcBorders")
    for edge in ("top","left","bottom","right"):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"),"single"); e.set(qn("w:sz"),"4"); e.set(qn("w:space"),"0"); e.set(qn("w:color"),"000000"); b.append(e)
    tcPr.append(b)
def shade_cell(cell, hexfill):
    tcPr = cell._tc.get_or_add_tcPr(); s = OxmlElement("w:shd"); s.set(qn("w:val"),"clear"); s.set(qn("w:color"),"auto"); s.set(qn("w:fill"),hexfill); tcPr.append(s)
def set_cell_text(cell, text, bold=False, size=10, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text=""; p=cell.paragraphs[0]; p.alignment=align; p.paragraph_format.space_after=Pt(2); p.paragraph_format.space_before=Pt(2)
    r=p.add_run(text); set_run(r, bold=bold, size=size); cell.vertical_alignment=WD_ALIGN_VERTICAL.TOP
def add_table(headers, rows, widths_cm):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False; t.allow_autofit=False
    hc=t.rows[0].cells
    for i,ht in enumerate(headers):
        set_cell_text(hc[i], ht, bold=True, size=10); shade_cell(hc[i],"D9E2F3"); set_cell_border(hc[i])
    trPr=t.rows[0]._tr.get_or_add_trPr(); th=OxmlElement("w:tblHeader"); th.set(qn("w:val"),"true"); trPr.append(th)
    for row in rows:
        cc=t.add_row().cells
        for i,v in enumerate(row): set_cell_text(cc[i], v, size=10); set_cell_border(cc[i])
    for i,w in enumerate(widths_cm):
        for row in t.rows: row.cells[i].width=Cm(w)
    return t

def indice_line(label, key, level=1):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.4), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    pg = str(PAGE_MAP.get(key, ""))
    r1 = p.add_run(label); set_run(r1, size=10.5, bold=(level==1))
    r2 = p.add_run("\t"+pg); set_run(r2, size=10.5, bold=(level==1))
    return p

# ENTRIES: (heading completo, etichetta indice, chiave rilevamento pagina)
ENTRIES = [
 ("1. Premessa e incarico", "1. Premessa e incarico", "Premessa e incarico"),
 ("2. Documentazione esaminata", "2. Documentazione esaminata", "Documentazione esaminata"),
 ("3. Metodologia e classificazione delle evidenze", "3. Metodologia e classificazione delle evidenze", "Metodologia e classificazione"),
 ("4. Ricostruzione cronologica dell'evento", "4. Ricostruzione cronologica dell'evento", "Ricostruzione cronologica"),
 ("5. Localizzazione tecnica della compromissione e perimetro IT di Tecnosys", "5. Localizzazione della compromissione e perimetro IT", "Localizzazione tecnica"),
 ("6. Catena di fornitura e attribuzione delle responsabilità tecniche", "6. Catena di fornitura e responsabilità tecniche", "Catena di fornitura"),
 ("7. Ripristino dei servizi applicativi e continuità operativa", "7. Ripristino dei servizi applicativi e continuità operativa", "Ripristino dei servizi applicativi"),
 ("8. Inquadramento privacy: ruoli e obblighi", "8. Inquadramento privacy: ruoli e obblighi", "Inquadramento privacy"),
 ("9. Gestione della violazione e adempimenti", "9. Gestione della violazione e adempimenti", "Gestione della violazione"),
 ("10. Valutazione del rischio residuo", "10. Valutazione del rischio residuo", "Valutazione del rischio residuo"),
 ("11. Conclusioni e risposta al quesito", "11. Conclusioni e risposta al quesito", "Conclusioni e risposta al quesito"),
 ("12. Roadmap di rimedio", "12. Roadmap di rimedio", "Roadmap di rimedio"),
 ("13. Riferimenti normativi e tecnici", "13. Riferimenti normativi e tecnici", "Riferimenti normativi e tecnici"),
]

# ===================== FRONTESPIZIO =====================
para("MAD Management Advisor S.r.l.  ·  PMI Innovativa", bold=True, size=11, space_after=0, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Via Alessandro Manzoni snc, Parco Commerciale \"Le Zagare\", 95037 San Giovanni La Punta (CT)", size=9, space_after=0, align=WD_ALIGN_PARAGRAPH.CENTER)
para("P.IVA 05526830871  ·  REA CT404199  ·  SDI JI3TXCE  ·  info@management-advisor.eu", size=9, space_after=24, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(2): para("", space_after=0)
para("PERIZIA TECNICA", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=22, space_after=10)
para("Verifica del perimetro di sicurezza informatica e degli adempimenti in materia di protezione dei dati "
     "personali a seguito dell'incidente del 23 marzo 2026 occorso presso il fornitore di servizi cloud Netalia S.r.l.",
     align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=12, space_after=24)
for _ in range(2): para("", space_after=0)
para("Soggetto interessato", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=11, space_after=0)
para("Tecnosys Italia S.r.l., C.da Gentilomo snc, 94100 Enna, P.IVA 01209050861", align=WD_ALIGN_PARAGRAPH.CENTER, size=10.5, italic=True, space_after=10)
para("", space_after=0)
para("Su incarico di", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=11, space_after=0)
para("Tecnosys Italia S.r.l.", align=WD_ALIGN_PARAGRAPH.CENTER, size=10.5, space_after=24)
for _ in range(3): para("", space_after=0)
para("Protocollo: ____________________     Revisione: 00     Data: 23/05/2026", align=WD_ALIGN_PARAGRAPH.CENTER, size=10, space_after=4)
para("Documento riservato", align=WD_ALIGN_PARAGRAPH.CENTER, size=9.5, italic=True, space_after=0)
doc.add_page_break()

# ===================== INDICE =====================
h("Indice", 1)
for full, label, key in ENTRIES:
    indice_line(label, key, level=1)
doc.add_page_break()

# ===================== 1. PREMESSA E INCARICO =====================
h(ENTRIES[0][0], 1)
para("MAD Management Advisor S.r.l., su incarico di Tecnosys Italia S.r.l., ha condotto gli accertamenti tecnici "
     "relativi all'incidente di sicurezza informatica che, a partire dalla notte tra il 22 e il 23 marzo 2026, ha "
     "colpito l'infrastruttura cloud del fornitore Netalia S.r.l., utilizzata da Tecnosys per l'erogazione di servizi "
     "applicativi verso enti e amministrazioni clienti.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("L'incarico conferito richiedeva di rispondere ai seguenti quesiti:", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
bullet("se l'infrastruttura e i sistemi propri di Tecnosys siano stati oggetto di compromissione a seguito dell'attacco;")
bullet("quale sia la collocazione dell'evento lungo la catena del trattamento e a chi siano riconducibili le responsabilità tecniche;")
bullet("se la condotta tenuta da Tecnosys, sul piano tecnico e su quello degli adempimenti in materia di protezione dei dati personali, risulti diligente e coerente con le buone prassi e con il quadro normativo applicabile.")
para("Gli accertamenti e le valutazioni che seguono sono resi a sostegno dell'accountability del titolare e del "
     "responsabile del trattamento ai sensi degli artt. 5, par. 2, e 24 del Regolamento (UE) 2016/679, e a supporto "
     "della preparazione a un'eventuale attività istruttoria dell'Autorità Garante per la Protezione dei Dati "
     "Personali, anche per il tramite del Nucleo Speciale Tutela Privacy e Frodi Tecnologiche della Guardia di "
     "Finanza. Le metodologie adottate sono quelle proprie dell'analisi tecnica degli incidenti di sicurezza delle "
     "informazioni e della disamina documentale a fini di conformità.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 2. DOCUMENTAZIONE ESAMINATA =====================
h(ENTRIES[1][0], 1)
para("Ai fini degli accertamenti sono stati esaminati gli atti e le evidenze di seguito elencati, acquisiti agli "
     "atti del fascicolo:", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
bullet("relazione tecnica interna sull'incidente di sicurezza informatica;")
bullet("incident status report trasmessi dal fornitore Netalia (edizioni dell'8, del 23 e del 27 aprile 2026);")
bullet("corrispondenza e comunicazioni a mezzo posta elettronica e posta elettronica certificata intercorse con il fornitore e con i clienti nel periodo 23 marzo - 15 maggio 2026, comprese le ricevute di accettazione e di avvenuta consegna;")
bullet("documentazione contrattuale con il fornitore cloud: condizioni generali di fornitura, accordo sul trattamento dei dati e service level agreement;")
bullet("accordo quadro con la società Fintel e ordini di fornitura;")
bullet("registro delle attività di trattamento;")
bullet("registro delle violazioni dei dati personali;")
bullet("atti di nomina a responsabile e sub-responsabile del trattamento ai sensi dell'art. 28 del Regolamento;")
bullet("comunicazione di perdita definitiva dei dati trasmessa dal fornitore;")
bullet("relazione tecnica sullo stato di ripristino dei servizi applicativi.")

# ===================== 3. METODOLOGIA =====================
h(ENTRIES[2][0], 1)
para("Gli accertamenti sono stati condotti sugli atti e sulle evidenze acquisiti, mediante ricostruzione "
     "cronologica dell'evento e correlazione delle fonti tecniche e contrattuali. Ciascun elemento è qualificato per "
     "livello di verificabilità, secondo tre classi:", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
bullet("classe A: evidenze verificabili in modo autonomo da chiunque;")
bullet("classe B: evidenze basate su segnali che richiedono interpretazione tecnica;")
bullet("classe C: evidenze derivanti da accesso privilegiato o da documentazione di parte.")
para("Si rileva che gran parte delle evidenze relative alla natura tecnica dell'attacco è di classe C, in quanto "
     "proveniente dal fornitore Netalia, unico soggetto in possesso dell'accesso diretto all'infrastruttura "
     "compromessa.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 4. CRONOLOGIA =====================
h(ENTRIES[3][0], 1)
para("La tabella seguente riepiloga la sequenza degli eventi rilevanti, come ricostruita dalle fonti esaminate.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
timeline = [
 ["Notte 22-23/03/2026, ore 03:00 ca.", "Inizio dell'irraggiungibilità dei servizi cloud Netalia, ricostruito a posteriori dai log dei servizi applicativi.", "Relazione tecnica; incident report"],
 ["23/03/2026, ore 07:41", "Tecnosys segnala formalmente a Netalia l'indisponibilità totale dell'ambiente cloud e della console di virtualizzazione VMware.", "E-mail Tecnosys 23/03"],
 ["23/03/2026, ore 13:00 ca.", "Tecnosys adotta misure cautelative di contenimento: disattivazione delle connessioni VPN sui firewall perimetrali e della VPN dedicata, prima della conferma ufficiale dell'attacco.", "Relazione tecnica"],
 ["23/03/2026, pomeriggio e ore 21:00", "Netalia conferma trattarsi di attacco ransomware, con compromissione delle componenti di rete logiche e virtualizzate e dell'accessibilità a piattaforma, servizi e dati.", "Comunicati Netalia 23/03"],
 ["24/03/2026", "Netalia adotta un dominio alternativo per le comunicazioni ufficiali, indizio di compromissione estesa anche ai servizi di posta e dominio.", "Relazione tecnica"],
 ["26/03/2026", "Netalia comunica l'accertamento dell'evento ransomware e di aver effettuato le notifiche ad ACN, CSIRT, Polizia Postale e Garante.", "Comunicazione Netalia 26/03"],
 ["08/04/2026", "Netalia comunica il trasferimento del datacenter di Milano in un ambiente protetto presso Palermo e il ripristino dei relativi backup.", "Incident status report"],
 ["23/04/2026, ore 17:15", "Tecnosys trasmette a Netalia comunicazione a mezzo PEC \"ad ogni effetto di legge\", con richiesta di aggiornamento; acquisite le ricevute di accettazione e di avvenuta consegna.", "PEC e ricevute"],
 ["23-24/04/2026", "Emerge il profilo di esfiltrazione: pubblicazioni rivendicate dagli attaccanti, riferite a dati di personale Netalia; verifiche sui dati di clienti terzi dichiarate in corso.", "Incident status report"],
 ["08/05/2026", "Netalia comunica la perdita definitiva e irreversibile dei dati ospitati sulla Region Genova.", "Comunicazione data loss 08/05"],
 ["12/05/2026", "Tecnosys predispone la comunicazione strutturata ai titolari sui profili di violazione dei dati personali (artt. 33 e 34 GDPR).", "Comunicazione 12/05"],
 ["Maggio 2026", "Region Milano recuperata dai backup; Region Palermo non compromessa; cifratura dichiarata tecnicamente non reversibile.", "Incident status report; PEC data loss"],
]
add_table(["Data / ora", "Evento", "Fonte"], timeline, [3.7, 9.6, 3.9]); para("", space_after=4)

# ===================== 5. LOCALIZZAZIONE =====================
h(ENTRIES[4][0], 1)
h("5.1 Natura ed estensione dell'attacco sull'infrastruttura del fornitore", 2)
para("Dagli incident status report del fornitore l'attacco è stato identificato come ransomware della famiglia "
     "\"Qilin\", operante secondo il modello \"Ransomware as a Service\", con cifratura asimmetrica di tipo AES256. "
     "Risultano coinvolte tutte le region cloud del fornitore (Milano, Genova e Palermo) e compromessi sistemi di "
     "virtualizzazione VMware ESXi, storage SAN e repository di backup; la documentazione tecnica riferisce la "
     "compromissione di 41 host ESXi e l'eliminazione di oltre 220 snapshot. Quali possibili vettori iniziali sono "
     "indicati campagne di malvertising e l'utilizzo di credenziali pregresse rivendute da Initial Access Broker. "
     "Tutti gli indicatori di compromissione documentati afferiscono all'infrastruttura gestita da Netalia.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
h("5.2 Posizione di Tecnosys nella catena tecnica", 2)
para("Tecnosys operava quale utilizzatore dei servizi cloud e di backup erogati dal fornitore, limitatamente alla "
     "gestione delle macchine virtuali, dei servizi applicativi e delle configurazioni di propria competenza. Non "
     "disponeva di accesso fisico ai datacenter, né di accesso amministrativo agli apparati infrastrutturali, agli "
     "hypervisor, ai sistemi storage o ai repository di backup del provider, né di visibilità sulle modalità di "
     "segregazione fisica e logica degli ambienti. Le attività di gestione infrastrutturale, di sicurezza "
     "sistemistica e di protezione dei backup erano integralmente demandate al fornitore, quale gestore esclusivo "
     "dell'infrastruttura sottostante.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
h("5.3 Misure di contenimento adottate da Tecnosys", 2)
para("Nelle prime ore dell'evento, valutato il rischio di propagazione laterale verso le infrastrutture collegate, "
     "Tecnosys ha adottato misure cautelative di contenimento, disattivando intorno alle ore 13:00 del 23 marzo 2026 "
     "le connessioni VPN sui firewall aziendali e la VPN dedicata, al fine di isolare le infrastrutture collegate e "
     "prevenire eventuali compromissioni indirette. Tali misure risultano antecedenti alla conferma ufficiale "
     "dell'attacco da parte del fornitore e coerenti con le buone prassi di incident response e containment.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
h("5.4 Esito dell'accertamento sul perimetro proprio di Tecnosys", 2)
para("Dagli accertamenti svolti non emergono indicatori di compromissione (Indicators of Compromise) riferibili ai "
     "sistemi propri di Tecnosys: gli indicatori tecnici documentati afferiscono esclusivamente all'infrastruttura "
     "del fornitore. I sistemi e gli applicativi gestiti direttamente da Tecnosys non risultano oggetto di cifratura, "
     "alterazione o accesso non autorizzato, e l'evento si colloca interamente a monte, sull'infrastruttura cloud del "
     "provider.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Ai fini del consolidamento probatorio dell'esito si dispone l'acquisizione e l'analisi dei log perimetrali "
     "propri di Tecnosys (autenticazione e accessi privilegiati, firewall e gateway di posta) e degli eventi dei "
     "sistemi di monitoraggio, secondo quanto indicato nella roadmap. Gli elementi acquisiti non presentano riscontri "
     "contrari alla collocazione dell'evento sull'infrastruttura del fornitore.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 6. CATENA DI FORNITURA =====================
h(ENTRIES[5][0], 1)
para("Il rapporto con il fornitore cloud era regolato da documentazione contrattuale sottoscritta nel 2024 "
     "(condizioni generali di fornitura, accordo sul trattamento dei dati e service level agreement). Oltre "
     "all'ambiente di produzione, Tecnosys aveva sottoscritto un servizio separato e specificamente dedicato al "
     "backup infrastrutturale delle macchine virtuali, distinto sul piano economico e contrattuale e rappresentato "
     "dal fornitore come ambiente dedicato alla protezione dei dati e alla continuità operativa.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Le evidenze acquisite attestano la regolare esecuzione dei processi di backup fino alle ore immediatamente "
     "precedenti l'evento: le notifiche automatiche del sistema Veeam riportano, per il job operativo, avvio alle ore "
     "02:00 e completamento con esito \"Success\" alle ore 02:35 circa del 23 marzo 2026, senza errori né "
     "segnalazioni di anomalia. La separazione degli endpoint e dei domini di gestione tra ambiente di produzione e "
     "ambiente di backup induceva ragionevolmente a ritenere che quest'ultimo fosse logicamente segregato, secondo le "
     "ordinarie buone prassi dei servizi cloud enterprise.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Ciò nonostante, dalla comunicazione di perdita definitiva trasmessa dal fornitore è emerso che nessuna delle "
     "macchine virtuali oggetto di backup risultava recuperabile, essendo stato compromesso anche l'ambiente di "
     "backup che avrebbe dovuto garantire il disaster recovery. La perdita simultanea dell'ambiente di produzione e "
     "dell'infrastruttura di backup è incompatibile con le buone prassi di segregazione e di disaster recovery "
     "normalmente attese in servizi cloud enterprise. La responsabilità tecnica dell'evento e della perdita dei dati "
     "è pertanto riconducibile al soggetto gestore esclusivo dell'infrastruttura compromessa.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("La diligenza di Tecnosys risulta inoltre supportata dalla scelta di un fornitore qualificato e dalla "
     "sottoscrizione di servizi dedicati di protezione dei dati, nonché dalle azioni formali assunte a seguito "
     "dell'evento, tra cui la comunicazione a mezzo PEC del 23 aprile 2026, trasmessa al fornitore \"ad ogni effetto "
     "di legge\" e assistita da ricevute di accettazione e di avvenuta consegna.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 7. RIPRISTINO =====================
h(ENTRIES[6][0], 1)
para("A seguito dell'evento, Tecnosys ha attivato immediatamente il proprio presidio tecnico interno, avviando in "
     "parallelo le attività di mitigazione e di ripristino di propria competenza. La gestione conferma la netta "
     "separazione dei piani di responsabilità: le attività a livello infrastrutturale (hosting, virtualizzazione, "
     "storage e recovery environment) restano nella competenza esclusiva del fornitore Netalia, mentre Tecnosys ha "
     "condotto in autonomia, senza soluzione di continuità, tutte le attività eseguibili a livello applicativo, "
     "sistemistico e dei dati, non dipendenti dagli interventi infrastrutturali del provider.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
h("7.1 Attività autonome di ripristino", 2)
para("In attesa del completamento delle attività infrastrutturali di competenza del fornitore, Tecnosys ha avviato "
     "le lavorazioni tecnicamente possibili in autonomia:", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
bullet("analisi e classificazione degli ambienti impattati;")
bullet("recupero dai backup disponibili e clonazione degli ambienti in aree separate dalla produzione;")
bullet("ricostruzione dei dati tramite i flussi storici, con riconciliazione di notifiche e protocolli;")
bullet("predisposizione di procedure ETL di riallineamento e verifica di consistenza degli archivi documentali;")
bullet("definizione delle priorità operative sugli atti più recenti, con attività manuali integrative ove necessarie.")
h("7.2 Processo di recupero dei dati", 2)
para("Il recupero dei dati segue un workflow strutturato: conferimento dei flussi storici da parte del cliente su "
     "area dedicata; clonazione di un ambiente di lavoro separato dalla produzione; import massivo dei flussi "
     "pregressi con protocollazione tecnica temporanea; recupero dei dati anagrafici dai documenti di notifica; "
     "ricostruzione della protocollazione originaria; matching delle notifiche con i flussi provenienti dalla "
     "stamperia; controlli di congruità; travaso via ETL verso l'ambiente produttivo. Le lavorazioni procedono con "
     "priorità sugli atti temporalmente più recenti, a ritroso fino al recovery point disponibile, al fine di "
     "preservare la lavorabilità degli iter sanzionatori.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
h("7.3 Stato operativo degli ambienti", 2)
add_table(["Ambiente", "Stato operativo e attività di ripristino"], [
 ["Squillace / Sellia Marina", "Ambiente ripristinato dal backup disponibile; sistemi operativi; riallineamento dei flussi pendenti in corso."],
 ["Acquappesa", "Non emergono impatti operativi rilevanti."],
 ["Soverato", "Ambiente non avviato con Tecnosys; nessuna attività di recupero necessaria."],
 ["Locri", "Ripristino in corso mediante ricostruzione dei ruoli a partire dai dataset disponibili e dai flussi sorgente conferiti dal cliente."],
 ["Amendolara", "Ripristino mediante ricostruzione completa dei dati a partire dai flussi detenuti dal cliente."],
], [4.6, 12.6]); para("", space_after=4)
para("Alla data della presente, tutte le attività eseguibili direttamente da Tecnosys risultano avviate o "
     "pianificate e procedono in parallelo; i ripristini completi di taluni ambienti restano condizionati agli "
     "interventi infrastrutturali a basso livello di competenza del fornitore. Le attività descritte confermano la "
     "natura applicativa del perimetro operativo di Tecnosys e la dipendenza della capacità di ripristino "
     "infrastrutturale dal fornitore.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 8. PRIVACY =====================
h(ENTRIES[7][0], 1)
para("La corretta individuazione dei ruoli lungo la catena del trattamento è dirimente per stabilire quali obblighi "
     "gravassero su ciascun soggetto. Per i dati trattati per conto delle amministrazioni clienti, queste ultime "
     "rivestono la qualità di titolare del trattamento; Tecnosys opera quale responsabile del trattamento (in taluni "
     "rapporti quale sub-responsabile, all'interno di una catena che vede a monte un ulteriore responsabile); il "
     "fornitore cloud opera quale ulteriore (sub-)responsabile per la componente infrastrutturale. Tecnosys riveste, "
     "distintamente, la qualità di titolare per i trattamenti di dati propri, tra cui i dati del personale.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Ne discende che, per i dati trattati per conto dei titolari, l'obbligo di Tecnosys ai sensi dell'art. 33, par. "
     "2, del Regolamento consisteva nell'informare il titolare senza ingiustificato ritardo, mentre la notifica "
     "all'Autorità di controllo ai sensi dell'art. 33 e la comunicazione agli interessati ai sensi dell'art. 34 "
     "competono al titolare, ove ne ricorrano i presupposti e all'esito della valutazione del rischio. Per eventuali "
     "dati propri di Tecnosys che risultassero coinvolti, gli obblighi degli artt. 33 e 34 graverebbero direttamente "
     "su Tecnosys quale titolare; l'effettivo coinvolgimento di tali dati è oggetto di verifica.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
roles = [
 ["Amministrazioni / Enti clienti", "Titolare del trattamento", "Notifica all'Autorità di controllo (art. 33) e comunicazione agli interessati (art. 34) ove ricorrano i presupposti; valutazione del rischio.", "Artt. 24, 33, 34"],
 ["Tecnosys Italia S.r.l. (dati per conto dei titolari)", "Responsabile / sub-responsabile", "Informare il titolare senza ingiustificato ritardo; assistere il titolare negli adempimenti.", "Artt. 28; 33, par. 2"],
 ["Tecnosys Italia S.r.l. (dati propri)", "Titolare del trattamento", "Obblighi degli artt. 33 e 34 ove i dati propri risultino impattati (da verificare).", "Artt. 33, 34"],
 ["Netalia S.r.l.", "Gestore infrastruttura / (sub-)responsabile", "Misure tecniche e organizzative di sicurezza; informazione lungo la catena dei responsabili.", "Artt. 28, 32"],
]
add_table(["Soggetto", "Ruolo GDPR", "Obblighi principali nell'evento", "Riferimento"], roles, [4.0, 3.4, 7.4, 2.4]); para("", space_after=4)

# ===================== 9. GESTIONE =====================
h(ENTRIES[8][0], 1)
para("La gestione dell'evento risulta documentata fin dalle prime ore. Tecnosys ha segnalato l'indisponibilità al "
     "fornitore già alle ore 07:41 del 23 marzo 2026 e ha adottato in giornata misure cautelative di contenimento; "
     "ha aperto la registrazione dell'evento nel registro interno delle violazioni; ha coinvolto il Responsabile "
     "della protezione dei dati; ha mantenuto un'interlocuzione continuativa con il fornitore, culminata nella "
     "comunicazione formale a mezzo PEC del 23 aprile 2026.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Quanto all'informazione resa ai titolari sui profili di violazione dei dati personali, occorre considerare "
     "che la qualificazione dell'evento come violazione di dati personali con rischio apprezzabile per i diritti e le "
     "libertà degli interessati si è consolidata progressivamente, in funzione delle informazioni rese disponibili "
     "dal fornitore, unico soggetto tecnicamente in grado di accertare la natura e l'estensione dell'evento. Gli "
     "elementi qualificanti, in particolare il profilo di esfiltrazione (emerso a fine aprile) e la perdita "
     "definitiva e irreversibile dei dati della Region Genova (comunicata l'8 maggio 2026), sono divenuti noti in un "
     "momento successivo all'innesco dell'incidente. La comunicazione strutturata ai titolari, predisposta il 12 "
     "maggio 2026 con il richiamo agli artt. 33 e 34 del Regolamento, si colloca coerentemente con il consolidarsi di "
     "tali elementi, secondo il criterio della consapevolezza (\"awareness\") delineato dalle Linee guida EDPB "
     "9/2022, che presuppone un ragionevole grado di certezza circa l'avvenuta violazione di dati personali.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 10. RISCHIO =====================
h(ENTRIES[9][0], 1)
para("Sul perimetro informatico proprio di Tecnosys non emergono indicatori di persistenza o di compromissione: il "
     "rischio residuo sui sistemi gestiti direttamente da Tecnosys si presenta contenuto, subordinatamente al "
     "completamento delle verifiche tecniche indicate nella roadmap. Il rischio per gli interessati deriva invece "
     "dall'evento occorso presso il fornitore, sotto il profilo della disponibilità (perdita definitiva dei dati "
     "della Region Genova) e, potenzialmente, della riservatezza (profilo di esfiltrazione in corso di verifica); la "
     "sua gestione ricade nelle competenze dei titolari del trattamento, che Tecnosys è tenuta ad assistere nella "
     "qualità di responsabile.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 11. CONCLUSIONI =====================
h(ENTRIES[10][0], 1)
para("Alla luce degli accertamenti svolti si risponde ai quesiti come segue.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Quanto al primo quesito, non emergono evidenze di compromissione del perimetro informatico proprio di "
     "Tecnosys. Gli indicatori tecnici documentati afferiscono esclusivamente all'infrastruttura del fornitore "
     "Netalia; i sistemi e gli applicativi gestiti direttamente da Tecnosys non risultano violati né cifrati.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Quanto al secondo quesito, l'evento è circoscritto all'infrastruttura cloud del provider, unico gestore dei "
     "sistemi compromessi e unico soggetto in possesso dell'accesso e del controllo tecnico su di essi. La "
     "responsabilità tecnica dell'evento e della perdita dei dati, derivante dalla compromissione simultanea "
     "dell'ambiente di produzione e di quello di backup contro le buone prassi di segregazione, è riconducibile al "
     "fornitore.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Quanto al terzo quesito, la condotta di Tecnosys risulta diligente e coerente con il principio di "
     "accountability e con le buone prassi di riferimento: il contenimento tempestivo, la scelta di un fornitore "
     "qualificato e la sottoscrizione di servizi dedicati di backup sul piano tecnico; la corretta qualificazione dei "
     "ruoli, l'apertura del registro delle violazioni, il coinvolgimento del Responsabile della protezione dei dati, "
     "l'informazione resa ai titolari al consolidarsi degli elementi qualificanti e le azioni formali assunte verso "
     "il fornitore sul piano degli adempimenti. La valutazione tiene conto della dipendenza tecnica totale "
     "dall'infrastruttura del provider e della progressiva maturazione delle informazioni disponibili.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
para("Permangono margini di consolidamento, attinenti al completamento delle verifiche tecniche e all'integrazione "
     "degli atti, che non incidono sulle conclusioni sopra esposte e che sono oggetto della roadmap di rimedio al "
     "punto successivo. Il loro completamento rafforza la posizione di accountability del soggetto in vista di "
     "un'eventuale attività ispettiva.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ===================== 12. ROADMAP =====================
h(ENTRIES[11][0], 1)
para("Le azioni seguenti, ordinate per priorità, completano e consolidano il quadro evidenziale e di conformità.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
rem = [
 ["Verifica tecnica del perimetro Tecnosys", "Acquisizione e analisi dei log perimetrali (autenticazione e accessi privilegiati, firewall, gateway di posta) e degli eventi di monitoraggio, per il consolidamento probatorio dell'assenza di indicatori di compromissione.", "ISO/IEC 27001:2022 (A.8.15, A.8.16); art. 32", "Alta"],
 ["Registro delle violazioni", "Aggiornamento e integrazione con la dimensione definitiva dell'evento, le categorie di interessati e di dati coinvolte (incluse le categorie particolari ex art. 9) e l'esito delle verifiche sull'esfiltrazione.", "Art. 33, par. 5; EDPB 9/2022", "Alta"],
 ["Nomine ex art. 28", "Formalizzazione e perfezionamento degli atti di nomina a responsabile e sub-responsabile lungo l'intera catena del trattamento, con le clausole su sicurezza, notifica delle violazioni e sub-responsabili autorizzati.", "Art. 28, par. 2, 3 e 4", "Alta"],
 ["Valutazione del rischio per gli interessati", "Conduzione di una valutazione strutturata del rischio sull'evento, a supporto delle decisioni di notifica e comunicazione dei titolari.", "Artt. 33 e 34; EDPB 9/2022", "Media"],
 ["Rafforzamento del perimetro", "Sostituzione degli apparati datati, adozione dell'autenticazione a più fattori sugli accessi privilegiati, hardening e gestione delle vulnerabilità.", "Art. 32; ISO/IEC 27001:2022 (A.8.5, A.8.8)", "Media"],
 ["Resilienza dei dati e governo del fornitore", "Introduzione di copie di backup geograficamente distinte e di clausole di audit e di notifica tempestiva delle violazioni nei contratti con i fornitori.", "Art. 28; ISO/IEC 27001:2022 (A.8.13)", "Media"],
 ["Conservazione delle evidenze", "Congelamento e conservazione delle evidenze con criteri di catena di custodia, in vista di eventuale attività ispettiva o giudiziaria.", "ISO/IEC 27037; accountability", "Media"],
]
add_table(["Area", "Azione", "Riferimento", "Priorità"], rem, [3.6, 8.8, 3.4, 1.4]); para("", space_after=8)

# ===================== 13. RIFERIMENTI =====================
h(ENTRIES[12][0], 1)
para("Gli accertamenti e le valutazioni fanno riferimento al seguente quadro normativo e tecnico:", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
bullet("Regolamento (UE) 2016/679 (GDPR), artt. 5, 24, 28, 30, 32, 33 e 34;")
bullet("D.Lgs. 196/2003 (Codice Privacy), artt. 154, 157, 158 e 166;")
bullet("Provvedimento del Garante per la Protezione dei Dati Personali del 27 novembre 2008 in materia di amministratori di sistema;")
bullet("Linee guida EDPB 9/2022 sulla notifica delle violazioni dei dati personali;")
bullet("ISO/IEC 27001:2022 e ISO/IEC 27035 in materia di sicurezza delle informazioni e gestione degli incidenti;")
bullet("NIST Cybersecurity Framework 2.0;")
bullet("UNI EN ISO 19011:2018 e UNI ISO 31000:2018.")
para("", space_after=10)

# ===================== FIRMA =====================
para("Luogo e data: San Giovanni La Punta, 23/05/2026", space_after=18)
para("Per MAD Management Advisor S.r.l.", bold=True, space_after=18)
para("Il Legale Rappresentante", space_after=2)
para("____________________________________", space_after=12)
para("Documento riservato. Le informazioni contenute sono destinate esclusivamente al soggetto interessato e non possono essere divulgate a terzi senza autorizzazione.", size=8.5, italic=True)

# ===================== HEADER / FOOTER =====================
header = sec.header; header.is_linked_to_previous = False
hp = header.paragraphs[0]; hp.text = ""; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
hr = hp.add_run("Perizia tecnica  ·  Incidente Netalia 23/03/2026  ·  Documento riservato"); set_run(hr, size=8, italic=True, color=(90,90,90))
footer = sec.footer; footer.is_linked_to_previous = False
fp = footer.paragraphs[0]; fp.text = ""; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
f1 = fp.add_run("MAD Management Advisor S.r.l.  ·  PMI Innovativa  ·  P.IVA 05526830871"); set_run(f1, size=8, color=(90,90,90))
fp2 = footer.add_paragraph(); fp2.alignment = WD_ALIGN_PARAGRAPH.CENTER; fp2.paragraph_format.space_before = Pt(0)
g1 = fp2.add_run("Pag. "); set_run(g1, size=8, color=(90,90,90))
fld1 = OxmlElement("w:fldSimple"); fld1.set(qn("w:instr"), "PAGE"); fp2._p.append(fld1)
g2 = fp2.add_run(" di "); set_run(g2, size=8, color=(90,90,90))
fld2 = OxmlElement("w:fldSimple"); fld2.set(qn("w:instr"), "NUMPAGES"); fp2._p.append(fld2)

# ===================== METADATI =====================
cp = doc.core_properties
cp.author = "MAD Management Advisor S.r.l."; cp.last_modified_by = "MAD Management Advisor S.r.l."
cp.title = "Perizia tecnica - Incidente Netalia 23/03/2026 - Verifica perimetro IT e adempimenti privacy"
cp.subject = "Tecnosys Italia S.r.l."; cp.category = "Perizia tecnica"; cp.comments = ""
cp.keywords = "data breach; GDPR; perimetro IT; accountability"

doc.save(OUT)
print("SAVED:", OUT, "| pagemap entries:", len(PAGE_MAP))
