# CT profile implementation checklist

Implementation baseline: classic CT Image Storage, DICOM PS3.3 module table A.3.3 (2026d online reference consulted during planning). This is a synthetic derived HEAD profile, not a complete independent conformance engine.

| Module | Implemented profile |
| --- | --- |
| Patient | Name, ID, issuer, birth date and sex; unknown sex is present empty |
| General Study | Study UID, date/time, referring physician present empty, Study ID and accession |
| General Series | Modality, series UID/number, patient position; HEAD is unpaired so Laterality is absent |
| Frame of Reference | Shared UID and present-empty position reference indicator |
| General Equipment | Manufacturer identifies synthetic generator |
| General Acquisition / General Image | Acquisition and instance numbers, derived secondary axial image type, patient orientation; no claim of physical acquisition |
| Image Plane | Pixel spacing, thickness, position and orientation |
| Image Pixel | 512x512 monochrome unsigned 16-bit pixels, bit fields and exact byte length |
| CT Image | Rescale slope/intercept/type and applicable Type 2 CT values, present empty when unknown |
| SOP Common / file meta | Class and instance UIDs, character set, matching media storage UIDs, transfer syntax and implementation UID |

Contrast, synchronization, multi-energy and CT-for-processing conditions are not asserted. No optional vendor profile is selected. Required-field presence/readback checks and independent dciodvfy checks remain separate. Check tests and build evidence for the actual validated cases; this checklist alone is not proof of complete IOD conformance.