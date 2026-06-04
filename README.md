# AI for Medical Science

UroSCC-LS Risk AI is a Flask-based medical science prototype for case entry, local knowledge-base retrieval, risk-factor explanation, and assisted discussion around male urethral squamous cell carcinoma and lichen sclerosus related clinical evidence.

This project is intended for teaching, research discussion, and prototype demonstration. It is not a medical device and must not be used as a diagnosis, staging, treatment, or triage system.

## Download Now

| Windows | macOS | Linux |
| --- | --- | --- |
| **[Download Windows ZIP](dist/AI-for-medical-science-windows.zip)** | **[Download macOS TAR.GZ](dist/AI-for-medical-science-macos.tar.gz)** | **[Download Linux TAR.GZ](dist/AI-for-medical-science-linux.tar.gz)** |

Windows users: extract the ZIP and double-click `start_windows_local.bat`. The launcher opens the chat UI automatically and creates a desktop shortcut with the themed doctor-patient app icon.

## Promotional Video

<video src="docs/media/ai-rare-disease-treatment-promo.mp4" poster="docs/media/promo-poster.jpg" autoplay muted loop playsinline controls preload="auto" width="100%">
  <a href="docs/media/ai-rare-disease-treatment-promo.mp4">Play the promotional video</a>
</video>

If your browser blocks autoplay, open the short promotional demo here: [AI rare disease treatment video](docs/media/ai-rare-disease-treatment-promo.mp4).

## Download Packages

The packages are portable source-based installers. Users need Python 3.10 or newer; the package startup scripts create a virtual environment and install the required Python libraries.

| System | Download | How to start |
| --- | --- | --- |
| Windows | [AI-for-medical-science-windows.zip](dist/AI-for-medical-science-windows.zip) | Extract the zip, then double-click `start_windows_local.bat`; it opens an app-style window and creates a desktop shortcut automatically |
| macOS | [AI-for-medical-science-macos.tar.gz](dist/AI-for-medical-science-macos.tar.gz) | Extract, open Terminal in the folder, run `bash run_mac_linux.sh` |
| Linux | [AI-for-medical-science-linux.tar.gz](dist/AI-for-medical-science-linux.tar.gz) | Extract, open a terminal in the folder, run `bash run_mac_linux.sh` |

After startup, open:

```text
http://127.0.0.1:5000
```

## More Notes

Older version notes, release notes, deployment notes, and security notes are collected in [docs/notes](docs/notes/README.md) so the project root stays clean.

## What It Does

- Structured case entry for symptoms, imaging, pathology, immunohistochemistry, and clinical notes.
- Local knowledge-base search from `data/knowledge_base.xlsx`.
- Transparent risk-factor extraction and rule-based scoring.
- Similar-case retrieval and case discussion support.
- Optional OpenAI-compatible API integration for explanatory summaries.
- Upload parsing for Excel, CSV, Word, text, PDF, and image attachments.

## Quick Start From Source

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python app.py
```

Or double-click:

```text
start_windows_local.bat
```

On Windows, `windows_launcher.pyw` starts the local Flask service, waits until it is healthy, and then opens the chat UI in an Edge/Chrome app-style window.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python app.py
```

Or run:

```bash
bash run_mac_linux.sh
```

## Optional AI API Configuration

Copy `.env.example` to `.env`, then fill in your API key if you want AI-generated explanatory summaries.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
FLASK_SECRET_KEY=change-this-in-production
DATA_PATH=data/knowledge_base.xlsx
```

The app can still run with local rules and knowledge-base retrieval when no API key is configured.

## Repository Structure

```text
.
|-- app.py
|-- core/
|   |-- case_parser.py
|   |-- data_loader.py
|   |-- llm_client.py
|   `-- risk_engine.py
|-- data/
|   |-- knowledge_base.xlsx
|   `-- knowledge_base_manifest.json
|-- static/
|-- templates/
|-- scripts/
|-- docs/
|   |-- media/
|   `-- notes/
`-- dist/
```

## Security And Data Notes

- Do not upload identifiable patient information to public GitHub repositories.
- Do not commit `.env` or API keys.
- Treat uploaded case files, runtime logs, and generated local data as sensitive. By default, user-fed cases and articles are stored in the Windows user directory `~/.uscc_scc_flask_data`.
- Public demonstrations should use synthetic or fully de-identified cases only.
- Every output should be reviewed by qualified medical professionals before any real-world interpretation.

## Deployment

For a cloud demo, use the included `render.yaml` or deploy the Flask app behind Gunicorn/Nginx on a controlled server. Before public deployment, add authentication, audit logging, data retention controls, and a complete privacy review.

## Rebuild Download Packages

From the project root on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release_packages.ps1
```

Generated packages are written to `dist/`.
