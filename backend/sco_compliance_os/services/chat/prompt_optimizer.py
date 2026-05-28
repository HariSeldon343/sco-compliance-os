"""Ottimizzazione silenziosa del prompt utente (Feature 4 componente A, v0.15.0).

Quando l'utente invia un messaggio in chat, il backend lo arricchisce con un
meta-wrapper di chiarezza PRIMA di passarlo all'LLM, in modo SILENZIOSO:

- l'utente vede e il DB persiste il messaggio ORIGINALE (chat history pulita);
- l'LLM riceve la versione ottimizzata (risposta piu strutturata e completa).

Approccio rule-based deterministico (nessuna chiamata LLM extra = zero latenza
e zero costo aggiuntivo). Applica una versione condensata dello "Schema del
Prompt Perfetto": esplicita task, completezza, gestione delle assunzioni.

Disattivabile via parametro `enabled` (per il toggle Impostazioni futuro).
"""

from __future__ import annotations

# Lunghezza minima sotto la quale non vale la pena ottimizzare (saluti, conferme).
_MIN_LENGTH = 12

# Marcatore di chiarezza appeso al messaggio (istruzione meta per l'LLM).
_META_WRAPPER = (
    "\n\n[Elaborazione: interpreta la richiesta sopra in modo completo e "
    "strutturato. Se mancano dettagli rilevanti, esplicita le assunzioni fatte. "
    "Dai una risposta precisa, azionabile e priva di riempitivi.]"
)


def should_optimize(message: str) -> bool:
    """Decide se il messaggio merita ottimizzazione.

    Skip per: messaggi vuoti/brevi, slash command, messaggi gia strutturati
    (multi-riga con markdown), conferme monosillabiche.
    """
    stripped = message.strip()
    if len(stripped) < _MIN_LENGTH:
        return False
    if stripped.startswith("/"):
        return False
    # Gia strutturato dall'utente: rispetta la sua formattazione.
    if "\n" in stripped and any(
        line.lstrip().startswith(("#", "-", "*", "1.", "```")) for line in stripped.splitlines()
    ):
        return False
    # Conferme/comandi monosillabici frequenti.
    if stripped.lower() in {"ok", "si", "sì", "no", "procedi", "vai", "grazie", "continua"}:
        return False
    return True


def optimize_prompt(message: str, *, enabled: bool = True) -> tuple[str, bool]:
    """Ottimizza silenziosamente il prompt utente.

    Args:
        message: messaggio originale dell'utente.
        enabled: se False, ritorna il messaggio invariato (toggle Impostazioni).

    Returns:
        (prompt_per_llm, was_optimized). `prompt_per_llm` e' la versione da
        inviare all'LLM; se non ottimizzato, coincide con `message`.
        `was_optimized` indica se e' stata applicata l'ottimizzazione (per il
        marker discreto nel log, non mostrato all'utente).
    """
    if not enabled or not should_optimize(message):
        return message, False
    return message.strip() + _META_WRAPPER, True
