# V37 Changes: Annotated Imaging Cases

## Data Import

- Imported 17 cases from `影像片子汇总.pdf` and kept their original source numbers: `1-10` and `12-18`.
- Preserved the existing 76 user cases and 230 articles. The resulting runtime library contains 93 user cases and 230 articles.
- Stored the source document hash, original case number, patient name, source pages, extracted images, image dimensions, and nearby physician annotations.
- Extracted 73 image placements across 16 cases. Original case 3 contains report text but no embedded image in the source PDF.
- The import is idempotent: rerunning it does not duplicate cases. It creates a backup before modifying runtime data.

## Document Splitting

- Numbered case headings are recognized by both Arabic sequence numbers and patient-name markers.
- Case boundaries use document layout positions, so text and images on a shared PDF page remain assigned to the correct case.
- Missing source number 11 is retained as a gap instead of causing later cases to be renumbered.

## Chat Behavior

- Similar-case and article retrieval no longer triggers from broad words such as treatment or surgery alone.
- Initial retrieval requires a sufficiently detailed, confirmed case.
- Follow-up questions about the confirmed case keep its context without repeatedly adding retrieval cards.
- Unrelated questions are answered normally without forcing patient context into the response.

## API Reliability

- Connection tests use a small output limit and a short bounded timeout.
- Normal calls use lower output limits, longer provider-aware read timeouts, and streaming where the provider supports it.
- SDK automatic retries are disabled to reduce duplicate requests and duplicate billing after a timeout.
- Each API request receives a local request ID. Timeout messages warn that the provider may already have accepted the request and advise checking provider records before resending.

These controls reduce accidental duplicate charges, but they cannot cancel a request that a remote provider has already accepted or guarantee that every provider exposes billing records in the same way.
