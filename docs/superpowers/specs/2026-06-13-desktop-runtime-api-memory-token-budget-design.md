# Desktop Runtime, API Memory, and Token Budget Design

## Problem

The desktop shortcut starts `D:\uscc_scc_flask_fixed`, an obsolete non-Git installation, while current development and releases live in the Git repository. The old runtime only saves API configurations after a successful connection test, sends non-streaming requests with a 1200-token output allowance, and exposes raw provider errors. Therefore recent fixes never reach desktop users, slow connection tests cause remembered keys to disappear, and repeated large requests can exhaust a provider's rolling token quota.

## Goals

- Make the desktop shortcut and launcher run one canonical, current installation.
- Preserve the user's existing local cases, articles, uploads, settings, and API key during migration.
- Save API credentials locally before connection testing and restore them after restart without returning plaintext to the browser.
- Bound prompt and output tokens, stream responses, prevent duplicate submissions, and never retry paid requests automatically.
- Convert provider 429 responses into a concise message with reset time and no API-key identifier or automatic local-answer substitution.
- Publish the corrected behavior in GitHub source and downloadable packages.

## Canonical Runtime And Migration

The Git repository remains the source of truth. `D:\uscc_scc_flask_fixed` is upgraded in place from the verified release tree because the existing desktop shortcut and virtual environment already target that location. Before replacement, the full old application directory and `C:\Users\ASUS\.uscc_scc_flask_data` are backed up to timestamped directories.

Runtime data remains under `C:\Users\ASUS\.uscc_scc_flask_data`; application files never contain API keys. The migration excludes `.git`, `dist`, build directories, `.env`, runtime JSON files, and uploads from source replacement. Existing runtime data is not overwritten by public seed data.

The launcher writes and verifies the desktop shortcut against its own `BASE_DIR`. On startup it checks the health endpoint's build identifier. A healthy service with a different build identifier is treated as stale: the launcher must not silently attach to it. The migration stops the currently running obsolete service before replacing files and restarts the upgraded service.

## API Memory

API configurations are written atomically to `api_config.json` and `api_config_history.json` before any network test. `test_ok` records test status but does not control persistence or eligibility for chat. Selecting a remembered configuration sends only `config_id`; the backend resolves the full key from local storage. The browser stores provider, model, base URL, and config ID only.

The configuration modal shows a masked key and a clear status. Opening or selecting a remembered configuration must never require key re-entry. Clearing configurations deletes both local backend files and legacy browser plaintext values.

## Request Budget And 429 Handling

All online chat uses streaming and zero automatic retries. The request builder limits conversation history, patient text, cases, articles, digest fields, attachment metadata, and output tokens. It preserves top-ranked database evidence and identifiers while clipping long text. The frontend disables send until the active request finishes and aborts only after the provider-specific inactivity window.

429 errors are classified separately from authentication, balance, and timeout failures. The sanitizer removes `api_key` identifiers and hashes from provider text, extracts an ISO/UTC reset timestamp when available, and returns a Chinese message stating that the provider's rolling token quota is exhausted and when it resets. A failed online request remains an online-request error; the application does not append a generated local fallback answer because that can disguise the failure and encourage immediate resubmission.

## Verification

- Unit tests cover unverified local persistence, restart resolution, context bounds, streaming/no-retry policy, duplicate-send prevention, and sanitized 429 messages.
- An endpoint test saves a key with a simulated timeout, recreates the store, and resolves it by config ID.
- A migration smoke test backs up a fixture old install, installs current files, preserves runtime data, and verifies the shortcut target.
- A real desktop smoke test stops the old service, launches from the desktop shortcut, checks build identity, confirms 93 cases and 230 articles, and confirms the remembered configuration is visible without exposing plaintext.
- Release packages are rebuilt, checked for seed data and absence of API configuration, pushed to GitHub, and published under a new version tag.

## Safety

No real API request is needed for verification. The existing key is read only by the local application and is never printed, copied into the repository, release package, test fixture, log, or response payload. Backups remain local and are not committed.
