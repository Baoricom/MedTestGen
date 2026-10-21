---
doc: scope
status: approved
---

# MedTestGen

A web-based generator of interconnected synthetic CT DICOM, HL7 v2.5.1, and FHIR R4 test datasets from one patient and imaging study scenario.

## The Unique Kernel

**One Patient. Three Standards. Consistent Test Data.**

One canonical data model drives all three outputs, keeping patient, order, study, series, and instance identifiers consistent wherever applicable. The value is a linked dataset suitable for demonstration and integration testing, rather than three independently generated samples.

## Who It's For

DICOM equipment testers and healthcare integration engineers who need usable test objects for demonstrations and testing of DICOM/HL7 software and equipment. The learner reports that they currently rely on a limited collection of anonymized data because of patient-data privacy constraints. MedTestGen generates synthetic data instead of requiring real patient records.

## The Core Loop

The user opens the web interface, generates a synthetic patient, configures a CT study, and generates linked DICOM, HL7, and FHIR outputs. They inspect the results and validation findings, then download the dataset as a ZIP for use in their testing or demonstration workflow.

Actual data transmission to external systems is outside this MVP. Detailed input controls, preview behavior, and error handling will be defined in the PRD.

## Inspiration & Identity

Product name: MedTestGen.

Tagline: One Patient. Three Standards. Consistent Test Data.

The learner requested a professional web interface. Specific layout, colors, and typography have not yet been selected; these will be established in the PRD interview.

## Why This Matters to the Learner

Provide useful synthetic datasets for medical integration testing and demonstrations without depending on a small set of anonymized source objects.

## What "Working" Looks Like

A user requests a synthetic CT study and obtains 1–10 CT DICOM slices, a matching ORM^O01 order, and one FHIR R4 Bundle containing Patient, ServiceRequest, and ImagingStudy. The interface provides previews and validation results, and a ZIP contains all three formats.

The demonstration shows that the patient and accession identifiers agree across outputs and that the FHIR ImagingStudy reflects the actual DICOM study, series, and instances. The ServiceRequest reflects the same order represented in ORM^O01.

Successful parsing by pydicom alone must never be presented as proof of full DICOM compliance. Validation reporting must distinguish checks actually performed from unperformed or unavailable checks. Independent CT Image IOD validation is required when an appropriate validator is available; its availability and integration must be investigated in the technical plan.

These statements define acceptance goals. No generator, validation functionality, or export has been implemented yet.

## The POC Boundary

### P0: CT DICOM Generation

- CT Image Storage SOP Class UID: 1.2.840.10008.5.1.4.1.1.2; Modality: CT.
- Explicit VR Little Endian transfer syntax.
- Generate 1–10 synthetic slices in one study and one series.
- 512 x 512 pixels, 16-bit grayscale, MONOCHROME2.
- Synthetic geometric imagery resembling a CT phantom.
- Correct CT Image IOD structure and required attributes, including Pixel Data, Rescale Slope/Intercept, Pixel Spacing, Slice Thickness, Image Position (Patient), and Image Orientation (Patient).
- Shared Study Instance UID, Series Instance UID, and Frame of Reference UID; unique SOP Instance UID per slice and consistent slice geometry.
- Use pydicom to create files. Use an independent CT Image IOD conformance check if an appropriate validator is available.
- Never substitute Secondary Capture for CT Image Storage without an explicitly agreed scope change.

### P0: HL7 Order

- One HL7 v2.5.1 ORM^O01 CT order with correct MSH, PID, PV1, ORC, and OBR segments.
- Patient ID, Accession Number, and ordered-study information agree with the generated CT study.
- Document the selected HL7-to-DICOM field mappings separately in the technical documentation.

### P0: FHIR R4 Bundle

- One Bundle containing Patient, ServiceRequest, and ImagingStudy, with correct internal references.
- ImagingStudy reflects the generated DICOM study, series, and SOP instances.
- ServiceRequest corresponds to the ORM^O01 order.

### P0: Cross-Standard Consistency

- Generate all outputs from one canonical data model.
- Keep Patient ID/MRN and Accession Number consistent across applicable fields.
- Keep Study, Series, and SOP Instance UIDs consistent between DICOM and FHIR.
- Include automated tests for generation, validation, and identifier/reference consistency, retaining the learner's original testing requirement.

### P0: Web UI and ZIP Export

- Generate synthetic patient demographics and configure the CT study.
- Preview results and show validation findings.
- Download DICOM, HL7, and FHIR outputs in one ZIP.

### Constraints and Risk Handling

- Windows 10 build 19045 is the approved development baseline, with PowerShell-compatible instructions. Check Windows 11 additionally when available; absence of that environment does not block MVP.
- No database, paid APIs, or external medical systems for the initial MVP.
- Preferred stack remains Python, FastAPI, pydicom, hl7apy, FHIR R4-compatible models, HTML, CSS, and JavaScript; detailed technical choices belong in 4-spec.
- If CT Image IOD implementation creates a deadline risk, explain the risk and propose scope reduction before changing requirements. Do not silently weaken conformance claims or replace CT with Secondary Capture.
- Finish approved planning documents and the build checklist before application coding.

## Implementation Priorities

The learner's priority order is:

1. A working, verified CT DICOM generator.
2. HL7 ORM^O01.
3. FHIR R4 Bundle.
4. Cross-standard consistency checks.
5. Web UI and ZIP export.
6. Additional capabilities only after P0 and a separately agreed extension.

The build checklist will turn these priorities into verifiable working steps. This scope does not approve a build checklist or authorize skipping planning.

## Later

The learner classified the following as P1, outside the required first MVP:

- HL7 ADT^A01.
- Other DICOM SOP Classes.
- C-STORE, MLLP, and FHIR REST transmission.
- Bulk generation beyond the scoped single study.
- AI-powered scenario creation.

These are optional extensions, not automatic work after P0. They are deferred to keep the first demonstration focused on the consistent three-standard dataset.

## Explicitly Cut

- Secondary Capture as the CT-mode output: the learner explicitly requires CT Image Storage.
- Database persistence, paid APIs, and integration with external medical systems: excluded by the learner's initial MVP constraints.
- Use of real patient records as the source of the generated demonstration dataset: the product is explicitly synthetic.
- Treating pydicom readability as evidence of full DICOM conformance: explicitly rejected by the learner.

## Approval

The learner explicitly approved the P0/P1 scope in conversation and requested continuation to the next Devpost phase. This document preserves that approval and the detailed CT requirements from the immediately preceding clarification. No second scope sign-off is required.

Detailed product behavior and technical design remain subject to their respective PRD and specification reviews.
