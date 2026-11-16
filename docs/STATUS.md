# Evidence-first project status

## Актуальный статус — 17.11.2026

**Режим: RESEARCH ONLY. Письма и RFQ не отправляются. Коммерческие пилоты и инвестиционные периметры P1–P3 остаются HOLD; `bankable_revenue_approved = False`.**

Текущая исследовательская серия доведена до **R18** и полностью записана в `main`:

- [индекс R1–R18](research/README.md);
- [документ R18](research/OPEN_SOURCES_RESEARCH_R18_20261117.md);
- источники **S01–S211**, расчёты **C01–C43**;
- единый реестр **IP01–IP33 + N1–N8**;
- полногодовые кривые обеспеченности Колымской ГЭС и фактический ряд 2007–2025;
- [каталог публичных данных](../data/public/README.md).

Ключевое ограничение ЦОД подтверждено первичными документами: при избытке установленной мощности критичны зимняя энергия и конец зимы. Аркагалинская ГРЭС (IP33) дополняет пакет N4, но даже полная сезонная загрузка очереди 165 МВт оставляет модельный остаток −122,48 млн кВт·ч в 95%-год с ЦОД 150 МВт [C41]. Это не банковская модель и не инвестиционный допуск.

На момент аудита 17.11.2026 открытых PR нет, `main` защищён. GitHub Actions и связанные ручные действия владельца по issue #7 этим исследованием не закрыты. Исторические ветки и файлы не удаляются.

**Различение обозначений:** в коммерческом контуре P1–P3 — три транспортных пилота; в открытых исследованиях R1–R18 P1–P4 — четыре инвестиционных периметра. Эти шкалы не смешивать.

## Исторический снимок — 26.10.2026

| Perimeter | Decision now | Evidence needed |
|---|---|---|
| Magadan logistics hub, standalone | **Investigate / controlled pilots** | D2D quotes, container histories, genuine incremental volumes, available port slots, expansion CAPEX/OPEX, operating data |
| Yakutia–Magadan railway | **Pre-feasibility only** | Funded feasibility, alignment, construction quantities, permafrost, power, freight contracts, alternatives |
| Magadan–Chukotka rail | **Concept / HOLD** | Route alternatives, geology, energy, logistics, freight evidence, regulatory regime |
| Bering subsea crossing | **HOLD** | Boreholes, surveys, fire and rescue, tunnels/RAMS, international approvals, US/Canada and Russia connections, long-term binding cargo |
| China–USA transit via Magadan | **Hypothesis / HOLD** | Origin-destination cargo, full tariff and time vs fast sea, US/RU/CN legal and tariff analysis, signed commitments |

## V14 acceptance ledger

- P1 Владивосток → Магадан / 40ft dry: published carrier rates available, complete D2D and new cargo evidence missing.
- P2 Владивосток → Магадан / 40ft refrigerated: published carrier rate available, cold-chain costs, actual evidence and new demand missing.
- P3 Shanghai/China → Vladivostok → Magadan: schedules available, no comparable contracted full service cost or signed shipper demand.
- RFQ requests: **15 prepared drafts; not sent**.
- Shipments with independently established incrementality: **none admitted**.
- Investment model should carry **no approved incremental freight revenue from these 3 pilots**.

## Critical open reconciliation

One investment project for a Magadan logistics center is described as 30,000 TEU/year in an earlier investor card and up to 150,000 TEU/year in later reported project review. Capacity, budget and operational startup are **not comparable until planning basis and stages are reconciled**. Neither capacity figure is actual cargo.

## Review rule

A published rate != carrier quote != contract != paid shipment != recurring incremental cargo. Each arrow requires independent documents. Avoid treating absence of evidence as proof that a project cannot succeed.
