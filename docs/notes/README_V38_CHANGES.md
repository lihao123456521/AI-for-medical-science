# V38 Changes: Local API Memory and Ready-to-Use Database

## Remembered API Configurations

- Successful API configurations are stored in the local runtime directory.
- Selecting a remembered configuration activates its saved key without requiring it to be typed again.
- The browser stores only the configuration ID and non-secret display settings.
- Clearing API settings removes both the active configuration and local history.
- API keys are excluded from Git, seed data, and downloadable packages.

## Faster Responses

- Answers stream into the chat window as providers generate them.
- General answers use a smaller output budget; initial case analysis remains larger but bounded.
- Provider-aware timeouts and zero automatic retries reduce long waits and duplicate billing risk.
- Partial output remains visible if a provider times out later in the response.

## Database-Grounded Answers

- Initial case analysis and explicit evidence requests retrieve similar cases and related articles.
- Case follow-up questions retain case context without repeatedly displaying evidence cards.
- General medical questions use relevant article excerpts and the local knowledge digest without forcing patient context.
- Unrelated questions do not receive artificial case or article context.

## Public Seed Library

- The repository and release packages include 93 de-identified cases and 230 articles.
- Fresh installations initialize their local library automatically from `data/seed`.
- Existing local data is never overwritten by the seed library.
- Patient names, identity numbers, exact clinical dates, local paths, API keys, and image files are not published.
- The generation script fails if record counts or privacy checks do not pass.
