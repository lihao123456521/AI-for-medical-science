# Desktop Runtime, API Memory, and Token Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use $superpower-subagents (recommended) or $superpower-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking via update_plan.

**Goal:** Upgrade the actual desktop installation, make remembered APIs survive restarts and failed tests, and prevent token-heavy or repeated requests from producing unsafe 429 behavior.

**Architecture:** Keep the Git repository as source and deploy a filtered copy into the existing D-drive desktop installation after backups. Add build identity to prevent the launcher attaching to stale services. Keep API secrets in the existing local runtime store, and centralize request budgeting plus provider-error sanitization in `core/llm_client.py`.

**Tech Stack:** Python, Flask, Waitress, OpenAI-compatible streaming, JavaScript Fetch/SSE, PowerShell, Windows shortcuts, unittest.

---

### Task 1: Lock Desktop And Error Behavior With Failing Tests

**Files:**
- Create: `tests/test_launcher_contract.py`
- Modify: `tests/test_llm_policy.py`
- Modify: `tests/test_frontend_contract.py`

- [ ] Add a launcher contract test requiring a build identifier health check and stale-service rejection marker.
- [ ] Add a 429 test with the observed provider error; assert the reset time remains and the API-key hash is absent.
- [ ] Add frontend tests requiring an in-flight send guard and prohibiting automatic local fallback after an API error.
- [ ] Run the three test modules and confirm each new assertion fails for the expected missing behavior.

### Task 2: Add Build Identity And Stale-Service Protection

**Files:**
- Modify: `app.py`
- Modify: `windows_launcher.pyw`
- Test: `tests/test_launcher_contract.py`

- [ ] Add `APP_BUILD_ID` and return it from `/healthz` as JSON.
- [ ] Make launcher health checks parse the build ID rather than accepting any HTTP 200 on port 5000.
- [ ] If a port hosts a different build, choose a free port and launch the current installation instead of opening the stale service.
- [ ] Run launcher contract and health endpoint tests until green.

### Task 3: Sanitize 429 Errors And Stop Disguised Fallbacks

**Files:**
- Modify: `core/llm_client.py`
- Modify: `app.py`
- Modify: `static/js/app.js`
- Test: `tests/test_llm_policy.py`
- Test: `tests/test_llm_streaming.py`
- Test: `tests/test_frontend_contract.py`

- [ ] Add a provider-message sanitizer that removes `api_key:` values, key hashes, and redundant payload formatting.
- [ ] Classify HTTP 429 token limits separately, preserving the UTC reset timestamp and request ID.
- [ ] Ensure streaming API exceptions emit an error event without appending a local generated answer.
- [ ] Add a single active-send guard in the frontend and keep the send button disabled until stream completion or failure.
- [ ] Run focused tests until green.

### Task 4: Enforce Prompt And Output Budgets

**Files:**
- Modify: `core/llm_client.py`
- Test: `tests/test_llm_policy.py`

- [ ] Keep `build_llm_context` as the only context construction path for streaming and non-streaming clients.
- [ ] Add a final serialized-size guard that progressively clips digest, article text, case text, history, and patient free text while retaining IDs and titles.
- [ ] Set normal output to at most 240 tokens and initial analysis to at most 400 tokens, with zero retries and streaming enabled.
- [ ] Add tests for worst-case Unicode context and verify the serialized context stays below 24,000 characters.

### Task 5: Build A Repeatable Desktop Deployment Script

**Files:**
- Create: `scripts/deploy_windows_desktop.ps1`
- Create: `tests/test_desktop_deploy_contract.py`
- Modify: `README.md`

- [ ] Add a contract test requiring source, install, backup, and runtime paths plus explicit secret exclusions.
- [ ] Implement timestamped backups for the D-drive install and local runtime directory.
- [ ] Stop only processes whose command line points into the target installation.
- [ ] Copy current source with exclusions for `.git`, `.env`, `dist`, build directories, runtime JSON, and uploads.
- [ ] Recreate the desktop shortcut to target the upgraded installation and preserve the runtime directory.
- [ ] Run the deployment contract test and a dry-run fixture test until green.

### Task 6: Deploy And Perform Real Desktop Smoke Tests

**Files:**
- Runtime target: `D:\uscc_scc_flask_fixed`
- Runtime data: `C:\Users\ASUS\.uscc_scc_flask_data`
- Shortcut: `C:\Users\ASUS\Desktop\AI罕见病助手.lnk`

- [ ] Record masked metadata and file hashes for the existing local API config without printing the key.
- [ ] Run the deployment script and capture backup paths.
- [ ] Launch the desktop shortcut and wait for the matching build health response.
- [ ] Verify 93 cases, 230 articles, remembered config present, plaintext absent, and old D-drive processes replaced.
- [ ] Close and relaunch once more, then repeat remembered-config checks to prove restart persistence.

### Task 7: Full Verification And GitHub Release

**Files:**
- Modify: `docs/notes/README_V38_CHANGES.md`
- Generated locally: `dist/*`

- [ ] Run all unittests, Python compilation, JavaScript syntax check, and `git diff --check`.
- [ ] Scan tracked files and packages for API config files, `.env`, and secret-like patterns.
- [ ] Build Windows, macOS, and Linux packages and smoke-test the extracted Windows package.
- [ ] Commit changes, push `main`, create a patch version tag, and wait for the GitHub release workflow to finish successfully.
- [ ] Verify the latest download URL resolves to the new tag.
