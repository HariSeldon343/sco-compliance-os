// SCO Compliance OS — fetch wrapper con retry exponential backoff.
// Risolve race condition v1.0.0: frontend Tauri WebView2 carica 200ms,
// sidecar PyInstaller v1.0.0 (61 MB con 14 router + openai + gemini hidden imports)
// impiega 5-10 sec per bind porta 7800. Senza retry, primo fetch sempre fallisce
// con "Failed to fetch" → toast "Errore. Riprova fra qualche secondo." visibile
// confondendo l'utente al primo avvio post-install fresh.
//
// Pattern: 5 retry totali con backoff 500ms / 1s / 2s / 4s / 8s (cumulative ~15s)
// che copre il worst-case startup sidecar PyInstaller bundle pesante.

const DEFAULT_MAX_RETRIES = 5;
const DEFAULT_BASE_MS = 500;

export interface FetchWithRetryOptions extends RequestInit {
  maxRetries?: number;
  baseMs?: number;
  /** Callback invocato al primo errore + ogni retry. Utile per mostrare "Connessione backend..." */
  onRetry?: (attempt: number, error: unknown) => void;
}

/**
 * fetch wrapper con retry exponential backoff per assorbire race condition
 * frontend ↔ sidecar startup. Solleva solo dopo MAX_RETRIES fallimenti.
 *
 * Treat as retriable: network errors (TypeError "Failed to fetch") + HTTP 5xx.
 * NOT retriable: HTTP 4xx (validazione, auth) → solleva subito per non mascherare bug.
 */
export async function fetchWithRetry(
  url: string,
  options: FetchWithRetryOptions = {},
): Promise<Response> {
  const {
    maxRetries = DEFAULT_MAX_RETRIES,
    baseMs = DEFAULT_BASE_MS,
    onRetry,
    ...fetchOpts
  } = options;

  let lastError: unknown = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const res = await fetch(url, fetchOpts);
      // HTTP 5xx → retry. HTTP 4xx → fail subito (errore client).
      if (res.status >= 500 && res.status < 600) {
        lastError = new Error(`HTTP ${res.status} (server error, retry)`);
        if (onRetry) onRetry(attempt + 1, lastError);
        if (attempt < maxRetries - 1) {
          await sleep(baseMs * Math.pow(2, attempt));
          continue;
        }
        return res; // ultimo tentativo, ritorna response 5xx per gestione esplicita
      }
      return res; // 2xx / 3xx / 4xx → ritorna senza retry
    } catch (err) {
      lastError = err;
      if (onRetry) onRetry(attempt + 1, err);
      if (attempt < maxRetries - 1) {
        await sleep(baseMs * Math.pow(2, attempt));
      }
    }
  }

  // Tutti i retry falliti → solleva ultimo errore.
  throw lastError ?? new Error("fetchWithRetry: failed after all retries");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
