// SCO Compliance OS — parser tag inline emessi dal backend nei text_delta.
//
// Bug v1.0.2: alcuni skill emettono tag testuali dentro il `content` del
// messaggio assistant invece di usare i campi strutturati `ask_user_question`
// del payload Conv. 48. Conseguenza: il frontend mostra raw text tipo
// `<ASK_USER_QUESTION>{"question":"...","options":[...]}</ASK_USER_QUESTION>`
// invece del widget cliccabile.
//
// Questo parser intercetta i tre tag inline conosciuti, estrae il JSON
// payload e produce una lista ordinata di segmenti (text | ask | tool_call
// | tool_result) che il renderer di MessageBubble compone correttamente.
//
// Pattern Conv. 47 SINGLE SOURCE OF TRUTH: il payload strutturato lato DB
// (`ask_user_question_json`) resta la fonte di verita preferita. Il parser
// inline interviene SOLO quando quel campo e' null ma il content contiene
// il tag testuale. Niente duplicazione del dato.

/** Singola opzione cliccabile della domanda inline. */
export interface InlineAskOption {
  /** Identificativo opaco — usato come body POST verso il backend. */
  value: string;
  /** Etichetta visibile sul bottone. */
  label: string;
  /** Eventuale descrizione breve. */
  description?: string;
}

/** Payload domanda strutturata inline (formato emesso dagli skill backend). */
export interface InlineAskPayload {
  /** Testo della domanda. */
  question: string;
  /** Opzioni cliccabili. */
  options: InlineAskOption[];
  /** v0.11.0: se true, l'utente puo' selezionare piu' opzioni + invia con bottone. */
  multi_select?: boolean;
  /** v0.11.0: se true, accetta input free-text oltre alle opzioni (campo "Altro"). */
  allow_free_text?: boolean;
}

/** Payload tool call inline. */
export interface InlineToolCallPayload {
  /** Nome del tool invocato. */
  tool_name?: string;
  /** Argomenti passati al tool (forma libera). */
  args?: Record<string, unknown>;
  /** Eventuale ID del tool_use. */
  id?: string;
}

/** Payload tool result inline. */
export interface InlineToolResultPayload {
  /** Nome del tool che ha emesso il risultato. */
  tool_name?: string;
  /** Risultato (stringa o JSON arbitrario). */
  result?: unknown;
  /** Riferimento al tool_use_id corrispondente. */
  id?: string;
  /** Flag errore. */
  is_error?: boolean;
}

/** Segmento di rendering prodotto dal parser. */
export type ContentSegment =
  | { kind: "text"; text: string }
  | {
      kind: "ask";
      payload: InlineAskPayload;
      /** Indice progressivo dentro il messaggio (per stable key). */
      index: number;
      /** Substring originale del tag (utile per debugging). */
      raw: string;
    }
  | {
      kind: "tool_call";
      payload: InlineToolCallPayload;
      index: number;
      raw: string;
    }
  | {
      kind: "tool_result";
      payload: InlineToolResultPayload;
      index: number;
      raw: string;
    };

// Regex multi-tag: cattura ASK_USER_QUESTION / TOOL_CALL / TOOL_RESULT con
// la coppia di chiusura corrispondente. Il body interno e' lazy (`[\s\S]*?`)
// per non incollare due tag consecutivi. Il flag `g` consente match multipli
// nello stesso content. Il backend ha emesso anche varianti con chiusura
// abbreviata `</>` (vedi commit storia): supportiamo entrambe le forme.
const TAG_REGEX = /<(ASK_USER_QUESTION|TOOL_CALL|TOOL_RESULT)>([\s\S]*?)<\/(?:\1|)>/g;

/**
 * Estrae i segmenti rendering-ready da un content markdown grezzo.
 *
 * Esempio input:
 * ```
 * Ti faccio una domanda:
 * <ASK_USER_QUESTION>{"question":"Come usi questo vault?","options":[...]}</ASK_USER_QUESTION>
 * Aspetto la risposta.
 * ```
 *
 * Output: 3 segmenti — text ("Ti faccio una domanda:\n"), ask (payload),
 * text ("\nAspetto la risposta.").
 *
 * Se il content non contiene nessun tag conosciuto, ritorna un singolo
 * segmento `text` con l'intero content (path no-op piu' performante).
 *
 * Resilient parsing: se il JSON interno e' malformato il tag viene
 * preservato come testo grezzo (cosi' l'utente vede comunque qualcosa)
 * e il parser prosegue.
 */
export function parseInlineWidgets(content: string): ContentSegment[] {
  if (!content || !content.includes("<")) {
    return [{ kind: "text", text: content }];
  }

  const segments: ContentSegment[] = [];
  let lastEnd = 0;
  let matchIndex = 0;
  // Reset lastIndex su ogni call (regex globale e' stateful).
  TAG_REGEX.lastIndex = 0;

  for (
    let match = TAG_REGEX.exec(content);
    match !== null;
    match = TAG_REGEX.exec(content)
  ) {
    const [raw, tagName, jsonBody] = match;
    const start = match.index;
    const end = start + raw.length;

    // Append testo precedente al tag, se presente
    if (start > lastEnd) {
      const before = content.slice(lastEnd, start);
      if (before.length > 0) {
        segments.push({ kind: "text", text: before });
      }
    }

    // Tenta parse JSON: se fallisce, preserva come testo grezzo
    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonBody);
    } catch {
      segments.push({ kind: "text", text: raw });
      lastEnd = end;
      continue;
    }

    if (tagName === "ASK_USER_QUESTION") {
      const askPayload = normalizeAskPayload(parsed);
      if (askPayload) {
        segments.push({
          kind: "ask",
          payload: askPayload,
          index: matchIndex,
          raw,
        });
        matchIndex += 1;
      } else {
        // Schema non valido — fallback a testo
        segments.push({ kind: "text", text: raw });
      }
    } else if (tagName === "TOOL_CALL") {
      segments.push({
        kind: "tool_call",
        payload: (parsed as InlineToolCallPayload) ?? {},
        index: matchIndex,
        raw,
      });
      matchIndex += 1;
    } else if (tagName === "TOOL_RESULT") {
      segments.push({
        kind: "tool_result",
        payload: (parsed as InlineToolResultPayload) ?? {},
        index: matchIndex,
        raw,
      });
      matchIndex += 1;
    }

    lastEnd = end;
  }

  // Append eventuale coda di testo dopo l'ultimo tag
  if (lastEnd < content.length) {
    const tail = content.slice(lastEnd);
    if (tail.length > 0) {
      segments.push({ kind: "text", text: tail });
    }
  }

  // Se nessun tag e' stato matchato, ritorna l'intero content come singolo text
  if (segments.length === 0) {
    return [{ kind: "text", text: content }];
  }

  return segments;
}

/**
 * Normalizza un payload `<ASK_USER_QUESTION>` validandone lo schema minimo.
 *
 * Accetta due varianti di campo per ogni opzione:
 * - `{value, label, description?}` (formato emesso dagli skill backend SCO)
 * - `{id, label, description?}` (formato strutturato Conv. 48 widget DB)
 *
 * In entrambi i casi la normalizzazione produce `{value, label, description?}`
 * per uniformare il contratto verso AskQuestionCard.
 *
 * Ritorna `null` se la shape non e' valida (manca `question` o `options[]`).
 */
function normalizeAskPayload(raw: unknown): InlineAskPayload | null {
  if (typeof raw !== "object" || raw === null) return null;
  const obj = raw as Record<string, unknown>;

  // Accetta sia `question` (formato skill) sia `prompt` (formato Conv. 48 widget)
  const question =
    typeof obj.question === "string"
      ? obj.question
      : typeof obj.prompt === "string"
        ? obj.prompt
        : null;
  if (!question) return null;

  if (!Array.isArray(obj.options)) return null;
  const options: InlineAskOption[] = [];
  for (const opt of obj.options) {
    if (typeof opt !== "object" || opt === null) continue;
    const optObj = opt as Record<string, unknown>;
    const label = typeof optObj.label === "string" ? optObj.label : null;
    // v0.12.1 fix Bug H smoke v0.12.0: il system prompt skill proposal EPSILON
    // istruisce l'LLM a emettere {"label":"slug","description":"..."} senza
    // campo "value" esplicito. Conv. 47 SSOT: fallback resiliente label -> value
    // per non bloccare il render del widget. Se anche "label" manca, skip.
    const value =
      typeof optObj.value === "string"
        ? optObj.value
        : typeof optObj.id === "string"
          ? optObj.id
          : label; // fallback: label come value (slug-friendly per skill proposal)
    if (!value || !label) continue;
    const description =
      typeof optObj.description === "string" ? optObj.description : undefined;
    options.push({ value, label, description });
  }

  if (options.length === 0) return null;

  // v0.11.0: propaga multi_select dal payload backend.
  const multi_select = obj.multi_select === true;

  // Conv. 49 enforcement (26/05/2026): "Altro" e' SEMPRE disponibile come
  // ultima opzione del widget. Il widget lo aggiunge in automatico,
  // indipendentemente dal payload dell'agente. Tre passi:
  //
  //   1. Filtra (deduplica) eventuali opzioni "altro/free_text/other"
  //      che l'agente potrebbe aver dichiarato per inerzia/hallucination.
  //   2. Append opzione "Altro" canonica come ultima posizione.
  //   3. Set allow_free_text: true sempre (la textbox si attiva al click).
  //
  // Backward compat: se in futuro qualche skill specifica vuole disabilitare
  // "Altro" (es. multiple-choice didattico con risposta unica corretta), puo'
  // emettere `disable_altro: true` nel payload — non implementato oggi.
  const FREE_TEXT_VALUE_SET = new Set(["altro", "free_text", "other"]);
  const dedupedOptions = options.filter(
    (o) => !FREE_TEXT_VALUE_SET.has(o.value.toLowerCase()),
  );
  dedupedOptions.push({
    value: "altro",
    label: "Altro",
    description: "Scrivi una risposta libera",
  });
  const allow_free_text = true;

  return {
    question,
    options: dedupedOptions,
    multi_select,
    allow_free_text,
  };
}
