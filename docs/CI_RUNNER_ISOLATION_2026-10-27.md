# Bering technical admission — runner isolation receipt

Date: 2026-10-27 (Riga time); **status: BLOCKED BEFORE EXECUTION**.

## Verified repository history

- Main latest confirmed: `e6dcc74cee46b327c399a1a0a5d4f8f282831d0f`.
- Research draft PRs: [#8](https://github.com/PetrFedin/bering/pull/8) and [#9](https://github.com/PetrFedin/bering/pull/9) remain unmerged.
- V18 main QA run: https://github.com/PetrFedin/bering/actions/runs/40536340370 — FAILED, steps empty, runner_id=0.
- **Independent clean runner probe** at SHA `11704d07cbe534bb650209c9e34e0ffc36720798`, branch `ci/runner-probe-20261027`: https://github.com/PetrFedin/bering/actions/runs/40539570411 — **FAILED with steps=[] and runner_id=0**.
- The probe uses `ubuntu-24.04`, has no checkout, no third-party actions, no project dependencies and one `echo`/Python version step. Failure therefore happens before any repository test can execute.

## Scope of conclusion

The clean failure rules out a **repository Python test / spreadsheet formula error as the direct cause of this particular failure**. It does **not** uniquely identify the upstream root cause: GitHub Actions billing/minutes, account/repository policies, available hosted runners, disabled Actions setting or platform-level admission can have similar symptoms. The connector cannot retrieve runner step logs or settings.

## Required operator inspection (no secrets shared in chat)

1. Open [isolated probe run](https://github.com/PetrFedin/bering/actions/runs/40539570411) in authenticated GitHub; inspect any pre-run check annotations or account notifications.
2. Repository **Settings → Actions → General**: confirm allowed Actions and workflow execution policies.
3. Account **Settings → Billing and licensing → Actions**: inspect hosted-runner eligibility/usage/payment constraints for private repository.
4. If policy has disabled hosted runners, resolve permission/administration issue. No paid resources are authorized by this project unless separately approved.
5. After settings remediation rerun minimal probe, capture **actual completed steps** and GREEN conclusion; only then rerun the full Research QA on the same SHA.
6. Protect main only after verifying CI branch rules and independent human review are functional.

## Local source verification (not equivalent to GitHub execution)

- Original recovery ZIP `Bering_Full_Research_Binary_Archive_2026-10-26.zip`: ZIP integrity PASS.
- **31/31** SHA-256 manifest entries verified against decompressed source files.
- Local V18 commercial evidence tests: **20/20 PASS**.
- Local V17 quality/risk unit tests: **7/7 PASS**.
- V14.1 → V15.2 workbook read-only XML check: 72 sheets, 493 candidate formulas, 35 blank formula result caches; exactly one package XML member changed; 3 added risk formulas.
- No full recalculation of all 493 formulas and no real cargo contract/waybill verification performed.
- **Original source XLSX/DOCX bytes remain outside GitHub**, held as separate ZIP; GitHub text extractions are not original spreadsheets.

## Release consequence

**TECHNICAL_ADMISSION = BLOCKED**. No PR merge, official research quality score 9/10, commercial bankability, or production-like certification is justified by these local tests alone.
