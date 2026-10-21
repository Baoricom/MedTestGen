---
doc: prd
status: approved
---

# MedTestGen — Product Requirements

A web-based synthetic CT DICOM, HL7 v2.5.1, and FHIR R4 dataset generator for DICOM equipment testers and healthcare integration engineers.

Source: scope.md > The Unique Kernel; Who It's For; The POC Boundary.

This is an approved product plan, not a record of implemented functionality. The learner explicitly approved the complete PRD after finalizing the backend export rule and requested progression to 4-spec.

## The Core Journey

Source: scope.md > The Core Loop; What "Working" Looks Like.

1. Open Dataset Generator without registration or sign-in. The patient and study form is already populated with synthetic values.
2. Optionally edit the patient and study fields or select Randomize Patient. Fixed MVP fields stay fixed.
3. Select Generate Dataset. Show a generation progress indicator.
4. Create the requested 1–10 CT slices, one ORM^O01 message, and one FHIR R4 Bundle from the same patient and study scenario. The default request creates five slices.
5. Show generated outputs in the Result Panel with DICOM, HL7, and FHIR tabs and separate validation results.
6. Enable Download ZIP only when all mandatory checks are PASSED, external CT IOD validation is PASSED/WARNING/NOT VERIFIED, there are no confirmed CT IOD conformance failures, and generation of all mandatory files has succeeded. Preserve diagnostic access after validation failure.
7. Download the linked dataset and manifest, or inspect failures and use Generate Again.

## Screens and Layout

Source: scope.md > The Core Loop; Inspiration & Identity.

### Dataset Generator

The upper section contains the MedTestGen logo/name, the tagline "One Patient. Three Standards. Consistent Test Data.", and the description "Generate synthetic DICOM, HL7 and FHIR datasets for healthcare interoperability testing."

Below it, show Patient Information and Imaging Study, followed by a prominent Generate Dataset button. All fields start populated; editing is optional. The form must remain understandable without exposing excessive medical parameters.

### Result Panel

After generation, show three tabs: DICOM, HL7, and FHIR. Include the validation summary, individual check results and findings, and the Download ZIP action. A failed mandatory check or an external CT IOD conformance failure must not hide successfully generated outputs.

## Look and Feel

Source: scope.md > Inspiration & Identity.

- Modern, minimalist, professional SaaS appearance with a light theme.
- Responsive desktop and mobile layout.
- A prominent primary generation action and clear progress and error messaging.
- Red "Validation Failed", green "Required Checks Passed", and a separate gray "Not Verified" status where applicable. Text labels communicate the meaning as well as color.
- Display "Synthetic Data — Not for Clinical Use".
- Exact typography and decorative colors are not prescribed by the learner; routine styling choices may follow this direction in the technical plan.
- The UI copy supplied by the learner is in English.

## Features and Behavior

### Patient Information

Source: scope.md > The POC Boundary > P0: Web UI and ZIP Export.

| Field or action | Behavior |
| --- | --- |
| Patient Name | Automatically populated synthetic name; editable. |
| Patient ID / MRN | Automatically generated identifier; editable. |
| Date of Birth | Automatically populated synthetic date; editable. |
| Sex | Male, Female, Other, or Unknown. |
| Randomize Patient | Populate the patient fields with a new synthetic patient. |

Acceptance criteria:

- A user can generate the default dataset without typing patient details.
- User-provided edits are reflected consistently in the generated outputs wherever applicable.
- Randomize Patient provides a usable synthetic patient for the next generation.

### Imaging Study and CT Output

Source: scope.md > The POC Boundary > P0: CT DICOM Generation.

| Field | Initial value and editability |
| --- | --- |
| Modality | CT, fixed. |
| Study Description | CT Head, editable. |
| Accession Number | Automatically generated, editable. |
| Number of Slices | 5 by default; configurable from 1 to 10. |
| Image Resolution | 512 x 512, fixed. |
| SOP Class | CT Image Storage, fixed. |

Acceptance criteria:

- The default request creates five DICOM files; an accepted count N creates exactly N files for 1 <= N <= 10.
- Files use CT Image Storage SOP Class UID 1.2.840.10008.5.1.4.1.1.2, Modality CT, and Explicit VR Little Endian.
- Images are synthetic CT-phantom-like geometric patterns, 512 x 512, 16-bit grayscale, MONOCHROME2.
- Each slice has a unique SOP Instance UID. Study Instance UID, Series Instance UID, and Frame of Reference UID are shared across the slices of the generated study/series.
- Slice geometry is consistent. Required CT Image IOD attributes include Pixel Data, Rescale Slope/Intercept, Pixel Spacing, Slice Thickness, Image Position (Patient), and Image Orientation (Patient).
- The stated CT Image IOD requirements remain generation requirements even when independent conformance validation is unavailable. Do not substitute Secondary Capture.

### Linked HL7 and FHIR Outputs

Source: scope.md > The POC Boundary > P0: HL7 Order; P0: FHIR R4 Bundle; P0: Cross-Standard Consistency.

Acceptance criteria:

- Generate one HL7 v2.5.1 ORM^O01 CT order containing correct MSH, PID, PV1, ORC, and OBR segments.
- Generate one FHIR R4 Bundle containing Patient, ServiceRequest, and ImagingStudy with resolvable internal references.
- Patient ID/MRN and Accession Number agree across applicable output fields.
- FHIR ImagingStudy reflects the generated DICOM study, series, and individual instances, including the corresponding UIDs.
- FHIR ServiceRequest represents the same ordered study as ORM^O01.
- All three outputs derive from one canonical scenario. Document the chosen HL7/DICOM field mappings during technical planning.

### Output Inspection

Source: scope.md > The Core Loop; What "Working" Looks Like.

- DICOM: show the slice list, Study/Series/SOP Instance UIDs, and metadata. A synthetic image preview is desired if feasible; it is not a promise of a full diagnostic viewer.
- HL7: show the ORM^O01 text with readable formatting.
- FHIR: show formatted Bundle JSON.
- When mandatory validation or external CT IOD conformance validation fails, preserve successfully generated outputs in their tabs for diagnosis.
- Show known validation errors with the standard, field, and reason. Do not invent unavailable error details.

### Validation Reporting

Source: scope.md > What "Working" Looks Like; The POC Boundary > P0: Cross-Standard Consistency.

Display separate results for:

1. DICOM serialization/file structure and readback — mandatory.
2. CT Image IOD conformance validation — independent, additional check when an appropriate validator is available.
3. HL7 structural validation — mandatory.
4. FHIR R4 resource validation — mandatory.
5. Cross-standard identifier and reference consistency — mandatory.

| Status | Meaning |
| --- | --- |
| PASSED | The check actually ran and succeeded. |
| FAILED | A check detected an error. |
| NOT VERIFIED | The check was not performed or could not technically complete; no conformance conclusion is available. |
| WARNING | A noncritical finding was detected. |

Never label an unperformed check as Valid or PASSED. WARNING and NOT VERIFIED cannot substitute for the required PASSED outcome of a mandatory check. Noncritical findings must not be silently promoted to proof of success.

Acceptance criteria:

- If any mandatory check fails, show red "Validation Failed", keep diagnostic tabs available, show concrete findings, disable Download ZIP, and offer Generate Again.
- If all mandatory checks pass and external CT IOD validation is PASSED, WARNING, or NOT VERIFIED, show green "Required Checks Passed" while retaining the separate external status and its findings. This wording does not claim full CT Image IOD conformance. An external CT IOD FAILED result takes precedence and changes the overall status to Validation Failed.
- If the independent CT IOD validator is unavailable, not installed, or cannot technically complete its check, show gray "Not Verified", explain the limitation, and display "Full DICOM CT IOD conformance has not been independently verified." A validator execution failure is not a detected CT IOD violation.
- In that unavailable-validator case, allow ZIP if all mandatory checks have passed. Include the NOT VERIFIED status and explanation in the manifest.
- Readback success alone must never be represented as full DICOM compatibility.
- If the external validator completes its check and identifies a CT Image IOD violation, report external FAILED, show overall Validation Failed, and block ZIP on both UI and backend even when every mandatory check is PASSED.
- Display DICOM Tag, error type, and description when supplied by the validator. Keep generated files and diagnostic results viewable and offer correction and regeneration.
- If the external check is PASSED and all mandatory checks pass, allow export and include the independent validation results in manifest.json.
- If the external validator reports only noncritical warnings without violations of mandatory CT Image IOD requirements, show WARNING, allow export when mandatory checks pass, and preserve the warnings in manifest.json.
- Distinguish actual CT Image IOD violations, validator startup/execution failures, and findings specific to an optional vendor profile. Optional vendor-profile findings must not be misclassified as CT Image IOD violations. Preserve their context in the diagnostic output and manifest.

Examples of diagnostic messages supplied by the learner:

- DICOM: Missing required CT attribute.
- HL7: Invalid PID-3 identifier.
- FHIR: Unresolved Patient reference.
- Consistency: Patient ID mismatch between DICOM and HL7.

### ZIP Export and Enforcement

Source: scope.md > The POC Boundary > P0: Web UI and ZIP Export.

**Never silently export data that failed mandatory validation.**

Download ZIP is allowed only when all four conditions hold simultaneously:

1. All mandatory checks are PASSED: DICOM serialization/readback, HL7 structural validation, FHIR R4 validation, and cross-standard consistency.
2. External CT IOD validation is PASSED, WARNING, or NOT VERIFIED.
3. There are no confirmed CT Image IOD conformance failures.
4. Generation of all required files has completed successfully.

Any confirmed CT Image IOD violation reported by an external validator blocks export on the backend regardless of all other check results. A NOT VERIFIED result permits export with the explicit warning only when the other conditions hold; it never establishes conformance and never overrides a known conformance failure.

A dataset generation/export system error prevents export. A failure confined to executing the optional external validator is NOT VERIFIED, not a detected conformance violation. All export-permission statements elsewhere in this document are subject to the four conditions above.

The same restriction must be enforced on the backend. Direct API requests must not bypass a failed or incomplete mandatory-validation gate or a detected external CT IOD conformance failure. The UI state alone is insufficient.

Archive layout:

- dicom/*.dcm
- hl7/ORM_O01.hl7
- fhir/bundle.json
- manifest.json

Acceptance criteria:

- The ZIP contains the generated dataset and validation results in manifest.json.
- Manifest results reflect the actual performed, failed, unperformed, and warning outcomes; no fabricated conformance claim is included.
- A direct download request for a dataset with failed mandatory validation or external CT IOD FAILED is rejected and returns no dataset archive.
- The downloaded contents correspond to the dataset whose results were inspected and passed the required checks.
- Automated verification must cover successful export and denial for each failed gate condition, including missing/incomplete required files, confirmed conformance failures despite other passing statuses, external FAILED, and mandatory checks that are not PASSED. Cover external PASSED, WARNING, and NOT VERIFIED when the other conditions hold, including external-validator startup failures.

### Atomic Replacement and Diagnostic Candidates

Learner-approved refinement during 4-spec; the export rule applies to the selected dataset, not indiscriminately to every dataset in the browser session.

- Keep the current active result and its sessionStorage dataset_id while building a separate candidate. Disable Generate Dataset while generation is running.
- Promote the candidate only after all required files, validation outcomes, absence of confirmed CT IOD failures, and ZIP preparation satisfy the approved export policy. Then switch to the new result, update the active identifier, and retire the old active dataset.
- A failed candidate must not delete the prior active dataset or extend its TTL. Show failed-candidate diagnostics and allow returning to the prior valid result; that prior result remains downloadable only while unexpired and export-eligible.
- Retain at most one latest failed diagnostic candidate per session, for 30 minutes from its own creation, with export blocked. Remove older failed candidates.
- A system failure cleans up unusable intermediate data, shows an understandable error, and preserves the previous unexpired active result and its eligible download.
- Each dataset expires 30 minutes from creation. Do not revive an old result that expires during a new attempt. Backend restart loses all datasets.
- Backend conflict control must prevent stale parallel requests from replacing a newer accepted result; frontend disabling alone is insufficient.
## States and Boundaries

- **First use:** prefilled synthetic patient and study, default five slices, primary Generate Dataset action, no generated dataset available for download.
- **Generating:** visible progress indicator and disabled Generate Dataset; no export of the unfinished candidate. Preserve the prior active result, subject to its existing TTL and export eligibility.
- **Mandatory validation passed:** inspect results; enable ZIP only when external CT IOD validation is PASSED, WARNING, or NOT VERIFIED and no generation/export system error prevents completion.
- **Mandatory validation failed:** red status, specific known findings, available generated data remain visible, no ZIP, Generate Again available.
- **Independent CT IOD validation failed:** overall Validation Failed, known tag/type/description details, generated results remain inspectable, ZIP blocked on UI and backend, correction and regeneration available.
- **Independent CT IOD validation not completed:** gray Not Verified and the explicit conformance warning; explain whether the validator is missing, unavailable, or failed to execute. ZIP is permitted when all mandatory checks pass and no generation/export system error prevents completion.
- **Independent CT IOD warnings only:** external WARNING with findings retained; ZIP permitted when mandatory checks pass and no generation/export system error prevents completion.
- **Generation/export system error:** understandable user-facing message, no internal traceback, no ZIP for the failed attempt, and an option to generate again. Preserve the prior active result and its eligible export while unexpired. A failure confined to executing the optional external CT IOD validator follows the NOT VERIFIED policy instead.
- **Noncritical warning:** show the finding accurately; WARNING is not a substitute for a required PASSED result.
- **Access:** no registration or authentication for this MVP.

## Product Decisions

- Use a prefilled form so the first meaningful action can be Generate Dataset.
- Default to five slices while retaining the approved 1–10 range.
- Keep modality, resolution, and SOP Class fixed to the approved CT MVP.
- Use three tabs for inspection of the linked standard-specific outputs.
- Preserve generated data for diagnosis after mandatory-validation failure while blocking export.
- Enforce mandatory-validation gating and the external CT IOD failure veto on both UI and backend.
- Permit export with an unavailable, uninstalled, or technically unsuccessful independent CT IOD validator only with passed mandatory checks, clear Not Verified reporting, the explicit warning, and no blocking generation/export error. External warnings alone may permit export; real CT IOD violations always block it.
- Use a light, minimal, responsive interface with the supplied English copy and synthetic-data notice.
- Keep optional features deferred and obtain agreement before any CT scope reduction.

## What We're Building

The approved P0 CT generator, linked ORM^O01 and FHIR R4 Bundle, consistency checks, prefilled responsive web interface, diagnostic previews, honest validation reporting, gated ZIP export, manifest, and automated tests. Detailed implementation mechanisms belong in 4-spec.

## Deferred From the POC

Source: scope.md > Later.

ADT^A01, other SOP Classes, C-STORE/MLLP/FHIR REST transmission, bulk generation, and AI-powered scenario creation are optional later work. They are not prerequisites for completing P0 and must not be added automatically.

## Non-Goals

Source: scope.md > Explicitly Cut; The POC Boundary > Constraints and Risk Handling.

No Secondary Capture substitution for CT mode, database, paid APIs, integration with external medical systems, or sourcing real patient records. No registration or authentication. No clinical-use claim and no claim of full DICOM conformance based only on parsing/readback.

## Open Questions

### Product Decisions Resolved

The final four-condition backend export rule is agreed. No unresolved product decision blocks technical planning.

### Planning Review Preference

- Markdown or an additional visual HTML companion remains unanswered. This does not change scope approval or authorize a change in product behavior.

### Technical Planning Follow-Up

- Specify exact cross-format mappings, FHIR Bundle details, validator tools and coverage, and automated checks in 4-spec. Preserve the learner's distinction between required structural checks and independent CT IOD validation.
- Translate the approved form, status, and failure behavior into input rules and execution details without adding product features or claiming implementation.

## Approved Validator Integration Refinement

The learner approved dciodvfy with the tested Windows delete-on-close method A. Main datasets, ZIPs and reports remain in RAM. A single temporary seekable synthetic DICOM file at a time is permitted solely for independent validation of each instance. No method B automatic fallback. Capture and classify stdout, stderr and exit code; exit zero alone cannot establish PASSED. Unknown diagnostics or technical inability are NOT VERIFIED with a reason, never silent success. Any confirmed CT IOD violation remains FAILED and blocks export even if a later technical error occurs. Preserve per-instance findings in the report and manifest.

Verify normal/error/timeout cleanup and provide bounded cleanup of application-owned crash remnants without touching unrelated temporary files. Document power-loss and file-lock limitations. Windows 10 build 19045 is the target; Windows 11 qualification is additional when available. See spec.md for implementation details. This refinement does not approve the whole technical specification or start application coding.