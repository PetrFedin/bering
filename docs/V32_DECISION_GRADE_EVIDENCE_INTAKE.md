# BERING V32 — acquisition of decision-grade originals, not another route forecast

**Checkpoint:** 10 November 2026. **Parent:** V31 Draft PR #30, exact head `3c26772a22945252df5f09328d96ca39160861bc`. **Decision:** INVESTMENT HOLD / P1–P3 HOLD. No edits to `main` or production. This source-readiness procedure is not a legal opinion, certified financial diligence, signed technical review or an approved investment case.

## 1. Public regulatory source check

- [Rosprirodnadzor official service notices](https://rpn.gov.ru/regions/cmu23/gov-services/gov-eco-exp/) contain an **opening** notice dated **31 August 2026**, order **878-О**, for the Stage 1 Magadan Marine Logistics Center environmental-expertise commission, 42 working days. This does **not establish a signed final positive or negative conclusion**. The source allows deadline extension and reporting of a legal period does not guarantee completion.
- [Glavgosexpertiza official announcement](https://egrz.ru/organisation/news/be268787-74bd-f111-80ff-00505634024e) dated **1 October 2026** reports **positive assessment of project documentation and engineering surveys** and **up to 150,000 TEU/year DESIGN**. The signed original and exact reviewed drawing schedule were not obtained. This is a **different expertise procedure** from the environmental one.
- [Earlier investment card](https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/) reports **30,000 TEU/year**, with no signed crosswalk reconciling that figure to 150,000. **Never sum** them or infer new cargo. Any comparison must preserve stage, revision, year, laden/empty, 20/40ft and the denominator of berth/container movements.
- Existing public copies of four PDF volumes from the V30 snapshot matched the owner's checksums. The Mac that retains those files was **offline at this V32 checkpoint**: they were not reread and their 2025 revision is **not** the confirmed certified October 2026 revision. The V30 geography discrepancy (Kola Bay/Murmansk in TBE 10.1, PDF pp. 12–13) remains **unresolved**, not demonstrated to be in the approved revision.
- Public-source search found **no authenticated final environmental order for this exact stage** in the sources checked by 10 Nov 2026. This is a search outcome, not proof of non-issuance. [Search and limitations receipt](../quality/V32_PUBLIC_EVIDENCE_SEARCH_20261110.json).

## 2. Twelve originals capable of changing the decision

The frozen [V32 evidence docket](../data/evidence/V32_DECISION_DOCUMENT_DOCKET.json) defines 12 **categories of documents**. It is not a claim there are 12 existing signed documents or 12 different customers.

| Docket category | Required proof | What it can answer |
| --- | --- | --- |
| Engineering original | Signed engineering opinion, number/date, approved document register | Did the designated authority approve these exact revisions? |
| Engineering revision crosswalk | Signed titles and differences 30k/150k | Do quoted capacities have the same scope and meaning? |
| Environmental final | Signed final expert opinion and approving order | Positive / negative / procedural status, scope and validity |
| TBE/geology correction | Corrected signed pages and expert tie-out | Was the observed Kola Bay/Murmansk text removed and were calculations affected? |
| Construction permit | Original permit, scope, issuing authority if issued | Can physical construction proceed legally? |
| Commissioning permit | Original commissioning/operating permit if issued | Is any part actually permitted to operate? |
| Port actual TEU 24m | Certified **real operations**, monthly physical units vs TEU | Historic throughput, not spare capacity or third-party project design |
| P1, P2, P3 paid shipment trails | Authorized 24-month OD, B/L, gate/receipt, invoice, credit note, bank match | Does each pilot represent paid cargo, real dates and a unique shipment? |
| Existing group baseline | Same period physical OD, client/asset mapping and margins | How much of pilot traffic merely displaces internal activity? |
| Independent investment QA | Independent engineering/financial reviewer sign-offs | Whether evidence supports a scenario and cash-flow model |

The docket is frozen **NOT_RECEIVED_NOT_ZERO**; no source originals or customer records are stored in the Git repository. It reflects a baseline as of 10 Nov and must not be retroactively edited when later evidence arrives. Subsequent signed arrivals create an independently reviewed later snapshot with their own immutable hashes and access controls.

## 3. Local private evidence admission (optional; no genuine bytes present in V32)

The [V32 gate](../scripts/v32_decision_evidence_gate.py) is executable without external data. Default result is `HOLD` with 12 required proof categories, **0 authenticated 24-month group-month slots out of 96**, cargo/margin/NPV **null**. It rejects fake values, duplicate IDs, illegal status promotion, altered prior SHA, and fabricated CI GREEN.

Only after legally obtained originals exist, an authorized custodian may place them under `local_private/v32_vault/` inside a full repo checkout. The directory is already excluded from Git by `.gitignore`. **Never upload passports, bank statements, customer lists, or unlicensed PDFs into Git history.** To check byte integrity, copy the empty [submission template](V32_PRIVATE_BYTES_SUBMISSION_TEMPLATE.json) into `local_private/v32_submission.json`, enumerate each original's stable *docket ID*, path relative to `local_private/v32_vault/`, and locally computed `sha256`. Then run:

```bash
python3 scripts/v32_decision_evidence_gate.py --repo .
python3 scripts/v32_decision_evidence_gate.py --repo . \
  --private-manifest local_private/v32_submission.json \
  --private-vault local_private/v32_vault
python3 -m unittest discover -s tests -p 'test_v32_*.py' -v
```

The gate **recomputes actual SHA-256 on local bytes**, checks file traversal, symlinks, length and docket IDs, but **never** converts hashes to a verified signature, an environmental conclusion, a permit, a paid invoice, an OD fact, or investment approval. It emits only aggregate counts, never customer names or original file paths. Even a `1/1` byte match results in `HOLD`, not `APPROVED`. Every true human/legal conclusion is a separate independent step.

For the synthetic intake test, one fake document is created within a temporary directory; test success **must not** be reported as a real received document. No actual outreach was sent.

## 4. Required transactional reconciliation

The commercial population remains 24 calendar months **October 2024 through September 2026** × P1/P2/P3/existing group = **96 group-month coverage slots**, not 96 shipments. **0/96 attested source-backed slots as recorded**; missing does not mean zero. Every received month needs source date, carrier/booking/waybill, route OD, physical ISO container and TEU unit, gate-out, terminal receipts, receiver acknowledgement, invoice/credit note, bank settlement, currency and VAT basis, original/source version, independent reviewer and a stable masked shipment key.

The incremental economic test must deduct existing-group displaced contribution margin and avoid counting the same physical container across multiple transport legs. No signed data supporting this calculation is presently in scope. Thus **paid new 40ft = null, incremental group CM = null, NPV = null**. Amounts must never be manufactured to satisfy a CI assertion. Independent banking and technical reviewers need the original signed source documents and formal authorization to access customer data.

## 5. GitHub Actions and independent one-SHA acceptance

V31 Draft PR #30 (head `3c26772a...`) hosted runs [regulatory QA #42736728458](https://github.com/PetrFedin/bering/actions/runs/42736728458) and [Research QA #42736728434](https://github.com/PetrFedin/bering/actions/runs/42736728434) failed before reported steps. Similar `runner_id=0` reports in [GitHub Community (8 Nov 2026)](https://github.com/orgs/community/discussions/212472) are anecdotal and **do not prove** the Bering root cause. The V31 check runs register annotations, but their texts were not accessible via existing GitHub tools. Billing, entitlement, account restrictions, runner provisioning and Actions settings must be inspected via an authorized GitHub UI and exact annotation text, not guessed. See [P0 issue #7](https://github.com/PetrFedin/bering/issues/7).

The V32 workflow runs the docket and full repository test suite on one checkout if hosted runner allocation becomes functional. A workflow file or `queued` status is **not green evidence**. Do not change GitHub plan, budget, private visibility or install a custom runner without a reason and owner control. `main` remains unchanged.

## 6. Immediate real-world actions (none represented as already completed)

1. Obtain final environmental-expertise **decision or a signed status reply** for the precise Stage 1 dossier, including order number, date, validity and whether examination was extended. [Open issue #31](https://github.com/PetrFedin/bering/issues/31).
2. Request signed engineering document register plus original approval and redline, explaining 30k/150k and the observed geography inconsistency. [Issues #26](https://github.com/PetrFedin/bering/issues/26), [#28](https://github.com/PetrFedin/bering/issues/28).
3. Identify authorized P1/P2/P3 data owners before sending [prepared but unsent letters](V30_OUTREACH_LETTER_TEMPLATES_NOT_SENT.md); agree NDA, secure transfer and independent access. Then obtain 96 monthly source-backed OD group slots and real bank evidence. [Pilot issue #4](https://github.com/PetrFedin/bering/issues/4).
4. Read actual GitHub job annotations and account billing/usage; fix that evidenced failure. Only then seek a real hosted `GREEN` on a fixed SHA.

**Investment conclusion V32:** Until genuine primary documents are available, the relevant unknowns remain unknown. No Bering investment return can honestly be certified. **DRAFT / INVESTMENT HOLD**.
