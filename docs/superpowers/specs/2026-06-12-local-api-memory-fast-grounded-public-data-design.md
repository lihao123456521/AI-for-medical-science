# Local API Memory, Fast Grounded Answers, and Public Seed Data

## Goal

Make saved API configurations reusable without re-entering a key, reduce perceived and actual response latency, ground medical answers in the bundled case and article library, and publish a de-identified default database to the public GitHub repository without publishing any API credentials.

## Current Findings

- The Flask backend already stores successful API configurations in the local runtime directory, including the full key, while its read endpoint returns only a masked key.
- The browser treats an empty key field as an instruction to use its own local storage. After selecting a backend-saved configuration, stale or empty browser values can override the intended active backend configuration. This is why the UI can ask for the key again even though the backend remembers it.
- Uncommitted work already introduces server-sent event streaming and shorter output limits. This work will be preserved, tested, and completed rather than replaced.
- Runtime storage contains 93 cases, 230 articles, 73 extracted case images, and local API configuration files. The repository's packaged JSON files are currently empty and ignored by Git.
- The target GitHub repository is public. Runtime cases and uploads can contain identifying text and therefore cannot be copied directly.

## API Configuration Memory

Successful configurations remain stored only under the local runtime data directory. The backend is the authority for the active configuration and its secret key. Browser storage keeps only non-secret UI preferences such as provider, model, base URL, and active configuration ID.

Selecting a remembered configuration activates it on the backend and updates the browser's non-secret metadata. Chat requests omit `api_key` when a remembered backend configuration is active, allowing the backend to use its saved key. The API modal displays a masked key and a clear status that the saved key is active; it does not require the user to type the key again unless replacing it.

Clearing API settings removes both the active backend configuration and saved history, plus any legacy browser-stored plaintext key. Repository and release checks reject API configuration files and common key patterns.

## Response Speed and Timeout Handling

The chat endpoint streams text chunks to the browser as soon as the provider returns them. The UI replaces the waiting indicator with partial output immediately and retains the partial answer if a later stream error occurs.

Requests use provider-aware connection and first-byte/read timeouts, bounded output tokens, eight recent conversation messages, and no automatic SDK retries. General questions use a smaller output budget than initial case analysis. Expensive database work is limited to the evidence needed for the current route.

On provider timeout, the stream reports a request ID and retains any received text. If no text was received, the application returns a concise local knowledge-base answer. The software cannot guarantee cancellation after a remote provider accepts a request, so it warns users not to resend immediately and never performs an automatic retry.

## Database-Grounded Answer Routing

Routing distinguishes four behaviors:

1. Detailed initial case analysis: use case context, retrieve similar cases and related articles, and display evidence cards.
2. Explicit case or evidence request: use the confirmed case, retrieve cases and articles, and display evidence cards.
3. Case follow-up: use the confirmed case and a compact evidence digest without repeatedly displaying cards.
4. General medical question: search relevant articles and compact knowledge summaries, but do not force patient context or similar-case cards. Questions unrelated to medicine use no database context.

The model receives compact evidence excerpts with stable case/article identifiers rather than the entire database. The answer instructions require distinguishing database evidence from general model knowledge and avoiding unsupported claims.

## Public Seed Database

Create versioned seed files inside the repository containing 93 de-identified cases and 230 articles. Seed generation removes or replaces:

- patient names, hospital numbers, record numbers, contact details, addresses, and exact identity-bearing dates;
- source file names or notes that expose a person's identity;
- local absolute paths, runtime IDs that reveal local history, and API configuration values;
- images that contain readable identifying text or cannot be reliably verified as de-identified.

Medical findings, diagnoses, treatments, outcomes, article metadata, abstracts, and content remain where they do not identify a person. Published case IDs are deterministic seed IDs, independent of local runtime IDs.

On a fresh installation, the app initializes the local runtime database from the seed files. Existing installations are never overwritten. Subsequent user-added cases and articles continue to live only in the local runtime directory.

## Data Safety and Publishing

Before committing, an automated audit checks seed JSON and tracked files for forbidden identity fields, Windows user paths, API configuration filenames, and likely API key patterns. The audit also verifies exact counts of 93 cases and 230 articles and confirms that no seed record contains a plaintext patient name field.

`api_config.json`, API history, `.env`, runtime uploads, backups, manifests containing local paths, and browser secrets remain excluded. Only de-identified seed assets that pass the audit are staged.

## Testing

- Backend tests verify saved configurations can be activated and used without a request key, while API responses never expose plaintext keys.
- Frontend behavior is covered through extracted pure helpers or static assertions for remembered-configuration payload behavior and stream parsing.
- Routing tests cover case analysis, explicit retrieval, follow-up, general medical questions, and unrelated questions.
- Streaming tests verify early chunks, partial-answer retention, timeout fallback, and no retry.
- Seed-data tests verify counts, deterministic IDs, de-identification, initialization behavior, and absence of credentials.
- The full Python test suite, Python compilation, JavaScript syntax check, Flask smoke tests, Git diff checks, and secret scan run before publication.

## Delivery

Preserve and incorporate the current uncommitted streaming work after reviewing it against this design. Commit implementation and seed data intentionally, push the resulting branch, and synchronize it to the public GitHub repository only after all privacy and credential checks pass.
