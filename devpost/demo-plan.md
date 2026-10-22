# MedTestGen Two-Minute Demo Plan

This is a recording plan, not a narration script. The entrant writes and speaks the final explanation in their own words. Target length: about 2:00; the official limit is under 3:00.

## Before Recording

- Use a clean browser window at `http://127.0.0.1:8000` and a fresh tab session.
- Close notifications and unrelated windows; do not expose account details, local paths, tokens, or personal information.
- Keep the default five-slice CT Head scenario and synthetic values.
- Confirm `dciodvfy` is available and the five per-instance results are actual `PASSED`, not staged text.
- Prepare an empty download folder so the ZIP and its contents are easy to show.

## Shot List

| Time | Show | Evidence to make visible |
|---|---|---|
| 0:00–0:12 | Product header and generator | Name, one-patient/three-standards purpose, intended DICOM testers and integration engineers, synthetic-data notice. |
| 0:12–0:28 | Prefilled form | Synthetic patient, CT Head, CT Image Storage, 512×512 and five slices. |
| 0:28–0:48 | Click **Generate Dataset** | Real progress state, then **Required Checks Passed**. Keep the generation uncut if practical. |
| 0:48–1:10 | DICOM tab | Five CT instances, shared Study/Series/Frame of Reference UIDs, unique SOP Instance UIDs and phantom preview. |
| 1:10–1:28 | HL7 and FHIR tabs | ORM^O01 plus Bundle; point out the same Patient ID and accession, and the DICOM UIDs represented in ImagingStudy. |
| 1:28–1:46 | Validation panel | DICOM readback, HL7, FHIR and consistency are mandatory checks; external CT IOD is a separate per-instance `dciodvfy` result. State that it is independent evidence, not absolute compatibility proof. |
| 1:46–1:58 | Download ZIP and open it | `dicom/` with five files, `hl7/ORM_O01.hl7`, `fhir/bundle.json`, and `manifest.json` with validation results and hashes. |
| 1:58–2:00 | Return to result header | End on the working result and synthetic-data notice. |

## Recording Review

- The app is shown functioning on Windows from input through ZIP output.
- All claims match the visible run; no `PASSED` status is described unless it appears in the recording.
- The video is in English, or includes an English translation.
- No copyrighted music, unauthorized third-party material, real health information, or unrelated trademarks are visible.
- Upload publicly to YouTube or Vimeo, verify playback without authentication, and paste that URL into Devpost.
