# Clean Windows Acceptance Checklist

Use a fresh Windows 11 x64 VM or Windows Sandbox without Python, Node.js, Git, or a previous UroPUC installation. Record the OS build, installer SHA-256, screenshots, and pass/fail result for every item.

## Install and launch

- Download `UroPUC-Setup-<version>.exe` only from the official GitHub Release.
- Verify the published SHA-256. Confirm the expected "Unknown publisher" warning while the installer remains unsigned.
- Install as a standard user. Confirm desktop and Start menu shortcuts are created.
- Launch from each shortcut; confirm the app becomes usable without Python, Node.js, PowerShell, or a network dependency install.
- Confirm the main window loads, `/healthz` is healthy, and no developer path or terminal window is visible.

## Core flows and isolation

- Create patient A, start a new chat, then create patient B. Confirm history, selected candidate, attachments, and generated text never cross between chats.
- Switch chats while an answer is streaming. Confirm the partial/final answer remains in the originating chat.
- Interrupt the network during streaming. Confirm partial text remains and the app does not automatically repeat a paid request.
- Select a candidate, force the initial brief to fail, and retry. Confirm the second attempt runs.
- Upload a valid case document and image. Confirm empty, damaged, oversized, and unsupported files show clear errors and leave no attachment.
- Edit a workbook-backed case label, export a backup, and confirm `case_label_overrides.json` is present in the ZIP.

## Persistence and upgrade

- Add a case, article, label, upload, API configuration, and chat; close the app and reopen it. Confirm all supported local data remains.
- Install the next version over the current version. Confirm runtime data under `%USERPROFILE%\.uscc_scc_flask_data` is not overwritten.
- Export data before uninstalling. Uninstall and confirm the application files/shortcuts are removed; separately document whether user data is retained.

## Security and process cleanup

- Confirm camera, microphone, geolocation, notifications, and other Electron permission prompts are denied.
- Confirm HTTP, credential-bearing, and malformed external links do not open; confirm a normal HTTPS documentation link does open in the default browser.
- Inspect installed resources for `.env`, API configuration/history, uploads, deleted cases, label overrides, or other private runtime data.
- Close the app normally and confirm no `UroPUC.exe` or `UroPUCBackend.exe` process remains.

Do not publish the release as clean-Windows-verified until every item above has recorded evidence.
