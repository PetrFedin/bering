# BERING · V24 — physical 40ft identity, actual-movement evidence and V23 reconciliation

**Snapshot:** 2026-10-31.  
**Branch:** audit/v24-source-identity-linkage-20261031  
**Release:** DRAFT / LOCAL_SYNTHETIC_TESTS_PASS / REMOTE_CI_NOT_CERTIFIED / CARGO_AND_INVESTMENT_HOLD

## Why V24 exists

V23 prevents repeated economic shipment and physical-consignment *keys* across P1/P2/P3. A second record using completely unrelated internal keys can still describe the same physical cargo, especially when a P3 China→Vladivostok→Magadan movement is also represented as a P1 Vladivostok→Magadan leg.

V24 adds a **second, independent, physical-identity layer**. It does not claim that a valid container ID proves that a container actually moved, that payment was made, or that a cargo commitment is new.

## Source-controlled data contract

Inputs:

- **V23 bytes:** data/pilots/V23_cross_pilot_unverified.json (or a private, externally reviewed replacement). V24 pins **its exact SHA-256** rather than trusting a loose version label.
- **V24 physical identity register:** data/pilots/V24_identity_unverified.json. Required: schema_version=V24, same as_of, same group_id, pinned v23_input_sha256 and one identity record for every V23 economic shipment.
- **One V24 shipment identity record per V23 economic shipment:** pilot_id (P1/P2/P3), economic_shipment_id, physical_consignment_key, waybill_evidence_id matching the corresponding V23 source, plus the list of **each individual physical container**.
- **Each container record:** ISO 6346 freight-container number, claimed ISO size/type, B/L reference, actual loading/delivery dates, source IDs for the container movement event and actual delivery. The number of listed container units must equal V23 quantity_40ft.
- **Independent evidence index plus source files (outside Git for confidential material):** source SHA-256, relative path, reviewed_on, submitted_by, reviewed_by, VERIFIED marker; sender and reviewer must differ. Source text must independently be read by an authorized commercial reviewer; a hash alone establishes **byte identity only**.

### Primary standard references

- Bureau International des Containers (BIC): [Container Identification Number](https://www.bic-code.org/identification-number/) — owner code, U for freight containers, six-digit serial number and check digit.
- Hapag-Lloyd: [Container Specification, ISO size/type table](https://static-cf.hapag-lloyd.com/content/dam/website/downloads/press_and_media/publications/15211_Container_Specification_engl_Gesamt_web.pdf) — examples 42G1 and 45G1 for 40ft dry, and 42R1 and 45R1 for 40ft refrigerated.

V24 intentionally supports **only container-category U**, with documented dry codes **42G0, 42G1, 45G0, 45G1** for P1/P3, and refrigerated codes **42R1, 42R3, 45R1** for P2. This is a conservative research subset, **not** a claim that these four families cover every valid real-world container configuration. Non-standard or special equipment must go to manual review under a future explicit schema extension; never silently coerce 20ft, 45ft, open-top or flat-rack equipment to ordinary dry 40ft. Size/type values are **claims until validated against actual records**.

ISO 6346 check digits detect transcription errors; they do not independently establish that an owner is registered, a physical unit exists or the quoted size/type is truthful. BIC lookup and real terminal documentation are separate provenance tasks.

## Fail-closed controls

1. A changed original V23 JSON byte sequence is rejected, even if its parsed key-value content is equivalent.
2. Reject cross-system disagreement about pilot, economic_shipment_id, physical_consignment_key and waybill_evidence_id.
3. Reject missing, invalid or duplicate physical unit lists and a claimed number of units inconsistent with V23.
4. Validate the U-category freight-container ID and calculated ISO check digit; enforce the applicable 40ft dry/reefer subset on the declared ISO size/type field.
5. Normalize B/L references and reject **identical B/L+physical-container combinations** across any pilots or within one pilot.
6. If the *same physical container* appears on **overlapping time intervals** under different B/Ls, classify as AMBIGUOUS/HOLD (not automatically fraud); legitimate reuse on later non-overlapping dates is permitted.
7. Reject reuse of one evidence ID as two different physical container-movement events.
8. Invalid/future/reversed loading/delivery dates and a future source as_of date are INVALID. A source reviewed after as_of cannot be used as support for that historical release.
9. Hash and reviewer checks must pass for every claimed waybill, container movement and actual delivery. Missing files, path traversal, changed source bytes and identical sender/reviewer cause HOLD.
10. Default dataset explicitly carries **zero recorded shipments** because real data has not yet been obtained. This is missing evidence, **not demonstrated zero market demand**.

## Integrated commercial decision

Read-only controller: scripts/release_commercial_v24.py.

- Calls the **existing V23 full commercial controller**, which in turn runs all original P1/P2/P3 commercial gates and the anti-double-count group margin controller.
- Calls the V24 physical source identity engine on the **exact same V23 input path**.
- Either system INVALID → overall INVALID.
- Either system HOLD → overall HOLD.
- Only if **both** systems are REVIEW → overall REVIEW. No code path promotes REVIEW to PASS.
- All output flags bankable_revenue_approved, investment_approved and contracts_authenticated are always false.

Output SCREENING CM may be included only in REVIEW and still requires independent verification of actual commercial evidence and extra group contribution. Group FCFF, IRR and NPV are not certified by this gate.

## Reproduce

~~~bash
python -m unittest discover -s tests -p 'test_shipment_identity_v24.py' -v
python -m unittest discover -s tests -p 'test_release_commercial_v24.py' -v

python scripts/shipment_identity_v24.py \
  --v23 data/pilots/V23_cross_pilot_unverified.json \
  --identities data/pilots/V24_identity_unverified.json \
  --out v24_identity_receipt.json

python scripts/release_commercial_v24.py --repo . --out v24_combined_receipt.json
~~~

With actual authorized documents, use **both** --evidence-index and --evidence-dir, plus --cross-input and --identity-input to point to mutually pinned private data. These paths are never stored in repository examples. Set --require-review for fail-closed exit 3 on HOLD (2 on INVALID); REVIEW still does not approve investment.

## Local QA (exact scope)

Python 3.11-compatible modules, executed **locally** with Python 3.13.5:

- **40/40** physical-identification tests with synthetic test-only container numbers and text files: check-digit failures, 20ft imposters, reefer/dry mismatch, cross-pilot B/L+container duplication, same-container interval overlap, allowed non-overlapping reuse, exact V23 fingerprint, evidence corruption and reviewer separation, incorrect quantities and time periods.
- **14/14** combined-controller interaction tests with **mocked subprocess results**: BOTH HOLD, asymmetric gates, INVALID rejection, true flags forbidden, missing sources, bad process results, and shared V23 file path.
- **54/54 total PASS** in an isolated local sandbox. This is not a GitHub-hosted run, a real waybill test or a complete integration E2E with actual consignments.
- Locally executed research-only V23→V24 identity baseline: HOLD, 0 **recorded** V23 shipments, 0 recorded physical container identities, two explicit missing-evidence findings; no bankable cargo.
- Five local source and test files were compared by exact Git object SHA against the version committed to GitHub.

## Remaining obstacles and release gate

- Original V8–V15.2 XLSX/DOCX source files expected by V20/V21 are **not in the remote GitHub tree**. The underlying original archive is still inaccessible.
- GitHub-hosted runner for V22/V23 repeatedly failed before any step. V24 CI GREEN on a pinned commit has **not** been established.
- There are no independently authenticated real P1/P2/P3 waybills, container movements, delivery receipts, paid invoices or reconciled 24-month OD records.
- V24 does not parse the actual content of waybills or compare carrier/terminal back-office exports; it compares **declared source IDs, raw file digests and timestamps**. The real physical/custody mapping requires external authorization and review.
- Synthetic ISO owner prefixes are **not** claims about BIC registration. Do not present generated IDs as operating containers.
- Local actual tests do **not** replace continuous CI, external independent reviewer, or investment diligence.

Next mandatory evidence milestone: obtain original signed/authorized documents and multi-terminal 24-month OD baseline; independently reconcile the physical B/L, container no., actual service legs, event chronology, counterparty, price and payment; verify incremental GROUP contribution versus existing terminals. Until these are documented: P1/P2/P3 **HOLD**, tunnel **HOLD**, no investment or production approval.
