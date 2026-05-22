## Cosa cambia

<!-- Descrivi sinteticamente cosa cambia con questa PR. Una frase per riga, bullet se servono. -->

## Perche

<!-- Motivazione del cambio. Quale problema risolve? Quale feature abilita? Quale debito tecnico riduce? -->

## Test eseguiti

<!-- Cosa hai testato concretamente. NON dire "ho testato tutto" - elenca i flussi. -->

- [ ] Lint frontend (`pnpm run lint`)
- [ ] Typecheck frontend (`pnpm run typecheck`)
- [ ] Test frontend (`pnpm run test`)
- [ ] Lint backend (`uv run ruff check`)
- [ ] Typecheck backend (`uv run mypy sco_compliance_os`)
- [ ] Test backend (`uv run pytest`)
- [ ] Cargo check + clippy (`cargo check && cargo clippy`)
- [ ] Smoke E2E manuale (`pnpm tauri dev` + flow critico)

## Checklist

- [ ] Codice formattato (ruff format + prettier + cargo fmt)
- [ ] Test aggiunti per nuova funzionalita
- [ ] Documentazione aggiornata (README + commenti inline)
- [ ] Changelog aggiornato se rilascio user-visible
- [ ] Nessun secret committato (verifica gitleaks locale: `gitleaks detect`)
- [ ] Conv. 47 BUMP VERSION: se bump version, eseguito grep no-residui post-bump

## Convenzione di commit

<!-- Conventional Commits 1.0.0. Esempi:
  feat: nuova feature visibile all'utente
  fix: bug fix visibile all'utente
  docs: solo documentazione
  refactor: refactoring senza cambio behavior
  perf: miglioramento performance
  test: aggiunta/modifica test
  chore: tooling, deps, CI
  build: cambi al sistema di build (Tauri, PyInstaller, pnpm)
  ci: cambi a GitHub Actions
-->

Prefisso commit: `<tipo>(<scope opzionale>): <descrizione breve>`

## Issue collegata

<!-- Closes #XXX o relativo a #XXX -->
