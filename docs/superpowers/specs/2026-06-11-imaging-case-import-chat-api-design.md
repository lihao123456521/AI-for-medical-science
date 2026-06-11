# Imaging Case Import, Chat Routing, and API Reliability Design

## Goal

Import the 17 named cases in `影像片子汇总.pdf` as independent, ordered cases while preserving the existing 76 user cases and 230 articles. Improve future multi-case document splitting, case image handling, chat retrieval routing, and third-party LLM timeout behavior.

## Data Safety

- Treat `~/.uscc_scc_flask_data` as the runtime source of truth.
- Create timestamped backups of `user_cases.json`, `articles.json`, `library_state.json`, and related manifests before migration.
- Import additively. Existing cases and articles must not be rewritten or deleted.
- Make the PDF import idempotent through a stable source-document and source-case signature.
- Keep the source PDF and extracted case images in persistent storage so links survive application updates.

## PDF Case Segmentation

The document contains 17 named cases numbered `1-10` and `12-18`; number 11 is absent in the source.

Segmentation uses explicit case-start anchors such as `序号 + 姓名`, not page boundaries. A case continues across pages until the next case-start anchor. Report item numbering inside a case must not create a new case.

Each imported case stores:

- source document name and hash;
- original case number and sortable numeric order;
- patient name, report dates, modalities, and imaging identifiers when present;
- complete report text and conclusions;
- page range;
- extracted images assigned to the case page range;
- physician-provided labels and annotations visible in the PDF;
- a note that these findings came from supplied annotated material and require clinical verification.

The missing source number 11 is recorded in import metadata, but no blank case is created.

## Case Data Model and Ordering

Keep the existing `USER-*` identifier system for compatibility. Add optional source metadata fields to saved user-case JSON, including `source_case_number`, `source_document`, `source_pages`, `source_hash`, and structured `imaging_findings`.

Knowledge-base listing uses `source_case_number` as the primary order for cases from the same imported document, with the existing case identifier as fallback. Other cases retain their current stable ordering.

`medical_images` entries gain optional fields for source page, modality, physician annotation, and image findings. Existing image entries remain valid.

## Future Document Splitting

Add a reusable multi-case text segmenter for PDF, DOCX, TXT, and MD inputs. It scores possible boundaries using:

1. explicit case numbers followed by patient/name markers;
2. demographic or identifier anchors;
3. numbering continuity and reset patterns;
4. page continuity;
5. safeguards against confusing report subsection numbers with case numbers.

The parser returns one candidate per segment. When confidence is low, candidates remain for doctor confirmation rather than being silently merged or saved.

## Image Processing

PDF embedded images are extracted without recompression when possible and linked to the correct case segment. The software preserves supplied annotations as authoritative user notes, while model-generated descriptions are stored separately with provider/model/time provenance.

Future uploaded case images can be analyzed through a configured multimodal provider. The prompt asks for descriptive observations, visible annotations, modality/body region, and uncertainty. It must not claim a diagnosis. Image-analysis failure must not prevent saving the case or original image.

## Chat Retrieval Routing

Separate conversation state into:

- general conversation;
- unconfirmed case material;
- confirmed active case;
- explicit evidence-retrieval request.

Similar cases and articles are retrieved only when:

- a detailed case has just been confirmed and the initial analysis is requested; or
- the doctor explicitly asks to search, compare, cite, or discuss similar cases/literature.

Terms such as `手术`, `用药`, `复发`, or `下一步` alone do not force retrieval. If an active case exists, case-related follow-ups receive that case context without automatically displaying retrieval cards. Unrelated questions are answered normally without forced case association.

The frontend must stop appending every general question to `patient.free_text`. Only recognized case details, parsed case files, selected candidates, or an explicit case-update action modify the active case.

## LLM Request Reliability

Introduce one provider-aware request policy shared by connection tests, chat, and image analysis:

- disable SDK automatic retries (`max_retries=0`);
- use explicit connect/read/write/pool timeouts instead of one short scalar timeout;
- lower normal answer output limits, with a slightly larger limit only for initial case analysis;
- use streaming for compatible OpenAI-style chat requests so the server receives output progressively;
- preserve native Anthropic handling with equivalent timeout and output limits;
- classify timeout, connection, authentication, quota, and bad-base-URL failures separately;
- never automatically issue a second paid generation after an ambiguous timeout;
- expose a request ID and clear message when the provider may have accepted a timed-out request.

The browser request timeout must be longer than the server read timeout and must support cancellation without triggering a duplicate request.

## Testing and Verification

- Unit tests for numbered case segmentation, page-spanning cases, missing number 11, and report subsection numbering.
- Migration tests proving 76 existing cases and 230 articles remain unchanged and 17 cases are added exactly once.
- Image-assignment tests for all 24 pages and extracted images.
- Chat-routing tests for initial analysis, case follow-up, explicit retrieval, and unrelated questions.
- LLM client tests verifying `max_retries=0`, output-token policy, streaming path, timeout classification, and no automatic second generation.
- End-to-end storage checks, knowledge-base ordering checks, and application test suite execution.

## Scope Boundaries

This change improves ingestion, descriptive image handling, retrieval routing, and request reliability. It does not create an autonomous diagnostic system, infer missing diagnoses, or replace clinician review.
