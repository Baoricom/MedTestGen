# MedTestGen — Cross-Standard Mapping Profile

Status: approved with the final technical specification. This is a local synthetic integration-test profile, not a claim of universal HL7 receiver compatibility. All values originate from the same immutable canonical scenario. Compare decoded values, not differently escaped serialized text.

## Patient and Order

| Canonical value | DICOM | HL7 v2.5.1 ORM | FHIR R4 |
| --- | --- | --- | --- |
| MRN | PatientID (0010,0020) | PID-3.1, authority PID-3.4 MEDTESTGEN, PID-3.5 MR | Patient.identifier: system https://medtestgen.example/identifier/mrn, value MRN |
| Issuer | IssuerOfPatientID (0010,0021) MEDTESTGEN | PID-3.4 | Identifier system above defines the local authority |
| Name | PatientName Family^Given | PID-5.1 family, PID-5.2 given | Patient.name.family and given array; text retains display form |
| Birth date | PatientBirthDate YYYYMMDD | PID-7 YYYYMMDD | Patient.birthDate YYYY-MM-DD |
| Sex | M/F/O; empty value for unknown | PID-8 M/F/O/U | male/female/other/unknown |
| Accession | AccessionNumber (0008,0050) | OBR-18 (chosen local radiology convention) | ServiceRequest.identifier and ImagingStudy.identifier, system https://medtestgen.example/identifier/accession |
| Placer order ID | Not forced into a DICOM study tag | ORC-2 and OBR-2: ID with namespace MEDTESTGEN | ServiceRequest.identifier, system https://medtestgen.example/identifier/placer-order |
| Filler order ID | Accession is the chosen local filler identifier | ORC-3 and OBR-3: accession with namespace MEDTESTGEN | ServiceRequest.identifier, system https://medtestgen.example/identifier/filler-order |
| Procedure | StudyDescription, BodyPartExamined HEAD, Modality CT | OBR-4: CT_SYNTHETIC^description^99MEDTESTGEN | ServiceRequest.code.coding: system https://medtestgen.example/codes/procedure, code CT_SYNTHETIC, display description |
| Description | StudyDescription (0008,1030) | OBR-4.2 | ServiceRequest.code.text and ImagingStudy.description |
| Scenario timestamp | StudyDate/Time, TimezoneOffsetFromUTC +0000 | MSH-7 and ORC-9 UTC HL7 timestamp | ServiceRequest.authoredOn and ImagingStudy.started, ISO 8601 UTC |

Accession, filler order number and placer order number are distinct concepts even when this profile deliberately gives accession and filler the same value. OBR-18 is not a universal accession mandate. No claim of IHE Scheduled Workflow conformance. Patient-sex Unknown does not become invalid DICOM value U; consistency uses the mapping above. Unicode uses DICOM SpecificCharacterSet ISO_IR 192, HL7 UTF-8 with MSH-18 UNICODE UTF-8, and JSON UTF-8. Escape HL7 separators and reject prohibited DICOM separators/control characters rather than corrupting structure.

## Study, Series and Instances

| Canonical value | DICOM | FHIR R4 ImagingStudy |
| --- | --- | --- |
| Study UID | StudyInstanceUID (0020,000D) | identifier system urn:dicom:uid, value urn:oid:<StudyUID> |
| Series UID | SeriesInstanceUID (0020,000E) | series[0].uid, bare dotted UID |
| SOP Instance UID | SOPInstanceUID (0008,0018), matching file meta | series[0].instance[i].uid, bare dotted UID |
| CT SOP Class | SOPClassUID (0008,0016), matching file meta | instance[i].sopClass system urn:ietf:rfc:3986, code urn:oid:1.2.840.10008.5.1.4.1.1.2 |
| Modality CT | Modality (0008,0060) | modality and series.modality Coding system http://dicom.nema.org/resources/ontology/DCM, code CT |
| Series/instance numbers | SeriesNumber 1; InstanceNumber 1..N | series.number 1, instance.number 1..N |
| Count N | Actual N serialized instances | numberOfSeries 1, numberOfInstances N, series.numberOfInstances N, exactly N instance entries |
| Frame of Reference UID | FrameOfReferenceUID (0020,0052), common across slices | No forced field or custom extension in MVP; preserved in manifest/DICOM metadata |

HL7 ORM does not receive fabricated UID fields or custom Z segments. Study/series/SOP consistency is checked between DICOM and FHIR wherever applicable. Frame of Reference consistency is checked across DICOM slices.

## Bundle References and Independent Checks

Bundle.type=collection; exactly three entries. Resource IDs are UUIDs, and fullUrl is urn:uuid:<resource-id>. ServiceRequest.subject and ImagingStudy.subject equal Patient.fullUrl. ImagingStudy.basedOn references ServiceRequest.fullUrl. Verify uniqueness and type-correct resolution by reading serialized Bundle entries. UUID resource IDs are not DICOM UIDs.

Extract identifiers using their system/authority, not array position. Read every DICOM instance, parse the emitted HL7 message and emitted JSON. Check exact MRN/accession/order/description values after decoding, normalized dates/sex/name, study and series UID equality, SOP UID set equality and uniqueness, numeric instance ordering and count. Record exact offending field/path without inventing a tag absent from diagnostics.

## Primary References

- [FHIR R4 ImagingStudy and DICOM mappings](https://hl7.org/fhir/R4/imagingstudy.html)
- [FHIR R4 ServiceRequest](https://hl7.org/fhir/R4/servicerequest.html)
- [FHIR R4 Patient](https://hl7.org/fhir/R4/patient.html)
- [FHIR R4 Bundle](https://hl7.org/fhir/R4/bundle.html)
- [HL7 v2.5.1 Chapter 4 order fields](https://hl7.eu/HL7v2x/v251/std251/ch04.html)
- [DICOM CT Image IOD module table](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_A.3.3.html)
