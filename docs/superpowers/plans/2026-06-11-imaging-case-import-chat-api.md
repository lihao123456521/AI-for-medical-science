# Imaging Case Import, Chat Routing, and API Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use $superpower-subagents (recommended) or $superpower-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking via update_plan.

**Goal:** Import 17 numbered imaging cases without changing the existing 76 cases or 230 articles, then make future multi-case parsing, chat retrieval routing, image handling, and provider requests reliable.

**Architecture:** Add a focused PDF case-segmentation/import module that processes layout events in reading order so mixed pages assign images correctly. Extend the existing case record with backward-compatible source metadata, isolate chat intent classification from accumulated case text, and centralize provider timeout/token/retry/stream policy in the LLM client.

**Tech Stack:** Python 3.10+, Flask, PyMuPDF, pypdf, OpenAI Python SDK, vanilla JavaScript, `unittest`.

---

## File Map

- Create `core/case_document.py`: numbered multi-case segmentation and PDF layout/image extraction.
- Create `scripts/import_imaging_pdf_cases.py`: backup, idempotent 17-case migration, image copying, manifest writing.
- Create `tests/test_case_document.py`: boundary and image ownership tests.
- Create `tests/test_imaging_import.py`: additive/idempotent migration tests against temporary storage.
- Create `tests/test_chat_routing.py`: retrieval and active-case routing tests.
- Create `tests/test_llm_policy.py`: retry, timeout, token, streaming, and error classification tests.
- Modify `core/data_loader.py`: optional case source metadata and structured imaging findings.
- Modify `app.py`: metadata persistence, stable imported-case ordering, reusable routing helpers.
- Modify `core/case_parser.py`: return multiple numbered candidates for text-oriented case documents.
- Modify `core/llm_client.py`: provider request policy and streamed compatible requests.
- Modify `static/js/app.js`: explicit active-case state, no automatic question-to-case merging, cancellable request timeout.
- Modify `templates/case_detail.html`: show source number/pages and structured image annotations.
- Modify `requirements.txt`: declare `httpx` explicitly because request timeout objects are used directly.

### Task 1: Numbered Case Segmentation and PDF Layout Ownership

**Files:**
- Create: `core/case_document.py`
- Create: `tests/test_case_document.py`

- [ ] **Step 1: Write failing segmentation tests**

```python
import unittest
from core.case_document import segment_numbered_cases, assign_layout_events


class NumberedCaseSegmentationTests(unittest.TestCase):
    def test_missing_number_and_report_subsections_do_not_split_cases(self):
        text = """1.姓名：甲\nCT报告：\n1.膀胱壁增厚\n2.淋巴结肿大\n2.姓名：乙\nMRI报告\n1.尿道肿块\n12.姓名：丙\nCT报告"""
        rows = segment_numbered_cases(text)
        self.assertEqual([r.source_case_number for r in rows], [1, 2, 12])
        self.assertIn("2.淋巴结肿大", rows[0].text)

    def test_image_before_new_name_stays_with_previous_case(self):
        events = [
            {"kind": "text", "page": 3, "y": 20, "text": "病例1续页"},
            {"kind": "image", "page": 3, "y": 100, "xref": 11},
            {"kind": "text", "page": 3, "y": 500, "text": "2.姓名：乙"},
            {"kind": "image", "page": 3, "y": 700, "xref": 12},
        ]
        owned = assign_layout_events(events, starting_case_number=1)
        self.assertEqual(owned[1]["images"][0]["xref"], 11)
        self.assertEqual(owned[2]["images"][0]["xref"], 12)
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m unittest tests.test_case_document -v`

Expected: import failure because `core.case_document` does not exist.

- [ ] **Step 3: Implement the minimal segmenter and layout event assignment**

```python
CASE_START_RE = re.compile(
    r"(?m)^\s*(?P<number>\d{1,3})\s*[\.、:：]\s*(?:姓名|患者姓名)\s*[：:]\s*(?P<name>[^\n]+?)\s*$"
)

@dataclass
class CaseSegment:
    source_case_number: int
    patient_name: str
    text: str
    pages: list[int] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)

def segment_numbered_cases(text: str) -> list[CaseSegment]:
    matches = list(CASE_START_RE.finditer(text or ""))
    return [
        CaseSegment(
            source_case_number=int(match.group("number")),
            patient_name=match.group("name").strip(),
            text=(text[match.start(): matches[index + 1].start()] if index + 1 < len(matches) else text[match.start():]).strip(),
        )
        for index, match in enumerate(matches)
    ]

def assign_layout_events(events: list[dict[str, Any]], starting_case_number: int | None = None) -> dict[int, dict[str, Any]]:
    current = starting_case_number
    owned: dict[int, dict[str, Any]] = {}
    for event in sorted(events, key=lambda row: (row["page"], row["y"], 0 if row["kind"] == "text" else 1)):
        if event["kind"] == "text":
            match = CASE_START_RE.search(event.get("text", ""))
            if match:
                current = int(match.group("number"))
        if current is None:
            continue
        bucket = owned.setdefault(current, {"texts": [], "images": [], "pages": []})
        bucket["pages"].append(event["page"])
        bucket["texts" if event["kind"] == "text" else "images"].append(event)
    return owned
```

Add `extract_pdf_case_segments(path)` using `fitz.Page.get_text("dict")`, emitting text and image events with page number and top `y`. Extract image bytes by xref and derive each image's nearby physician annotation from the closest numbered text block in the same owned case.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m unittest tests.test_case_document -v`

Expected: all segmentation and mixed-page ownership tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add core/case_document.py tests/test_case_document.py
git commit -m "Add numbered medical case document segmentation"
```

### Task 2: Backward-Compatible Case Metadata and Ordering

**Files:**
- Modify: `core/data_loader.py:84-145`
- Modify: `app.py:69-122,1317-1380,1477-1507,1609-1621`
- Modify: `templates/case_detail.html:14-53`
- Create: `tests/test_case_metadata.py`

- [ ] **Step 1: Write failing metadata round-trip and ordering tests**

```python
import unittest
from core.data_loader import CaseRecord


class CaseMetadataTests(unittest.TestCase):
    def test_source_metadata_is_public_and_searchable(self):
        rec = CaseRecord(
            case_id="USER-077", sheet="影像片子汇总", diagnosis="影像资料病例",
            sex="", age=None, history="", prior_operation="", symptoms="", tumor="",
            grade="", tnm="", lymph_node="", ls="", immuno="", imaging="尿道肿块",
            pathology="", surgery="", other_treatment="", recurrence="", followup="",
            remarks="", source_row=0, patient_name="甲", source_case_number=12,
            source_document="影像片子汇总.pdf", source_pages=[13, 14],
            source_hash="abc", imaging_findings=[{"text": "双侧腹股沟淋巴结"}],
        )
        public = rec.as_public_dict()
        self.assertEqual(public["source_case_number"], 12)
        self.assertIn("甲", rec.searchable_text)
        self.assertIn("双侧腹股沟淋巴结", rec.searchable_text)
```

Also test `_case_sort_key` with source numbers `[1, 2, 10, 12, 18]` and ordinary `USER-*` records.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m unittest tests.test_case_metadata -v`

Expected: `CaseRecord` rejects the new keyword arguments.

- [ ] **Step 3: Extend the record and persistence path**

Add these defaults after `medical_images`:

```python
patient_name: str = ""
source_case_number: int | None = None
source_document: str = ""
source_pages: List[int] = field(default_factory=list)
source_hash: str = ""
source_import_key: str = ""
imaging_findings: List[Dict[str, Any]] = field(default_factory=list)
```

Include them in `as_public_dict`, `searchable_text`, `_record_to_saved_dict`, `_load_user_cases`, and `_add_case_from_fields`. Preserve unknown old records by using empty defaults.

Add:

```python
def _case_sort_key(rec: CaseRecord) -> tuple:
    source_document = str(getattr(rec, "source_document", "") or "")
    source_number = getattr(rec, "source_case_number", None)
    if source_document and isinstance(source_number, int):
        return (0, source_document, source_number, rec.case_id)
    return (1, "", 10**9, rec.case_id)
```

Sort only the `/api/cases` response copy, leaving `kb.records` ownership unchanged.

Show source number, source pages, source document, structured findings, and image annotation in the detail template.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m unittest tests.test_case_metadata -v`

Expected: metadata round-trip and ordering tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add core/data_loader.py app.py templates/case_detail.html tests/test_case_metadata.py
git commit -m "Preserve imported case source and imaging metadata"
```

### Task 3: Additive and Idempotent Import of the 17 Imaging Cases

**Files:**
- Create: `scripts/import_imaging_pdf_cases.py`
- Create: `tests/test_imaging_import.py`
- Modify: `core/case_parser.py:259-290`
- Modify: `app.py:1228-1262`

- [ ] **Step 1: Write failing importer tests**

```python
class ImagingImportTests(unittest.TestCase):
    def test_import_adds_17_once_and_preserves_articles(self):
        result = import_segments(self.data_dir, self.segments, source_hash="pdfhash")
        self.assertEqual(result["before_case_count"], 76)
        self.assertEqual(result["after_case_count"], 93)
        self.assertEqual(result["article_count"], 230)
        second = import_segments(self.data_dir, self.segments, source_hash="pdfhash")
        self.assertEqual(second["added"], 0)
        self.assertEqual(second["after_case_count"], 93)

    def test_original_numbers_are_1_to_10_and_12_to_18(self):
        self.assertEqual(
            [row["source_case_number"] for row in self.imported],
            [1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18],
        )
```

Use temporary JSON files containing 76 placeholder cases and 230 placeholder articles. Include an image event before and after a same-page case anchor.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m unittest tests.test_imaging_import -v`

Expected: importer module is missing.

- [ ] **Step 3: Implement backup and import functions**

The script exposes:

```python
def create_storage_backup(data_dir: Path, timestamp: str | None = None) -> Path: ...
def build_case_rows(pdf_path: Path, upload_dir: Path) -> list[dict[str, Any]]: ...
def import_segments(data_dir: Path, case_rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]: ...
def import_pdf(pdf_path: Path, data_dir: Path) -> dict[str, Any]: ...
```

`create_storage_backup` copies the JSON source-of-truth files into `backups/<timestamp>-imaging-import/` before any write. `build_case_rows` saves the source PDF and images under `uploads/imaging-summary-<hash>/`, assigns `USER-*` IDs after the current maximum, and stores the full report text in `imaging` plus structured numbered findings in `imaging_findings`.

Idempotency key:

```python
source_key = f"{source_hash}:{source_case_number}"
```

Store it as `source_import_key` and skip any existing row with the same key. Write `user_cases.json` atomically, preserve `articles.json` byte content, update `library_state.json` and `storage_manifest.json`, and write `imaging_import_manifest.json` with missing number `[11]`.

Update `parse_pdf` and `_extract_case_batch_candidates` to return all numbered segments as candidates instead of one merged candidate.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m unittest tests.test_imaging_import tests.test_case_document -v`

Expected: additive, idempotent, numbering, image ownership, and backup tests pass.

- [ ] **Step 5: Run the real import and verify counts**

Run:

```powershell
python scripts/import_imaging_pdf_cases.py "C:\Users\ASUS\Desktop\影像片子汇总.pdf" --data-dir "$HOME\.uscc_scc_flask_data"
```

Expected summary: `before_cases=76`, `added=17`, `after_cases=93`, `articles=230`, source numbers `1-10,12-18`, missing `[11]`.

- [ ] **Step 6: Commit Task 3**

```powershell
git add scripts/import_imaging_pdf_cases.py core/case_parser.py app.py tests/test_imaging_import.py
git commit -m "Import numbered annotated imaging cases safely"
```

### Task 4: Explicit Chat Context and Retrieval Routing

**Files:**
- Modify: `app.py:2014-2025,2213-2264`
- Modify: `core/llm_client.py:13-27,88-146,337-445`
- Modify: `static/js/app.js:77-92,257-283,337-382,384-420`
- Create: `tests/test_chat_routing.py`

- [ ] **Step 1: Write failing routing tests**

```python
from app import classify_chat_request

class ChatRoutingTests(unittest.TestCase):
    def test_general_question_does_not_retrieve(self):
        route = classify_chat_request("Python如何读取PDF？", has_confirmed_case=True)
        self.assertFalse(route.retrieve_evidence)
        self.assertFalse(route.use_case_context)

    def test_case_followup_uses_case_without_cards(self):
        route = classify_chat_request("这个患者下一步需要补充哪些检查？", has_confirmed_case=True)
        self.assertTrue(route.use_case_context)
        self.assertFalse(route.retrieve_evidence)

    def test_explicit_similarity_request_retrieves(self):
        route = classify_chat_request("请检索并比较相似病例和文献", has_confirmed_case=True)
        self.assertTrue(route.retrieve_evidence)
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m unittest tests.test_chat_routing -v`

Expected: `classify_chat_request` is missing.

- [ ] **Step 3: Implement a narrow classifier and frontend state**

```python
@dataclass(frozen=True)
class ChatRoute:
    use_case_context: bool
    retrieve_evidence: bool
    mode: str

EXPLICIT_RETRIEVAL_PATTERNS = (
    "相似病例", "检索病例", "比较病例", "参考文献", "检索文献", "查指南", "证据依据"
)

def classify_chat_request(question: str, has_confirmed_case: bool, mode: str = "") -> ChatRoute:
    q = str(question or "").strip()
    if mode == "initial_patient_analysis" and has_confirmed_case:
        return ChatRoute(True, True, mode)
    retrieve = any(term in q for term in EXPLICIT_RETRIEVAL_PATTERNS)
    case_words = ("患者", "病例", "病灶", "影像", "病理", "分期", "该患者", "这个患者")
    use_case = has_confirmed_case and (retrieve or any(term in q for term in case_words))
    return ChatRoute(use_case, retrieve, "explicit_retrieval" if retrieve else "case_followup" if use_case else "general")
```

`/api/chat` accepts `has_confirmed_case`. It passes an empty patient object to the model for general mode, the active case for case-followup mode, and generates reports only for retrieval modes.

Frontend chat records gain `caseConfirmed: false`. Candidate selection and parsed detailed case confirmation set it to `true`. Remove `mergePatientFromText(text)` from ordinary sends. Add a conservative `extractCaseUpdateFromText` only for explicit prefixes such as `补充病例：` and `更新病例：`.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m unittest tests.test_chat_routing -v`

Expected: all four routing modes pass.

- [ ] **Step 5: Commit Task 4**

```powershell
git add app.py core/llm_client.py static/js/app.js tests/test_chat_routing.py
git commit -m "Gate case retrieval behind confirmed context and explicit intent"
```

### Task 5: Provider-Aware Timeout, Token, Retry, and Streaming Policy

**Files:**
- Modify: `core/llm_client.py:269-445`
- Modify: `static/js/app.js:272-283,354-382,638-668`
- Modify: `requirements.txt`
- Create: `tests/test_llm_policy.py`

- [ ] **Step 1: Write failing request-policy tests**

```python
from core.llm_client import build_request_policy, classify_provider_error

class LlmPolicyTests(unittest.TestCase):
    def test_normal_policy_disables_retries_and_limits_output(self):
        policy = build_request_policy("deepseek", "normal_followup")
        self.assertEqual(policy.max_retries, 0)
        self.assertEqual(policy.max_output_tokens, 600)
        self.assertGreaterEqual(policy.read_timeout, 75)
        self.assertTrue(policy.stream)

    def test_initial_analysis_allows_more_output_without_retry(self):
        policy = build_request_policy("openai", "initial_patient_analysis")
        self.assertEqual(policy.max_output_tokens, 900)
        self.assertEqual(policy.max_retries, 0)

    def test_timeout_message_warns_request_may_have_been_accepted(self):
        msg = classify_provider_error(TimeoutError("read timed out"), "deepseek", "req-1")
        self.assertIn("可能已经接收", msg)
        self.assertIn("req-1", msg)
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m unittest tests.test_llm_policy -v`

Expected: request-policy helpers are missing.

- [ ] **Step 3: Implement one shared policy**

```python
@dataclass(frozen=True)
class RequestPolicy:
    connect_timeout: float
    read_timeout: float
    write_timeout: float
    pool_timeout: float
    max_retries: int
    max_output_tokens: int
    stream: bool

def build_request_policy(provider: str, mode: str) -> RequestPolicy:
    return RequestPolicy(
        connect_timeout=10.0,
        read_timeout=90.0 if provider in {"deepseek", "openrouter", "fourrouter", "custom"} else 75.0,
        write_timeout=30.0,
        pool_timeout=10.0,
        max_retries=0,
        max_output_tokens=900 if mode == "initial_patient_analysis" else 600,
        stream=provider != "anthropic",
    )
```

Construct SDK clients with:

```python
OpenAI(
    api_key=api_key,
    base_url=base_url or None,
    timeout=httpx.Timeout(
        connect=policy.connect_timeout,
        read=policy.read_timeout,
        write=policy.write_timeout,
        pool=policy.pool_timeout,
    ),
    max_retries=policy.max_retries,
)
```

Use `stream=True` for compatible Chat Completions and collect deltas once. Use `client.responses.stream` for OpenAI Responses. Never catch a timeout and call generation again. Generate a UUID request ID before the call, return it in success/error payloads, and classify timeout/auth/quota/connection/base-URL errors.

Connection tests use 20-second read timeout and 24 output tokens. Chat uses 600/900 token limits. Browser `AbortController` timeout is 105 seconds and abort only cancels the current fetch; it does not resubmit.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m unittest tests.test_llm_policy -v`

Expected: retry, timeout, token, streaming, and error tests pass.

- [ ] **Step 5: Commit Task 5**

```powershell
git add core/llm_client.py static/js/app.js requirements.txt tests/test_llm_policy.py
git commit -m "Make provider requests bounded streamed and non-retrying"
```

### Task 6: Full Verification and Storage Evidence

**Files:**
- Modify: `README.md`
- Create: `docs/notes/README_V37_CHANGES.md`

- [ ] **Step 1: Run the full test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass with zero errors and zero failures.

- [ ] **Step 2: Verify live persistent counts and source ordering**

Run a read-only Python check that prints:

```text
user_cases=93
articles=230
imported_cases=17
source_numbers=1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18
missing_source_numbers=11
cases_with_images=17
```

Also verify every imported image path exists and every imported case has non-empty `imaging`, `source_pages`, and `imaging_findings`.

- [ ] **Step 3: Run application and endpoint smoke checks**

Run the Flask app with `USCC_DATA_DIR` pointing to a temporary copy, then check `/healthz`, `/api/summary`, `/api/cases?sheet=影像片子汇总`, and one imported `/api/case/<id>` response.

Expected: HTTP 200; summary reports 93 user-fed cases plus built-ins as applicable and 230 articles; imported cases are ordered by original source number.

- [ ] **Step 4: Review UI behavior manually**

Confirm:

- imported detail pages display report text, source pages, structured findings, and images;
- a general question does not show similar-case/article cards;
- a confirmed-case follow-up uses the active case without cards;
- an explicit similar-case request shows cards;
- browser cancellation displays one timeout message and does not create a second request.

- [ ] **Step 5: Document the release and commit**

```powershell
git add README.md docs/notes/README_V37_CHANGES.md
git commit -m "Document annotated imaging import and request reliability"
```

## Verification

- `python -m unittest discover -s tests -v`
- `git diff --check`
- Persistent JSON count and image-path audit
- Flask endpoint smoke tests
- Browser chat-routing and cancellation checks

## Next Skill

`$superpower-executing-plans` for inline execution in this session.
