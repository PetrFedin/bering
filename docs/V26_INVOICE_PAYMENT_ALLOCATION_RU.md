# Bering Corridor V26 - batch invoices and bank settlement allocation

2026-10-31 | DRAFT RESEARCH | based on V25 | PAID CARGO NOT PROVEN | INVESTMENT HOLD

## Why the previous model was too restrictive

V25 modelled one 40-foot physical consignment per row and considered repeated original invoice/payment evidence IDs invalid among shipment records. In real operations, an invoice can bill multiple physical containers, and one bank transfer or bank statement may cover several invoice balances. Rejecting every repeated invoice evidence ID can cause false rejections; alternatively counting the same statement amount once for each container inflates sales. Both are analytically wrong. These are permitted document relationships, NOT evidence that the project's real counterparties have provided such documents.

V26 builds a **separate, fail-closed invoice/settlement allocation contract**. The new engine is a mandatory parallel admission check, NOT yet a replacement for the existing V25 cargo/source matching. Batch payment integration into V25 remains an explicit unresolved task.

Data grain:
- Physical container: unique 64-char pseudonymous physical consignment key, matched to the exact set of keys in the same-date/same-group V25 manifest.
- Invoice: unique invoice id, dated original, NET RUB, VAT RUB and GROSS RUB as independently supplied values. No assumed VAT rate, no implicit currency conversion. Each invoice has one or more allocation lines to physical containers, with exact net + VAT = gross per line and in aggregate.
- Bank transaction: unique transaction ID and date, verified bank source bytes, GROSS settled RUB, allocation rows to one or more invoice ids. One invoice may be paid by several independent transactions; one transaction may pay multiple invoices. Sum of bank amounts must equal invoice allocations; no overpayments, silent residuals or double-posting. Shared evidence of a bank statement across several bank transactions is permitted, but underlying individual bank transaction identities must be independently verified by an authorized reviewer.
- Refund/credit note rules are not implemented. A declared refund forces HOLD until separately modelled and reconciled.
- Evidence original bytes SHA-256, indexed source paths, reviewer names and review dates follow the V25 evidence guard. This is *byte-review*, not verification of the bank's digital signature or its payment-rail API.

Status:
- INVALID for duplicate invoice/transaction ID, wrong net/VAT/gross, overpayment, unknown physical key/invoice, cross-group/as-of join, future dates, wrong currency, invalid units, extra fractional kopeks.
- HOLD for absent original documents, missing V25 consignment match, incomplete settlement, undeclared refund/credit note accounting or missing independent reviewer/source bytes.
- REVIEW_ONLY for full mechanical reconciliation, never bankable revenue recognition. Any matched gross amounts are screening observations, not contractual new demand or incremental group contribution. `group_incremental_cm_rub=null` and investment approval remains false.

## Only synthetic check values are available

30 new unit tests locally PASS using deliberately fabricated evidence and amounts. Example: batch invoice A bills two invented container rows for 330 RUB gross; invoice B bills a third for 55 RUB gross. Fake transaction A pays 200; fake transaction B pays 185 allocated across invoice A (130) and B (55). Two invoices, two bank transactions and three physical keys reconcile at **385 fictitious RUB gross**, which is NOT a real port tariff, invoice, payment, VAT rate, forecast or margin. V25's pre-existing 28 synthetic source-join tests are independent.

No real invoices, bank records, 24-month customer history, new cargo proof or original container crosswalk has been provided to this repository. The canonical V26 input keeps invoices/payments empty, which means **UNKNOWN paid cargo**, not an observed zero. The CLI returns HOLD with all quantitative output NULL.

## Public operating context (separate from real paid units)

FESCO press release 19 October 2026: Vladivostok Sea Commercial Port processed >674k TEU Jan-Sep 2026 (+15% YoY) and import throughput rose 33%. https://www.fesco.ru/ru/press-center/news/konteynerooborot-vmtp-vyros-na-15-za-devyat-mesyatsev-2026-goda/

PАО Magadan Marine Commercial Port discloses MP-1 / MP-2 reporting XLS for nine months of 2026, published 07 October 2026; official files are listed but actual XLS contents and source totals are not verified by this version. https://magadanport.ru/raskrytie-informacii/

These are not P1/P2/P3 40ft incremental origin-destination shipments. Port/terminal throughput, capacity, group revenue, and physically new paid containers must be kept on separate accounting lines.

## Remaining unproved route to real forecast

1. Obtain valid data-use permission, authentic B/L, bank statement/payment extract, invoices, tax basis and settlement snapshots for each physical container / batch; verify shared source event identifiers against real originals.
2. Add an evidence-backed consignment-to-invoice-to-bank graph accepted **consistently by both V25 and V26**. V25 currently expects unique invoice/payment evidence references per container, whereas V26 correctly allows shared batches; until unified, source-level financial E2E is HOLD.
3. Map historical 24-month incumbent terminal OD and lost group CM; prevent P3 leg duplication as P1 and shared fixed/risk cost double charging. Determine NEW vs DIVERTED by actual clients and original contracts.
4. Reconcile the V25/V26 source ground truth to exact 36-month observed route counts admitted to V24. Only then compute a fixed historically held-out forecast error; no synthetic forecast claims.
5. Finish public tariff/legal checks, realistic D2D ex-VAT, customs, reefer energy, service disruptions, CAPEX, OPEX, capital lockup, FCFF/NPV and signed independent reviews. No merging to main and no real settlement or production changes.

Local: 30/30 new synthetics PASS. Remote GitHub hosted CI GREEN not certified. Source contracts and bank permissions HOLD. INVESTMENT HOLD.