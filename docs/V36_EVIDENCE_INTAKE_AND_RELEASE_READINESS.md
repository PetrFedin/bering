# Bering V36 | Evidence-custody trail and honest release readiness

**Snapshot date:** 2026-11-16. **Parent:** V35 Draft PR #35, SHA `01e5061cd24259128fc9685c2d3d89cbe3120ed1`. **Posture:** research only / P1, P2, P3 HOLD / investment HOLD / no main changes.

## Executive finding

The controlling constraint is external, not computational. In the repository there are still no independently authenticated source documents proving paid incremental cargo, group contribution margin, commissioned competitor capacity, or an approved environmental conclusion for MLC Magadan Stage 1. The historical 24-month OD matrix has 96 **required group-month cells** (24 months x P1/P2/P3/existing group), with 0 source-attested cells in its last verified snapshot. Missing does **not** equal zero cargo. New paid 40ft, incremental margin and Bering NPV stay **null**, not zero. No investment approval follows from passing Python tests.

## What V36 actually adds

The [event-chain gate](../scripts/v36_evidence_intake_chain.py) and [empty template](../data/evidence/V36_EMPTY_PRIVATE_EVENT_LEDGER_TEMPLATE.json) offer a reproducible log of *claims that a custodian has received or reviewed source records*. Each recorded event includes a pseudonymous document token, source kind, content SHA-256 as reported by the custodian, event time, actor/role token, basis reference and preceding-event hash. The program recomputes canonical hashes and checks sequential numbering, chronology, permitted actions/roles, identity drift, duplicate receipts and changes after rejection.

A receipt must precede any claim of checking, outreach, content review or bank tie-out. A claimed independent review must come from an actor token different from the receiving custodian. An action requires a basis token. This is a consistency control, **not** real identity verification, signatory verification or independent banking verification.

Even with perfect chain links and a matching user-supplied terminal hash the only possible statuses are `SELF_REPORTED_CHAIN_UNANCHORED` / `SELF_REPORTED_CHAIN_MATCHES_SUPPLIED_ANCHOR`. The supplied hash is **not** a trusted external anchor: a malicious editor can replace the entire JSON and recompute all links. Independent time stamping and custody under a party not controlling the input are mandatory before relying on chronology. The gate **always** returns `investment_approved=false`, `bankable_revenue_approved=false`, `new_paid_40ft=null`, `group_incremental_contribution_rub=null`, `bering_npv_rub=null`.

The executable consumes only a JSON ledger stored under git-ignored `local_private/`; it does **not** read original source documents and must not be substituted for the V35 byte recomputation, issuer query or external review.

```bash
# Baseline: no private records, no implied cargo zeros
python3 scripts/v36_evidence_intake_chain.py --repo .

# After authorized parties lawfully provide actual records:
cp data/evidence/V36_EMPTY_PRIVATE_EVENT_LEDGER_TEMPLATE.json local_private/v36_event_ledger.json
# Add events via authorized custody process; never put real names/PII/bank details in Git.
python3 scripts/v36_evidence_intake_chain.py --repo . --ledger local_private/v36_event_ledger.json
# Optional user-provided previous terminal hash (does not verify external issuer):
python3 scripts/v36_evidence_intake_chain.py --repo . --ledger local_private/v36_event_ledger.json --expected-head-sha256 YOUR_EXPECTED_64_HEX_SHA

python3 -m unittest discover -s tests -p 'test_v36_*.py' -v
```

## Public regulatory verification: source controls, not invented conclusions

- The [investment card](https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/) was last updated **26 October 2026** and still states **30,000 TEU/year** as design capacity, not actual traffic or a Bering customer contract.
- [Glavgosexpertiza's 1 October 2026 announcement](https://egrz.ru/organisation/news/be268787-74bd-f111-80ff-00505634024e) reports a positive **project documentation / engineering surveys** review and up to **150,000 TEU/year** design for Stage 1. It does not contain in this evidence pack the signed drawing register or reconciliation of 30k and 150k. **Do not sum these design figures or turn them into Bering volumes.**
- The [Rosprirodnadzor official GEE register](https://rpn.gov.ru/activity/gee-registry/) explicitly says the public registry **may be incomplete** and directs users to an authorized territorial unit for up-to-date information. A web search cannot prove that a final environmental decision was or was not issued for this specific object. A conclusive answer requires the specific numbered signed decision / authorized status letter matched to the Stage 1 dossier. [Read-only source snapshot](../quality/V36_SOURCE_VERIFICATION_20261116.json).

## Release-train risk: eight staged Draft PRs, main not protected

The linked [read-only GitHub snapshot](../quality/V36_RELEASE_TRAIN_20261116.json) records Draft PRs #24 (V28), #27 (V29), #29 (V30), #30 (V31), #32 (V32), #33 (V33), #34 (V34), #35 (V35), each based on its predecessor's audit branch. Their `merged` flags were false at inspection. On 16 November 2026 `main` pointed to `e6dcc74cee46b327c399a1a0a5d4f8f282831d0f` and its `protected` flag was `false`. **No merge or branch protection update is performed in V36.** This is a material process risk: successful isolated module tests cannot prove a single release-candidate graph or full integration.

GitHub-hosted V35 jobs [#43764059354](https://github.com/PetrFedin/bering/actions/runs/43764059354) and [#43764059032](https://github.com/PetrFedin/bering/actions/runs/43764059032) ended `failure` without exposed steps and job log downloads returned `404 BlobNotFound` through the available connector; 1 and 2 annotations exist but their text could not be read. **Root cause remains UNKNOWN**, and no credible claim of GREEN is possible. [P0 issue #7](https://github.com/PetrFedin/bering/issues/7). The owner's Mac that retains four original MLC PDF copies is offline, so those bytes are not re-inspected here.

## Minimum documentary closure before model use

| Topic | Required authenticated original / review | Why decision cannot advance |
| --- | --- | --- |
| Approved engineering/project revision | Exact signed positive expert document, endorsed drawing schedule, 30k/150k crosswalk, correction history for Kola Bay/Murmansk in TBE 10.1 | Design editions cannot be reconciled from press notes |
| Environmental result | Numbered signed final GEE order/conclusion **or** signed pending/status confirmation, linked to Stage 1 | Start of review is not a result; registry warns of incomplete entries |
| Actual operating competitor capacity | Commissioning/operating permits and verified throughput, date and stage | Design capacity is not physical throughput |
| OD baseline | 24 months (2024-10 through 2026-09) x P1/P2/P3/group = 96 source-attested coverage cells | No evidence-backed historical denominator |
| Real paid pilot cargo | Signed waybill, gate/receiving, invoice/credit note, original bank settlement, issuer/owner confirmation and permissions | JSON arithmetic does not verify paid shipments |
| Group additionality | Same physical shipment ID and baseline before/after, displaced incumbent margin, customer permissions and an independent reviewer | Moving cargo between group sites does not create incremental group profit |
| Investment decision | Independently reviewed CAPEX/OPEX, financing, tax, FX, WACC, scenario risks, source-to-cashflow tie-out, hosted CI GREEN on one SHA | NPV / IRR are not bankable without source data |

**Owner actions still outstanding:** ascertain contacts/mandates, send previously prepared source requests only as an authorized representative, receive materials in a private controlled repository, authenticate issuer/signature, perform independent financial and engineering review, then assemble **one** release candidate with complete real CI and protected branch rules. None of those external acts are presented as completed in V36.

## Verification limits and next stage

V36 has 47 passing synthetic unit tests in a partial local container; V35 has 42 passing synthetic unit tests in a separate local directory (89 test methods in total, not a full repository regression). V35 unit tests are available locally, but the complete private GitHub checkout and GitHub-hosted job execution are not. Any claim that full V1-V36 CI or independent financial diligence is GREEN would be false. After the next signed documents arrive, create a new provenance snapshot rather than retroactively overwriting prior frozen evidence. **Release decision: HOLD.**
