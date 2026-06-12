# Local API Memory, Fast Grounded Answers, and Public Seed Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use $superpower-subagents (recommended) or $superpower-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking via update_plan.

**Goal:** Make locally remembered API configurations reusable without retyping secrets, stream faster database-grounded answers, and publish audited de-identified seed data containing 93 cases and 230 articles.

**Architecture:** The Flask backend remains the sole authority for saved API secrets, while the browser stores only a saved configuration ID and non-secret UI preferences. A focused evidence-routing layer selects compact case/article context per question type. A standalone seed-data module generates deterministic de-identified JSON and initializes only empty runtime stores.

**Tech Stack:** Python 3, Flask, OpenAI-compatible SDK, vanilla JavaScript, JSON persistence, `unittest`, Git/GitHub.

---

## File Map

- Create `core/api_config_store.py`: normalize, mask, activate, clear, and resolve local API configurations.
- Create `core/evidence_context.py`: classify medical questions and build compact database evidence payloads.
- Create `core/seed_data.py`: de-identify runtime records, audit seed data, and initialize empty runtime stores.
- Create `scripts/build_public_seed.py`: command-line seed generator and privacy audit.
- Create `data/seed/user_cases.json` and `data/seed/articles.json`: audited public defaults.
- Modify `app.py`: use the focused modules, stream responses, initialize seed data, and expose remembered-config state safely.
- Modify `core/chat_routing.py`: restore explicit evidence requests and distinguish general medical grounding.
- Modify `core/llm_client.py`: finalize bounded streaming, partial fallback, compact context, and request IDs.
- Modify `static/js/app.js`: never require or resend a remembered secret; handle streamed chunks and partial failures.
- Modify `.gitignore`: continue excluding runtime/API secrets while allowing only `data/seed/*.json`.
- Modify `README.md` and version notes: document local secret storage and bundled de-identified database.
- Create tests for API config, evidence routing, stream behavior, seed generation, and startup initialization.

### Task 1: Preserve Existing Work and Establish Baseline

**Files:**
- Inspect: `app.py`, `core/chat_routing.py`, `core/llm_client.py`, `static/js/app.js`, `templates/index.html`
- Test: `tests/`

- [ ] Run `python -m unittest discover -s tests -v` and record the current failures caused by the uncommitted streaming/token changes.
- [ ] Run Python compilation and JavaScript syntax checks.
- [ ] Inspect the five-file diff and classify each hunk as user work to preserve, required implementation, or conflicting behavior.
- [ ] Commit only after subsequent tasks bring the preserved work under tests.

### Task 2: Backend-Owned Remembered API Configuration

**Files:**
- Create: `core/api_config_store.py`
- Create: `tests/test_api_config_store.py`
- Modify: `app.py`

- [ ] Write failing tests proving that a masked remembered configuration can be activated by `config_id`, resolved with its full local key, and serialized without exposing that key.
- [ ] Run `python -m unittest tests.test_api_config_store -v`; expect failures because the store module does not exist.
- [ ] Implement `ApiConfigStore` with `current_masked()`, `history_masked()`, `save_verified()`, `activate()`, `resolve_request_config()`, and `clear_all()`.
- [ ] Make `resolve_request_config()` prefer an explicitly supplied non-empty key, otherwise use the active locally saved key when `use_saved_config` or `config_id` is supplied.
- [ ] Update Flask config endpoints and chat endpoints to use the store and never return plaintext secrets.
- [ ] Run the focused tests and existing API/LLM tests; expect all to pass.
- [ ] Commit as `Fix local remembered API activation`.

### Task 3: Browser Uses Saved Configuration Without Secret Re-entry

**Files:**
- Create: `tests/test_frontend_contract.py`
- Modify: `static/js/app.js`
- Modify: `templates/index.html`

- [ ] Write a failing static contract test proving `apiPayloadExtras()` sends `use_saved_config` and `config_id` while it does not read `API_KEY_STORAGE` for normal chat requests.
- [ ] Run `python -m unittest tests.test_frontend_contract -v`; expect failure against the current browser payload.
- [ ] Remove new plaintext-key writes to browser local storage and clear legacy key storage on startup after backend state is loaded.
- [ ] When a remembered configuration is selected, persist only its ID/provider/model/base URL and send that ID with chat requests.
- [ ] Allow the key input to remain blank when testing or saving an already active remembered configuration; require a key only when creating/replacing one.
- [ ] Update UI labels to state that the backend-local key is active.
- [ ] Run focused tests and `node --check static/js/app.js`.
- [ ] Commit as `Use remembered API configs without retyping keys`.

### Task 4: Fast Streaming and Timeout Fallback

**Files:**
- Create: `tests/test_llm_streaming.py`
- Modify: `core/llm_client.py`
- Modify: `app.py`
- Modify: `static/js/app.js`
- Modify: `tests/test_llm_policy.py`

- [ ] Write failing tests for bounded token policies, zero retries, generated request IDs, streamed text chunks, and local fallback when a timeout occurs before any chunk.
- [ ] Run the focused tests and confirm the expected failures against the current uncommitted implementation.
- [ ] Complete provider streaming using Responses streaming for OpenAI and Chat Completions streaming for compatible providers; retain Anthropic SSE support.
- [ ] Use 350 tokens for general answers and 550 for initial analysis, eight recent messages, a 10-second connect timeout, and provider-aware 45-75 second read timeout with zero retries.
- [ ] Make stream errors include the request ID. Preserve received partial text; use local fallback only if nothing was received.
- [ ] Make the Flask SSE endpoint emit `chunk`, `error`, and `done` events consistently and add no-buffer headers.
- [ ] Make the browser render the first chunk immediately, retain partial output, and show a short timeout note instead of replacing useful text.
- [ ] Run focused tests, full Python tests, Python compilation, and JavaScript syntax checks.
- [ ] Commit as `Stream bounded provider responses with fast fallback`.

### Task 5: Database-Grounded Evidence Routing

**Files:**
- Create: `core/evidence_context.py`
- Create: `tests/test_evidence_context.py`
- Modify: `core/chat_routing.py`
- Modify: `app.py`
- Modify: `core/llm_client.py`
- Modify: `tests/test_chat_routing.py`

- [ ] Write failing routing tests for detailed analysis, explicit evidence retrieval, case follow-up, general medical questions, and unrelated questions.
- [ ] Write failing evidence tests proving general medical questions receive relevant article excerpts but no case cards, while explicit case requests receive both cases and articles.
- [ ] Restore explicit retrieval terms removed by the current uncommitted diff and add a `general_medical` route that does not use patient context.
- [ ] Implement compact evidence builders capped at four case excerpts, four article excerpts, and a small digest.
- [ ] Require the model instructions to identify local database evidence by stable IDs and clearly separate it from general knowledge.
- [ ] Update both JSON and SSE chat endpoints to share one report-building function and avoid duplicated routing logic.
- [ ] Run focused tests and the full suite.
- [ ] Commit as `Ground medical answers in local evidence`.

### Task 6: De-identified Public Seed Generator

**Files:**
- Create: `core/seed_data.py`
- Create: `scripts/build_public_seed.py`
- Create: `tests/test_seed_data.py`
- Modify: `.gitignore`

- [ ] Write failing tests using synthetic identifying fields to prove names, hospital IDs, record IDs, local paths, source names, API keys, and unsafe image references are removed.
- [ ] Write failing tests proving deterministic `SEED-CASE-001` IDs, exact record counts, and article content preservation.
- [ ] Implement field allowlists, identity-pattern redaction, deterministic IDs, source metadata removal, image removal by default, and a recursive secret/path audit.
- [ ] Implement a CLI accepting runtime data and output directories and failing nonzero when counts or privacy checks fail.
- [ ] Allow only `data/seed/user_cases.json` and `data/seed/articles.json` through `.gitignore`; keep API config, runtime uploads, backups, and ordinary `data/user_cases.json` ignored.
- [ ] Run focused tests.
- [ ] Commit as `Add audited public seed data generator`.

### Task 7: Generate and Audit the 93/230 Seed Database

**Files:**
- Create: `data/seed/user_cases.json`
- Create: `data/seed/articles.json`
- Create: `data/seed/manifest.json`

- [ ] Run the generator against `C:\Users\ASUS\.uscc_scc_flask_data` with expected counts 93 and 230.
- [ ] Audit every string recursively for identity labels, Windows user paths, email/phone/ID patterns, API key patterns, and local upload references.
- [ ] Manually sample at least ten cases including the 17 imaging-derived cases and ten articles.
- [ ] Confirm no image files or API configuration files are staged.
- [ ] Commit as `Bundle de-identified case and article seed data`.

### Task 8: Initialize Fresh Installs from Seed Data

**Files:**
- Modify: `core/seed_data.py`
- Modify: `app.py`
- Create: `tests/test_seed_initialization.py`

- [ ] Write failing tests proving an empty runtime directory receives 93 cases and 230 articles, while an existing non-empty runtime directory is not overwritten.
- [ ] Implement `initialize_runtime_from_seed()` before ordinary storage-file creation.
- [ ] Record seed version in migration state without copying any API configuration.
- [ ] Run focused tests and a Flask smoke test with a temporary `USCC_DATA_DIR`.
- [ ] Commit as `Initialize new installs from public seed data`.

### Task 9: Documentation, Security Audit, and Release Verification

**Files:**
- Modify: `README.md`
- Create: `docs/notes/README_V38_CHANGES.md`
- Modify: `docs/notes/README.md`

- [ ] Document local API storage, remembered-config behavior, streaming, evidence grounding, de-identified seed counts, and privacy limits.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run Python compilation and Node syntax checks.
- [ ] Run Flask smoke tests against a fresh temporary runtime and verify summary counts 93/230.
- [ ] Run `git diff --check`, inspect `git status`, and scan all staged files for API key patterns and local API config filenames.
- [ ] Verify the user's existing title/UI modification remains present.
- [ ] Commit as `Document V38 local memory and public database`.

### Task 10: Publish to GitHub

**Files:**
- Git branch and GitHub repository: `lihao123456521/AI-for-medical-science`

- [ ] Confirm the final diff contains only intended source, tests, documentation, and audited seed JSON.
- [ ] Confirm no plaintext key appears in Git history being pushed by scanning commits ahead of `origin/main`.
- [ ] Push the verified branch to `origin`.
- [ ] Use the connected GitHub app to confirm the remote commit and public seed files are visible.
- [ ] Report the commit SHA, GitHub URL, verification counts, and the exact local runtime path that retains private API configurations.

## Verification

Completion requires all unit tests passing, clean Python/JavaScript syntax checks, fresh-install Flask summary counts of 93 cases and 230 articles, zero privacy/secret audit findings, no tracked API config files, and successful GitHub synchronization.

**Next skill:** `$superpower-executing-plans`
