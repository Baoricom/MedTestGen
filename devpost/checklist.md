---
doc: checklist
status: approved
---

# MedTestGen Build Checklist

Build mode: fast — explicitly approved. Stages 1–2 accepted. Continue stages 3–4; stop for final learner review after the completed local end-to-end demonstration.

Scope, PRD, specification and mappings are approved. Stage 4-spec is complete. No application implementation is claimed by this checklist.

## Slices

- [x] **1. Generate and independently check a synthetic CT study**
  Becomes usable: A runnable synthetic CT generation and validation probe produces 1–10 instances in RAM and shows real per-instance findings without exporting unchecked data.
  Why now: CT correctness and Windows validator lifecycle are the largest approved technical risks; this slice leaves runnable evidence before integrating the other standards. Bootstrap is included here.
  PRD ref: `prd.md > Imaging Study and CT Output`, `prd.md > Validation Reporting`
  Spec ref: `spec.md > Stack`, `spec.md > Canonical Scenario Builder`, `spec.md > CT DICOM Generator`, `spec.md > External CT IOD Validator Adapter — Approved Method A`
  Build: Create the package and pinned environment; verify FHIR/dependency imports early; implement the canonical CT scenario, phantom generation, readback and method A adapter with bounded child lifecycle and owned cleanup. Add a synthetic RAM-only diagnostic entry point and tests. No alternative file transport.
  Verify (mechanical): Run pip check and version/import smoke checks; pytest tests/test_ct.py tests/test_validator.py; exercise N=1..10, real positive and negative validator cases, warnings, exit-zero errors, unknown output, unavailable tool, timeout, all-instance aggregation and cleanup including parent death with a live child. Record untested environments honestly. Fix failures before progressing.
  Learner check: Run the documented diagnostic command and inspect a five-slice study's UIDs and per-instance validation report; confirm the CT output profile matches the intended test use.
  Commit: `Implement synthetic CT generation and qualified Windows validation`

- [x] **2. Generate one linked DICOM, HL7 and FHIR dataset**
  Becomes usable: A single scenario produces the three standard-specific outputs with readable diagnostic summaries and independent consistency results.
  Why now: Proves One Patient, Three Standards early, immediately after the CT risk is qualified.
  PRD ref: `prd.md > Linked HL7 and FHIR Outputs`, `prd.md > Validation Reporting`
  Spec ref: `spec.md > HL7 Order Generator`, `spec.md > FHIR Bundle Generator`, `spec.md > Mandatory Validation and Consistency`, `spec.md > Data Model`
  Build: Implement grouped ORM v2.5.1, R4 collection Bundle, serialized-output validation and the approved mappings. Extend the runnable diagnostic entry point to display all three outputs without adding production export bypasses.
  Verify (mechanical): Run pytest tests/test_hl7_fhir.py tests/test_consistency.py and the CT/validator regression suite; verify R4 version, references, UID sets, counts, Unicode, escaping, unknown sex and deliberately mismatched identifiers/order fields.
  Learner check: Inspect one scenario's DICOM metadata, ORM PID/ORC/OBR and FHIR identifiers/references; confirm the documented local mapping represents the intended test order.
  Commit: `Generate linked ORM and FHIR R4 with consistency checks`

- [x] **3. Retrieve and export only eligible datasets through the API**
  Becomes usable: The local API generates, retains, restores and exports a complete validated ZIP while preserving a previous valid result on failed replacement.
  Why now: Applies the established validation results to the most consequential behavior: backend-controlled export and safe replacement.
  PRD ref: `prd.md > ZIP Export and Enforcement`, `prd.md > Atomic Replacement and Diagnostic Candidates`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > In-Memory Store and Atomic Replacement`, `spec.md > Results and ZIP Export`, `spec.md > Internal HTTP API`
  Build: Implement one-process RAM store, session ownership/revisions, TTL/tombstones, capacity reservation, complete generation pipeline, manifest/ZIP and the single export predicate. Add safe API errors, bounded admission and cleanup lifecycle.
  Verify (mechanical): Run pytest tests/test_store.py tests/test_api_export.py and prior suites. Test each export gate with direct API requests, known expiry/restart, lost response/revision conflict, incomplete ZIP, failed candidate preservation and expiration mid-generation. Measure peak memory and verify configured limits and reservation release with ten-slice requests.
  Learner check: Use the documented API demonstration to inspect a valid ZIP and an explicitly denied failed candidate; confirm previous valid data remains available until its original expiry.
  Commit: `Enforce RAM retention atomic replacement and validated ZIP export`

- [x] **4. Complete the browser generator and diagnostic workflow**
  Becomes usable: The approved prefilled web interface generates a dataset, previews DICOM/HL7/FHIR, explains validation results and downloads the gated ZIP.
  Why now: Connects the proven core and backend policy to the complete user journey without hiding missing functionality behind UI.
  PRD ref: `prd.md > The Core Journey`, `prd.md > Dataset Generator`, `prd.md > Result Panel`, `prd.md > Output Inspection`, `prd.md > Look and Feel`
  Spec ref: `spec.md > Dataset Generator UI`, `spec.md > Results and ZIP Export`, `spec.md > Where It Runs and How Someone Tries It`
  Build: Implement static responsive UI, synthetic defaults/randomization, input validation, generation progress, three tabs, actual check statuses, diagnostic/active switching, refresh reconciliation and ZIP action. Document PowerShell setup, validation coverage and platform/cleanup limitations. Include a simple phantom preview only within the approved optional preview scope.
  Verify (mechanical): Run the full pytest suite and start the server using the documented command. Exercise default and 1/10-slice journeys, invalid input, failed validation, unavailable validator, expiry, refresh and lost-response handling. Inspect desktop/mobile layouts, keyboard navigation and escaped diagnostic content; verify ZIP contents against displayed identifiers and manifest.
  Learner check: Open http://127.0.0.1:8000, generate and inspect a dataset, download ZIP, refresh and try awkward inputs; report anything broken or confusing.
  Commit: `Complete MedTestGen browser workflow and run documentation`

## Hands-on Checkpoints

- [x] Stage 2 review accepted by learner based on the 84-test report; learner authorized stages 3–4. No hands-on execution by the learner is claimed.
- [x] Final MVP review accepted by learner based on the 108-test and completed browser-workflow report. No hands-on execution by the learner is claimed.

## Final Review

- [x] Final review complete — on 2026-10-22 the learner approved the completed MVP and explicitly authorized `6-ship`; no additional fixes were requested.

## Code Tour and App Map

- [x] Learning activity complete — an evidence-based reference route traces Generate Dataset through the browser, API, canonical pipeline, atomic promotion and backend export policy using actual finished symbols.
- [x] Optional edit and transfer reflection addressed — no incidental product edit was needed during the final approved review; the reusable practice is captured in the map without claiming a personal reflection.
- [x] `devpost/app-map.html` generated from finished code and checked for the named paths, symbols, offline use and keyboard-readable structure.

Activity and evidence: Evidence-based recap after the learner's final MVP approval; the implementation and its 108-test verification report were already reviewed. No claim of learner hands-on execution is made.
Route and stops: `static/app.js > generate()` and `renderDataset()`; `pipeline.py > build_dataset()`; `store.py > finish()` and `download()` with `export.py > eligible()`.
Edit outcome: Not applicable; the approved scope and implementation required no incidental change.
Reflection: Not supplied. The map records a factual practice to reuse: express a safety requirement as a backend predicate and test the direct bypass path.
Activity mode: Concise reference route aligned with FAST mode and the request to proceed to shipping.

## Revisions

- hl7apy 1.3.5 treats ORM order-detail alternatives as simultaneously required. Narrow its reference choice to the approved OBR branch before validation; preserve group/field validation and add missing-OBR/procedure regressions. No stack, output or scope change.
- HTTP payload leases are released by a response wrapper in `finally`, including send failures. Independent review caught an obsolete `BackgroundTask` path before the Stage 3 commit; the corrected path has API and accounting regression coverage.
