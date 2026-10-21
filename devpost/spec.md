---
doc: spec
status: approved
---

# MedTestGen — Technical Specification

## How This Works, In Plain Language

One patient and one CT order become a single shared scenario. Three generators read that scenario to produce CT DICOM slices, an HL7 order, and a FHIR Bundle. Checks read the actual generated outputs and compare them. The browser shows the results and the backend permits ZIP export only when the approved checks allow it.

Datasets, ZIPs, and reports stay in backend RAM for 30 minutes from creation. The only approved disk exception is one short-lived, seekable synthetic DICOM file at a time for dciodvfy, using the tested Windows delete-on-close method A. A new dataset replaces the previous one only after generation, validation, and ZIP preparation succeed.

This is the complete specification submitted for approval, not a claim of implemented application functionality. Scope and PRD are approved. The learner explicitly approved this full specification and its mappings; stage 4-spec is complete. Application implementation starts in 5-build after that sign-off and the skill's build planning checkpoint.

## Stack

The learner's Python/FastAPI/pydicom/hl7apy/FHIR R4 models/HTML/CSS/JavaScript preference is retained. Proposed qualification baseline: Windows 10 build 19045, Python 3.10.11 x64 (the PoC environment). Windows 11 is an additional compatibility target when available, not an MVP blocker.

| Dependency | Proposed pin | Purpose and documentation |
| --- | --- | --- |
| FastAPI | 0.119.1 | Local HTTP API and static UI; [documentation](https://fastapi.tiangolo.com/) |
| Uvicorn | 0.34.2 | Single-process server; [settings](https://www.uvicorn.org/settings/) |
| Pydantic | 1.10.26 | Request models and compatibility with the selected FHIR models; [v1 documentation](https://docs.pydantic.dev/1.10/) |
| pydicom | 3.0.2 | DICOM serialization/readback; [documentation](https://pydicom.github.io/pydicom/stable/) |
| NumPy | 2.2.6 | Phantom pixel arrays; [documentation](https://numpy.org/doc/2.2/) |
| hl7apy | 1.3.5 | HL7 v2.5.1 structure and validation; [tutorial](https://hl7apy.readthedocs.io/en/latest/tutorial/) |
| fhir.resources | 6.1.0 | FHIR **R4 4.0.1** models; [version documentation](https://pypi.org/project/fhir.resources/6.1.0/) |
| dicom3tools | 20260927 | Windows dciodvfy binary; [package](https://pypi.org/project/dicom3tools/), [tool documentation](https://www.dclunie.com/dicom3tools/dciodvfy.html) |
| pytest / HTTPX | 8.4.2 / 0.28.1 | Automated unit/integration/API tests; [pytest](https://docs.pytest.org/en/stable/), [HTTPX](https://www.python-httpx.org/) |

Do not upgrade fhir.resources blindly: version 6.5.0 targets R4B, not the required R4. Assert the selected package's FHIR version is 4.0.1 and validate generated resource JSON with its R4 classes. The older Pydantic/FHIR combination is a deliberate proposed local-MVP compatibility choice; no claim of latest-version support is made. Resolve and lock transitive dependencies, run pip check and import/serialization smoke tests early in 5-build. Metadata resolution is not runtime verification.

Python standard-library BytesIO, zipfile, secrets, uuid, tempfile, subprocess, threading, and time cover storage, export, identifiers, process control, and lifecycle. No Node build, database, account service, paid API, external medical system, or online terminology service is required. Package installation needs internet; normal generation does not.

## Where It Runs and How Someone Tries It

Proposed delivery is a local browser app on the learner's Windows machine. Run one worker on loopback. Public hosting is not part of this specification. These are planned commands, usable after 5-build creates the referenced files:

```powershell
Set-Location 'C:\Projects\MedTestGen'
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe -m uvicorn medtestgen.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Open http://127.0.0.1:8000. No environment activation or PowerShell execution-policy change is needed. Do not use auto-reload for the recorded demonstration: restarts lose RAM datasets. No API keys. requirements-dev.txt includes runtime requirements and testing dependencies; requirements-validator.txt pins dicom3tools separately so a missing optional validator can be reported honestly without disabling the core app. Install it for the full demonstration:

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-validator.txt
```

Demo: generate the default five slices; inspect all three standards and matching identifiers; show actual separate validation statuses; download and inspect ZIP; demonstrate one blocked-validation test using automated evidence. The official skill's submission workflow requires a short demo video and public GitHub repository. Deployment is optional. Recheck competition submission details in 6-ship; do not invent a deadline.

## The Core Journey Through the System

Implements `prd.md > The Core Journey` and `Atomic Replacement and Diagnostic Candidates`.

1. The page obtains synthetic defaults and a random session token from the backend.
2. Generate submits the filled form and an expected session revision. Backend validates inputs, reserves memory, and admits one generation attempt.
3. Create a candidate with its own creation time and 30-minute TTL. Build a canonical scenario, then DICOM, ORM, and FHIR bytes in RAM.
4. Independently read and check outputs. Run external CT validation sequentially for every serialized instance. Preserve diagnostic outputs even when validation fails.
5. If all export conditions are satisfied, build the ZIP in RAM, then atomically promote the candidate under the session lock. Only then remove the old active dataset.
6. Otherwise retain the latest usable failed candidate for diagnosis, preserving the prior active dataset and its original expiry. System errors release unusable intermediates.
7. The UI displays the selected result; downloads always recheck backend eligibility. Refresh reconciles with backend session state, including after a lost promotion response.

## Components

### Dataset Generator UI

Implements `prd.md > Dataset Generator`, `Patient Information`, `Imaging Study and CT Output`, and `Look and Feel`.

Serve static HTML/CSS/JavaScript from FastAPI. Carry forward the exact title, tagline, description, and synthetic-use notice. Prefill every field. Randomize Patient changes patient fields only; generation is the main action. Fixed CT/SOP/resolution controls are read-only. Use an indeterminate progress indicator, not invented percentages. Disable generation until completion or authoritative reconciliation of an interrupted request.

Use a light background, dark readable text, restrained blue primary action, system fonts, two-column desktop form collapsing to one column on mobile. Show status text with color, keyboard-accessible tabs, labeled fields, visible focus, and an error summary. Use textContent for user/validator content; never render it as HTML. No frontend framework or CDN dependency.

### Canonical Scenario Builder

Implements `prd.md > Patient Information` and `Linked HL7 and FHIR Outputs`.

Validate input once, generate identifiers once, and freeze the scenario for all generators. No generator independently invents patient, order, study, series, or instance identifiers. User-edited values remain synthetic inputs; show the synthetic-only notice. No upload/import feature.

Proposed input profile: MRN 1–64 characters, accession 1–16 characters, study description 1–64 characters, slice count integer 1–10, birth date valid and not future, sex M/F/O/U. Reject control characters and structural separators in identifiers. Use a documented single Patient Name field in `Family^Given` notation with an inline example; support Unicode, optional given name, and a maximum 64-character PN component group. Reject unsupported PN component forms with a field error rather than silently splitting or losing text. The form label remains Patient Name. These interface/input details are proposed for final review, not previously approved restrictions.

### CT DICOM Generator

Implements `prd.md > Imaging Study and CT Output`.

Generate classic single-frame CT Image Storage `1.2.840.10008.5.1.4.1.1.2`, Explicit VR Little Endian `1.2.840.10008.1.2.1`. Never substitute Secondary Capture. ImageType DERIVED\\SECONDARY\\AXIAL describes synthetic pixels and does not change the SOP Class.

One study, one series, one Frame of Reference, N distinct SOP Instance UIDs. Use pydicom generate_uid; mirror class/instance UIDs in file meta. Include file preamble and correct file meta, and serialize with enforce_file_format=True into BytesIO.

| Area | Fixed profile or scenario-derived values |
| --- | --- |
| Patient / study | PatientName, PatientID, issuer, birth date, mapped sex; StudyInstanceUID, StudyDate/Time, StudyID, AccessionNumber, StudyDescription; ReferringPhysicianName present, empty if unknown |
| Series / frame | SeriesInstanceUID, Modality CT, SeriesNumber 1, BodyPartExamined HEAD, PatientPosition HFS, FrameOfReferenceUID; PositionReferenceIndicator present empty |
| Equipment / image | Manufacturer MEDTESTGEN, synthetic derivation description, InstanceNumber 1..N; required General Acquisition and General Image attributes applicable to this derived phantom; LossyImageCompression 00, BurnedInAnnotation NO |
| Pixel module | Rows=Columns=512, SamplesPerPixel=1, MONOCHROME2, BitsAllocated=BitsStored=16, HighBit=15, unsigned PixelRepresentation=0, little-endian uint16 PixelData of exactly 524288 bytes per slice |
| Geometry | PixelSpacing [0.5,0.5] mm, SliceThickness 1 mm, ImageOrientationPatient [1,0,0,0,1,0], ImagePositionPatient [0,0,i] mm for zero-based i; coherent increasing slice locations |
| Rescale | Slope 1, Intercept -1024, RescaleType HU; display window fixed and documented, not a diagnostic viewer |
| CT attributes | ImageType as above; KVP, ScanOptions, DataCollectionDiameter, ReconstructionDiameter, GantryDetectorTilt, TableHeight, RotationDirection, ConvolutionKernel and any other applicable Type 2 attributes present with appropriate values or empty where allowed |

Phantom pixels use a background and geometric inserts with deterministic values (for example 0, 750, 1024, 1500). No anatomical realism or simulated physical scanner acquisition is claimed. Editing Study Description changes the order/display description; the initial phantom profile remains head-oriented. No contrast, multi-energy acquisition, overlays, or vendor-specific profile is asserted. Omit Laterality for this unpaired HEAD profile; do not insert an empty conditional field blindly.

This table is an implementation profile, not a substitute for the normative IOD tables. During the first CT build slice, create a reviewed attribute checklist against [PS3.3 A.3.3](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_A.3.3.html) and its mandatory/conditional modules: Patient, General Study, General Series, Frame of Reference, General Equipment, General Acquisition, General Image, Image Plane, Image Pixel, CT Image, SOP Common. Satisfy all Type 1/2 and triggered conditional requirements. Record the standard edition used. The corrected PoC fixture is a starting reference, not proof that every application case conforms.

### HL7 Order Generator

Implements `prd.md > Linked HL7 and FHIR Outputs`.

Create an hl7apy ORM_O01 object with version 2.5.1 and the actual message/group hierarchy, including patient/visit and order/detail groups; do not validate unrelated loose segments as if they were a complete message. Output MSH, PID, PV1, ORC, OBR in that order, CR segment separators, UTF-8 bytes, and MSH-18 UNICODE UTF-8. MSH-9 is ORM^O01^ORM_O01, MSH-11 T (training), MSH-12 2.5.1, MSH-10 a unique control ID. PV1-2 O represents a synthetic outpatient visit. ORC-1 NW represents the generated new order.

Use hl7apy escaping/structured fields to preserve content; test separators and Unicode. See [mappings.md](mappings.md) for MRN, placer/filler numbers, accession, procedure and timestamps. The accession mapping is an explicit local radiology convention, not a claim of universal receiving-system compatibility. No MLLP transmission or ACK workflow.

### FHIR Bundle Generator

Implements `prd.md > Linked HL7 and FHIR Outputs`.

Generate FHIR R4 4.0.1, Bundle.type collection with exactly Patient, ServiceRequest, ImagingStudy. UUID resource IDs and `urn:uuid:` fullUrls permit all references to resolve within the Bundle without a FHIR server. ServiceRequest.subject and ImagingStudy.subject refer to Patient; ImagingStudy.basedOn refers to ServiceRequest. No transaction request entries.

Patient carries MRN, structured name, birth date, mapped gender. ServiceRequest status active, intent order, local CT procedure coding and order identifiers. ImagingStudy status available, one series, exact instance count, CT modality, every generated SOP UID and class, matching study/series UIDs. The Bundle is a static test scenario joining a new-order message to generated images; it does not simulate a full order lifecycle. Mapping details and R4 sources are in mappings.md.

### Mandatory Validation and Consistency

Implements `prd.md > Validation Reporting` and `ZIP Export and Enforcement`.

Validate the serialized outputs, not only the shared input model:

1. DICOM: deserialize every byte stream, verify file meta/transfer syntax/class, pixel decoding/length, expected required-profile tags, UID uniqueness and sharing, geometry, values and slice count.
2. HL7: parse serialized ORM as v2.5.1 with grouping and run strict structural validation; require the five selected segments and the application's populated identifiers/order fields.
3. FHIR: parse serialized JSON through pinned R4 models; check required enums and generated-profile constraints, Bundle type, unique fullUrls, reference resolution/type, patient/order links, modality, UID forms, and counts. Model validation alone is not a full terminology/profile/FHIRPath conformance engine; report this coverage honestly.
4. Cross-standard: extract and compare patient demographics, MRN/authority, accession, order ID/code/description, study/series/SOP UIDs and counts from actual DICOM, HL7 and FHIR using mappings.md normalization rules.

All four categories must actually execute and return PASSED for export. A required check that cannot run is NOT VERIFIED and blocks export; detected errors are FAILED. Keep precise field/tag/path and reason when known. Do not turn readback into a full conformance claim.

### External CT IOD Validator Adapter — Approved Method A

Implements `prd.md > Validation Reporting`; follows the learner-approved External CT IOD Validator Integration exception.

Main data storage stays RAM-only. Serialize validation across all N instances, with at most one temporary `.dcm` file open at a time. No stdin transport, no method B fallback, no permanent DICOM output folder. No dcentvfy in mandatory MVP.

Qualification: Windows 10 build 19045, Python 3.10.11 x64, dicom3tools 20260927. Locate the packaged executable using dicom3tools.bin_dir(), not an arbitrary executable from PATH. Record version and binary digest in validation metadata. PoC binary SHA256: `7f42d1d165d4f8d4e436d863501a6c8c50987b671d7f5c2fe83c662a227cd14b`.

For each instance:

1. Create a uniquely named application-owned invocation directory under the OS temporary location. Create `tempfile.NamedTemporaryFile(mode='w+b', suffix='.dcm', delete=True, dir=...)` and retain its handle. Write bytes and flush before invoking the validator.
2. Python 3.10 does not have delete_on_close as a keyword. The tested `delete=True` held-open behavior uses Windows delete-on-close. On later Python versions inspect API/platform support and requalify held-open sharing; do not silently substitute `delete_on_close=False` or closed-file deletion.
3. Invoke `[executable, '-new', path]` without a shell or visible console. Proposed timeout: 10 seconds per instance; collect stdout, stderr and exit code separately. Drain both streams concurrently with bounded capture (256 KiB per stream per instance); on overflow stop/reap the child, retain collected evidence and mark incomplete classification. No raw output to persistent logs.
4. On timeout/cancellation/exception, terminate the owned subprocess, wait for exit with a bounded grace interval, then release file handles. Keep any conformance findings captured before failure. Never leave a still-running child while assuming cleanup succeeded.
5. Close the temporary file, verify its path is absent, then remove the exact owned invocation directory. Record cleanup outcome separately. If cleanup fails, show a technical limitation; preserve a confirmed FAILED result. Without confirmed violations, a cleanup/execution failure prevents PASSED and yields NOT VERIFIED. Do not replace confirmed conformance failures with a technical status.

Compatibility of this Cygwin-based executable with a held-open delete-on-close file was observed in the PoC. It is not a general Windows sharing guarantee.

#### Classification and aggregation

Parse both streams with a version-specific parser tested against recorded diagnostics. Preserve normalized diagnostic text (redacting temporary absolute paths), tags, severity, and whether a finding is a confirmed CT IOD violation. Recognize benign CTImage identification output explicitly. Unknown lines, truncated capture, unexplained nonzero exit, or a failed invocation must never become PASSED. A nonzero exit alone is not proof of IOD failure; exit zero does not clear an Error diagnostic.

| Evidence | Per-instance status |
| --- | --- |
| At least one confirmed CT IOD violation, with or without later technical failure | FAILED; retain irreversible confirmed-failure flag |
| Incomplete run, unavailable tool, technical failure, unknown/unclassifiable diagnostics, without confirmed violation | NOT VERIFIED, explicit reason |
| Completed run and recognized warnings only | WARNING |
| Completed run, acceptable exit, only recognized benign output, no errors/warnings, cleanup verified | PASSED |

Do not use an optional vendor profile. If such a finding occurs, retain its context and do not classify it as a base CT IOD violation without evidence. Parser uncertainty is visible NOT VERIFIED, not silent success. Add captured examples as regression fixtures.

Study aggregate precedence: FAILED if any instance has a confirmed failure; else NOT VERIFIED if any instance is unverified; else WARNING if any has warnings; else PASSED only if all N instances passed. Preserve all individual findings even when aggregate status hides another severity. Missing result for any expected instance means NOT VERIFIED. Attempt every instance when technically possible; if the tool is unavailable, create a separate unavailable result for each expected SOP UID.

#### Cleanup and crash limits

Use an application-specific temporary root, per-run random directory, and a lock held for the lifetime of that run. Record only cleanup ownership metadata on disk, never dataset/validation reports. On startup, inspect at most 100 matching owned run directories; only after obtaining their abandoned lock and verifying the root, marker, exact containment and absence of reparse points may the app delete known invocation files. Do not follow symlinks/junctions or delete unknown entries. Skip active/locked runs and surface inability to clean. This is bounded cleanup of application-owned remnants, not a sweep of system TEMP.

The proposed implementation uses a Windows Job Object with kill-on-job-close for the validator process, assigned while suspended before resuming, so abrupt backend death does not intentionally leave its child running. Use the standard-library ctypes Windows API boundary; test availability and assignment failure early. If lifecycle supervision or delete-on-close compatibility cannot be established, report NOT VERIFIED and do not use a different transport. This lifecycle control is proposed implementation work, not a completed PoC result.

PoC proved normal cleanup, an exception after child exit, deterministic timeout/termination of a suspended child, and owner termination without a live reader. Live-child owner death remains a build qualification test. Power loss, OS crashes, antivirus/third-party locks and secure erasure were not proven. Cleanup can be delayed until the final compatible handle closes. Deletion is not secure erasure. Document these limits in README and report operational failures without exposing internal tracebacks.

### In-Memory Store and Atomic Replacement

Implements `prd.md > Atomic Replacement and Diagnostic Candidates` and `States and Boundaries`.

One backend process owns all state. A 256-bit random session token, stored in sessionStorage, groups active and latest failed datasets; it is not an account/login. Each dataset has an independently random 256-bit dataset_id. Require the session token in a header and verify ownership on all result/download routes; tokens must not appear in URLs or access logs. No CORS access from other origins. Browser stores only tokens/IDs/revision, not medical objects in persistent storage.

Server holds session revision and a generation-in-progress flag. At admission, lock the session, require matching expected revision, reserve capacity, increment revision and set busy. Proposed MVP global generation capacity is one; same-session overlap or stale revision returns 409, global capacity exhaustion returns 503 with retry guidance. Offload blocking generation so reads/downloads remain responsive. Do not queue unbounded work.

Promotion under lock requires a complete still-unexpired candidate, export eligibility, and ZIP ready. Switch active pointer and retire old active payloads atomically. A failed candidate replaces only the previous failed diagnostic candidate, never the valid active dataset. A system error drops unusable intermediates and preserves active state. Always release busy state/reservation in finalization. Retain at most one failed candidate per session. An expired old dataset is never revived.

Browser includes a fresh request ID, checks returned revision, and reconciles GET /api/session after an uncertain response rather than blindly resubmitting. The server rejects overlap even if browser controls are bypassed. If the original request finished but its response was lost, session reconciliation returns the new authoritative active ID; update sessionStorage only from that response. A duplicated tab sharing the token is handled as the same session, protected by server revision/lock.

TTL is 30 minutes from candidate creation using monotonic deadlines; UTC timestamps are for display/manifest. Reads, downloads, failures and promotion never extend TTL. Check expiry on every access and in a 60-second cleanup loop. Keep expired-ID tombstones with owning session for at most 30 more minutes and at most 1024 entries, without content. Known expiry returns 410; unknown/retired/foreign identifiers return 404. Restart loses everything, including tombstones. In-flight downloads authorized before expiry may finish; new requests after expiry are refused.

Proposed initial limits for review: 256 MiB total accounted retained/transient payload budget; 32 MiB per completed dataset including files/ZIP/report/preview; 64 MiB reservation for the one generation operation; 16 KiB request bodies; 64 concurrent session records. Count old active and failed records while reserving a replacement; never evict a valid dataset to make its replacement fit. Expire stale entries first, otherwise reject admission with 503. Release unused reservation after finalization. Account buffers and outgoing ZIP response references until released; bound diagnostic capture and preview allocation. These are application allocation limits, not a guarantee of total process RSS. Measure peak RAM in build tests. Remove empty idle sessions after 30 minutes, never while work is in progress.

### Results and ZIP Export

Implements `prd.md > Output Inspection`, `Result Panel`, `Validation Reporting`, and `ZIP Export and Enforcement`.

Return metadata and text previews, not a full DICOM download endpoint that bypasses the ZIP gate. DICOM tab lists slices/UIDs/tags; an optional lightweight canvas phantom preview can be derived in RAM without adding a diagnostic viewer. HL7 and FHIR tabs show escaped formatted text. Failed candidates retain available previews and diagnostics; allow switching to the previous active result. No all-or-nothing hiding of successfully generated artifacts after a validation failure.

The single backend export predicate requires: existing unexpired dataset, every mandatory check PASSED, external aggregate in PASSED/WARNING/NOT VERIFIED, zero confirmed CT IOD failures, every required file complete, and ZIP prepared. Recompute this predicate at promotion and every download. Do not trust UI flags or cached eligibility. A missing mandatory result blocks export. Failed diagnostic candidates have no ZIP and cannot be promoted by a download request.

Use red Validation Failed for detected validation failures; green Required Checks Passed only with all required checks passed and no conformance veto. Show external WARNING/NOT VERIFIED separately. For NOT VERIFIED show: “Full DICOM CT IOD conformance has not been independently verified.” Include warnings and known limitations even when ZIP is allowed. Incomplete mandatory checks also block export with a clear explanation. System errors have safe user messages, no traceback, and retry; prior eligible results remain usable.

Build a deterministic-layout ZIP in BytesIO: `dicom/CT_001.dcm` through N, `hl7/ORM_O01.hl7`, `fhir/bundle.json`, `manifest.json`. Filenames never include user input. Check archive membership and CRC after preparation. Manifest contains schema version, dataset creation/expiry, synthetic-use notice, identifiers, file paths/sizes/SHA256 digests for the three artifact types, actual per-check/per-instance findings, external version/digest and coverage/limitations. Do not hash manifest into itself. No session token in manifest. Runtime TTL limits backend access, not the user's already downloaded ZIP.

## Data Model

All records below live in RAM except browser identifiers, the approved short-lived validator file, and bounded cleanup ownership metadata.

| Record | Fields and rules |
| --- | --- |
| GenerateRequest | patient name, MRN, DOB, sex; study description, accession, slice count; expected session revision and request ID |
| CanonicalScenario | patient {family,given,mrn,issuer,dob,sex}; order {placer_id,filler_id,accession,code,description}; created_at UTC; study/series/frame UIDs; ordered instances {index,sop_uid,position}; fixed geometry/pixel profile; UUIDs for FHIR resources |
| ArtifactSet | ordered DICOM byte streams, optional ORM bytes, optional FHIR bytes, completeness flags; partial artifacts permitted for failed diagnosis |
| CheckResult | check name, required flag, status, coverage, findings {standard,field/tag,reason,severity,confirmed_conformance_failure}; actual completion metadata |
| ExternalInstanceResult | SOP UID, invocation attempted, status, exit code, bounded stdout/stderr, parser/tool version, timeout/overflow/cleanup details, findings |
| DatasetRecord | dataset_id, owner session, created/expiry UTC and monotonic deadline, active/candidate/failed state, scenario, artifacts, validation report, optional ZIP, accounted bytes |
| SessionRecord | random token, revision, busy/request ID, active ID, latest failed ID, last activity; no account or long-term history |

Cross-format mappings are normative for the application profile in [mappings.md](mappings.md). They must be versioned with generated manifest schema and tested on serialized output. No database or permanent generated-content cache.

## Internal HTTP API

Same-origin JSON, session token header `X-MedTestGen-Session`, Cache-Control no-store on dataset/session responses. Safe error body `{code, message, fields?, request_id?}`; do not echo internal exception objects. Planned contracts:

| Route | Request and response |
| --- | --- |
| POST /api/session | Empty body; create random token, revision=0 and synthetic defaults; 201. Session cap => 503. |
| GET /api/session | Header token; active/failed IDs, revision, busy, expiry metadata. 404 after restart/unknown. |
| GET /api/patient/random | Header token; new synthetic patient form values, no dataset mutation. |
| POST /api/datasets | Header token, GenerateRequest; synchronous result once attempt completes: 201 promoted result or 200 failed-validation candidate with report and preserved active ID. 422 bad input, 409 stale/busy session, 503 capacity, 500 safe system error. |
| GET /api/datasets/{id} | Owner-scoped summary, metadata, HL7/FHIR previews, report, expiry and backend eligibility; 404 unknown/retired, 410 known expired. |
| GET /api/datasets/{id}/zip | Rechecked gate; application/zip for eligible result; 409 validation/incomplete gate, 404/410 availability. Never archive bytes on denial. |

If canvas preview is implemented, it uses a bounded owner-scoped preview endpoint under the same TTL and no-store rules, including failed-dataset diagnostic access. No networking to PACS, HL7 engines, or FHIR servers.

## File Structure

Planned files, not existing implementation:

```text
MedTestGen/
  medtestgen/
    __init__.py
    main.py                 # FastAPI startup, routes, cleanup lifecycle
    config.py               # Limits and qualified validator settings
    models.py               # Input, canonical scenario, reports
    scenario.py             # Synthetic defaults and shared identifiers
    store.py                # RAM ownership, TTL, revision and promotion
    pipeline.py             # Generate/check/package orchestration
    export.py               # Single eligibility predicate and ZIP/manifest
    generators/
      __init__.py
      dicom_ct.py           # CT profile, pixels, BytesIO serialization
      hl7_order.py          # Grouped v2.5.1 ORM
      fhir_bundle.py        # R4 models and internal references
    validation/
      __init__.py
      dicom_readback.py     # Independent bytes/readback/profile checks
      hl7.py                # Serialized-message validation
      fhir.py               # R4 structure and generated-profile rules
      consistency.py        # Extracted cross-format comparisons
      dciodvfy.py            # Bounded subprocess and diagnostic parser
      windows_temp.py      # Method A, Job Object and owned cleanup
    static/
      index.html            # Prefilled generator and results
      styles.css            # Responsive light styling
      app.js                # API, tabs, session restoration, revisions
  tests/
    conftest.py             # Synthetic fixtures, controllable clock
    test_ct.py
    test_hl7_fhir.py
    test_consistency.py
    test_validator.py       # Parser, real binary qualification, cleanup
    test_store.py           # TTL, atomic replacement and races
    test_api_export.py      # Direct-download gates and ZIP contents
    fixtures/validator/     # Text diagnostics only, no patient datasets
  devpost/
    learner-profile.md      # Private learning preferences
    scope.md                # Approved boundary
    prd.md                  # Approved behavior
    spec.md                 # This canonical blueprint
    mappings.md             # Exact local standards mapping profile
    checklist.md            # Created/reviewed in 5-build
    research/validator-poc/ # Historical planning experiment evidence
  requirements.txt          # Pinned runtime dependencies
  requirements-validator.txt # Optional independent validator pin
  requirements-dev.txt      # Runtime plus test tools
  README.md                 # PowerShell setup, demo, limitations
  .gitignore                # venv, caches, secrets and private profile
```

## External Services and Dependencies

No runtime remote service, API credential, rate limit or paid account. Package repositories are setup dependencies only. dciodvfy is a local executable with the exact invocation described above; its output is diagnostic text, not a hosted service response. Check licenses before redistribution. See Stack for library references and [Python tempfile](https://docs.python.org/3.10/library/tempfile.html), [subprocess](https://docs.python.org/3.10/library/subprocess.html), [Windows file sharing](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew), and [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) for the adapter boundaries.

## Verification Plan

These are required build checks, not completed application test results.

- Generate N=1..10 and test count, pixel type/length, geometry, unique/shared UIDs, mandatory tags and exact SOP/transfer syntax. Independently run dciodvfy on every instance in qualified integration runs. No validator skip can be reported as an integration pass.
- Valid positive CT fixture => external PASSED. Remove PixelSpacing => confirmed FAILED and direct ZIP denied. Warning-only diagnostic => WARNING. Missing executable and timeout => NOT VERIFIED. Exit 0 with recorded Error diagnostic => FAILED. Mixed study results must preserve any failure; unknown/truncated diagnostics cannot pass.
- Test method A cleanup after success, Python exception while a child is active, timeout, forced child termination, and parent death with a live child. Test lock interference, abandoned-root ownership checks, refusal to touch unrelated/reparse paths, and Python/version incompatibility. Record Windows 11 as untested until run there.
- Validate actual ORM hierarchy/required fields, FHIR R4 version, internal references, UIDs and counts. Mutate MRN, accession, UID, procedure or references in one output and require detection. Include Unicode, escaped separators, unknown sex and invalid inputs.
- Exercise every export gate independently via direct API, including missing files/results, FAILED external with otherwise passing checks, confirmed-failure flag with inconsistent aggregate, and allowed WARNING/NOT VERIFIED. Verify manifest matches previews and ZIP payloads and cannot falsely report completion.
- Fake-clock tests cover before/at/after TTL, cleanup, 410 versus 404, no TTL extension, restart, and expiration during generation. Failure/ZIP error must preserve previous active data; success retires it; only latest failed candidate remains. Race and lost-response tests verify server revision and browser reconciliation.
- Capacity tests retain old active data on rejected replacement and release reservations/buffers after errors. Measure memory during ten-slice generation and preview/download. Manually exercise desktop/mobile layout, keyboard, refresh, active/failed switching and safe errors.

Build order remains CT first, ORM second, FHIR third, consistency/export enforcement fourth, UI/ZIP journey fifth. Tests accompany each slice. dcentvfy and P1 features stay deferred. If CT correctness threatens the deadline, present evidence and request scope change before altering requirements.

## Important Failure Modes

- Validator transport/parser/lifecycle qualification fails: keep mandatory checks independent, show NOT VERIFIED with explicit limitation; confirmed IOD violations still block export. Never silently change transport.
- Candidate validation, ZIP preparation, capacity or system failure: preserve old unexpired active dataset and show diagnosis/retry. No traceback and no silent replacement.
- Dataset expires, backend restarts or browser loses response: reconcile session, distinguish known expiry where possible, and offer regeneration. Do not promise recovery of RAM after restart.

## What Was Simplified and Why

One CT study/series, geometric phantom and fixed acquisition profile make the three-standard consistency kernel demonstrable. Local one-process delivery, synchronous generation with bounded admission, and static UI avoid extra services. No accounts/history, clinical image simulation, external transport, bulk jobs, AI scenarios or optional standards expansion. These reflect approved scope; no CT-to-Secondary-Capture downgrade is allowed.

## Decisions and Open Issues

Approved: P0 scope/UX/export policy; RAM main storage with 30-minute TTL; atomic replacement; separate failed diagnostics; method A validation-file exception, no method B fallback; Windows 10 build 19045 baseline and optional later Windows 11 qualification.

Proposed as part of this final review: exact library pins, local loopback delivery, session token/revision protocol, memory/admission limits, Patient Name notation/input profile, the documented local standards mappings, and Job Object lifecycle supervision. These details are recommendations derived from the approved behavior, not claims of earlier learner approval.

The genuine technical uncertainty raised by the learner was whether the validator requires seekable input and whether Windows delete-on-close can coexist with an external reader. The [RAM transport PoC](research/validator-poc/REPORT.md) could not validate stdin input. The [temporary-file PoC](research/validator-poc/TEMPFILE-REPORT.md) demonstrated method A for one controlled CT instance and the documented cleanup scenarios. That evidence led to the learner's explicit exception approval. It does not prove absolute DICOM compatibility or that live-child parent death is handled by an application that has not been built.

Historical PoC reports remain unchanged as experiment records; their earlier “proposal only” wording is superseded for the selected exception by this specification and the learner's approval. Pending build qualifications include dependency imports, full CT attribute checklist, all-instance external runs, robust diagnostic parsing, live-child lifecycle cleanup and actual memory measurements. No unresolved product scope expansion is proposed.

Markdown is used for this review because no alternate review format has been selected. Full-document approval has been received. Proceed to the official 5-build workflow.

### Build-discovered internal correction

- hl7apy 1.3.5 treats ORM order-detail alternatives as simultaneously required. Narrow its reference choice to the approved OBR branch before validation; preserve group/field validation and add missing-OBR/procedure regressions. No stack, output or scope change.
