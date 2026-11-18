## R21 — каталог полученных оригинальных файлов ММТП (18.11.2026)

- [Срез источников и SHA-256](R21_OFFICIAL_SOURCE_INTAKE_20261118.json), [S227–S234](SOURCE_REGISTRY_R21_20261118.csv), [отчёт](../../docs/research/OPEN_SOURCES_RESEARCH_R21_20261118.md).
- Четыре оригинальных файла, полученных с сайта ПАО ММТП: FY2024 `.xls`, FY2025 `.xls`, 2026-H1 `.xls` и инфраструктурный `.xlsx`. Содержимое оригинальных XLS **не перевалидировано по ячейкам**; на FY2024 парсер сообщил `Workbook is encrypted`. Байтовые хеши 2024/2025 совпали с историческим CSV; исходные коммерческие файлы не загружались в публичный репозиторий.
- [R21 контрольная процедура](../../scripts/r21_source_integrity_and_freight_scope.py) допускает сравнение локальных байтов только при законном доступе; цена FESCO и доступная мощность в 2026 = `null`; инвестиционный HOLD.

## R20 — сверка показателей ММТП и тарифной базы (17.11.2026)

- [S216–S226: реестр источников](SOURCE_REGISTRY_R20_20261117.csv) и [отчёт](../../docs/research/OPEN_SOURCES_RESEARCH_R20_20261117.md) с ограничениями доступа и сопоставимости.
- [`MMTP_MP1_MONTHLY_SERIES_2024-01_2026-09.csv`](MMTP_MP1_MONTHLY_SERIES_2024-01_2026-09.csv) — существовавшие 33 месячные строки; R20 пересчитал их без изменения оригинального Git blob `3b6bee1a1874dea96537b0406125154233ff5a51`, **а не повторно извлёк оригинальные XLS**.
- [QA R20](../../quality/R20_COMPUTED_QA.json) — 2025 по МП-1 84 294 TEU, вторичный всего-порт 84 300 TEU; 2024 расхождение −2336 TEU, тонны других публикаций пока не согласованы. Идентификатор группы P1–P3 ≠ 3 новых сделки, экономическая дополнительность неизвестна.

# Публичные и производные данные Bering Corridor

Актуально на **17.11.2026**. Основной содержательный индекс — [исследования R1–R18](../../docs/research/README.md) плюс [R19](../../docs/research/OPEN_SOURCES_RESEARCH_R19_20261117.md). Все расчёты с типом `[модель]` являются воспроизводимой аналитикой, а не банковскими входами.

## Главные реестры

| Файл | Содержание |
|---|---|
| `INVESTMENT_PROJECTS_MAGADAN_REGISTRY.csv` | Единый реестр IP01–IP33 и предложений N1–N8; обновляется с датированными пометками раундов |
| `BERING_CORRIDOR_LINKED_PROJECTS.csv` | Связанные проекты B01–B21 и инициативы хаба H1–H6 |
| `SOURCE_REGISTRY_20261116.csv` и `SOURCE_REGISTRY_R2…R19` | Источники S01–S215 по раундам |
| `MODEL_CALCULATIONS_R10…R19` | Формулы, входы, единицы и результаты C01–C51 |

## Реестры источников по раундам

| Раунд | Файл | ID |
|---|---|---|
| R1 | `SOURCE_REGISTRY_20261116.csv` | S01–S29 |
| R2 | `SOURCE_REGISTRY_R2_20261116.csv` | S30–S48 |
| R3 | `SOURCE_REGISTRY_R3_20261116.csv` | S49–S68 |
| R4 | `SOURCE_REGISTRY_R4_20261116.csv` | S69–S83 |
| R5 | `SOURCE_REGISTRY_R5_20261116.csv` | S84–S93 |
| R6 | `SOURCE_REGISTRY_R6_20261116.csv` | S94–S105 |
| R7 | `SOURCE_REGISTRY_R7_20261116.csv` | S106–S114 |
| R8 | `SOURCE_REGISTRY_R8_20261116.csv` | S115–S122 |
| R9 | `SOURCE_REGISTRY_R9_20261116.csv` | S123–S133 |
| R10 | `SOURCE_REGISTRY_R10_20261116.csv` | S134–S138 |
| R11 | `SOURCE_REGISTRY_R11_20261116.csv` | S139–S152 |
| R12 | `SOURCE_REGISTRY_R12_20261116.csv` | S153–S163 |
| R13 | `SOURCE_REGISTRY_R13_20261116.csv` | S164–S170 |
| R14 | `SOURCE_REGISTRY_R14_20261116.csv` | S171–S181 |
| R15 | `SOURCE_REGISTRY_R15_20261116.csv` | S182–S187 |
| R16 | `SOURCE_REGISTRY_R16_20261117.csv` | S188–S194 |
| R17 | `SOURCE_REGISTRY_R17_20261117.csv` | S195–S202 |
| R18 | `SOURCE_REGISTRY_R18_20261117.csv` | S203–S211 |
| R19 | `SOURCE_REGISTRY_R19_20261117.csv` | S212–S215 |

## Расчёты

- R10: `MODEL_CALCULATIONS_R10.csv` — C01–C14.
- R11: `MODEL_CALCULATIONS_R11.csv` — C15–C20.
- R12: `MODEL_CALCULATIONS_R12.csv` — C21–C24.
- R13: `MODEL_CALCULATIONS_R13.csv` — C25–C28.
- R14: `MODEL_CALCULATIONS_R14.csv` — C29–C31.
- R15: `MODEL_CALCULATIONS_R15.csv` — C32–C35.
- R16: `MODEL_CALCULATIONS_R16.csv` — C36–C37.
- R17: `MODEL_CALCULATIONS_R17.csv` — C38–C40.
- R18: `MODEL_CALCULATIONS_R18.csv` — C41–C43.
- R19: `MODEL_CALCULATIONS_R19.csv` — C44–C51; матрица периметров `MAGADAN_ENERGY_PERIMETER_MATRIX_R19.csv`.

## Энергетика и гидрология

| Файл | Назначение |
|---|---|
| `KOLYMA_ENERGY_DATACENTER_FACTS.csv` | Первичный контур каскада и ЦОД, R7 |
| `KOLYMA_HPP_WINTER_MONTHLY_PROFILE.csv` | Помесячный зимний профиль по 10 расчётным годам, R15 |
| `KOLYMA_HPP_ANNUAL_OUTPUT_CURVE.csv` | 85 обеспеченностей: зима/лето/год, R18 |
| `KOLYMA_HPP_POWER_DURATION_CURVES.csv` | 85 обеспеченностей × 22 интервала года, R18 |
| `KOLYMA_HPP_ANNUAL_OUTPUT_2007_2025.csv` | Фактический ряд; 2023 = `null`, R18 |
| `ENERGY_SYSTEM_AND_MLC_FACTS_R9.csv` | Балансы СО ЕЭС и факты МЛЦ, R9 |
| `MAGADAN_ENERGY_PERIMETER_MATRIX_R19.csv` | Явная матрица периметров СИиПР/генсхема/приказ №287/НПУ, R19 |

Для двух летних строк 8,1 % и 10,5 % в массиве мощностей R18 отсутствующие значения записаны как `null`, не как ноль и не интерполяция. Годовая кривая и помесячные/декадные мощности — разные таблицы одного первичного документа; расхождения с приложениями №11–12 не скрываются.

## Порт, флот, тарифы и макроэкономика

- `CARRIER_TARIFFS_VVO_MAGADAN_2026.csv` — опубликованные тарифы перевозчиков.
- `LINE_FLEET_SCHEDULES_VVO_MAGADAN_2026.csv` — флот и расписания.
- `MMTP_STEVEDORE_TARIFFS_2026.csv` — стивидорный прейскурант.
- `MMTP_FINANCIALS_2019_2025.csv` — финансовый ряд ММТП.
- `MMTP_MP1_MONTHLY_SERIES_2024-01_2026-09.csv` — помесячный публичный ряд.
- `MMTP_PRIMARY_INTAKE_RECEIPT_20261116.json` — акт первичной приёмки.
- `MAGADAN_PORT_ANNUAL_SERIES.csv` — годовой ряд порта.
- `MAGADAN_OBLAST_ECONOMY_SERIES.csv` — макроэкономический ряд области.
- `MAGADAN_TELECOM_TARIFF_FACTS.csv` — связность и тарифный контур.

## Мониторинг и ранние evidence/QA-реестры

- `MONITORED_SOURCES.json` — источники для контроля изменений; работа automation зависит от issue #7.
- V26: `V26_PUBLIC_SOURCE_REGISTER.json`.
- V27: `V27_KASCO_LIST_RATE_20261101.json`, `V27_PORT_MONTHLY_UNVERIFIED.json`, `V27_PRIMARY_SOURCE_REGISTER.json`.
- V28: `V28_MAGADAN_MARKET_PERIMETER.json`, `V28_MLC_PRIMARY_PROJECT_FILE_MANIFEST.json`.
- V29: `V29_COMPETITOR_TIMELINE_CLAIMS.json`.
- V30: `V30_PDF_SOURCE_FINDINGS_20261109.json`, `V30_PUBLIC_PDF_BYTE_AUDIT_20261109.json`.
- V31: `V31_REGULATORY_STAGE_CHAIN.json`.

Эти ранние файлы относятся к технической/evidence-истории и не заменяют текущие источники S01–S215.

## Правила чтения

1. `null` означает отсутствие проверенного значения, а не ноль.
2. Публичный тариф ≠ котировка ≠ контракт ≠ оплаченная перевозка.
3. Проектная мощность ≠ фактический груз или фактическая выработка.
4. Разные периметры, годы, валюты, НДС, тонны и TEU не складывать без сверки.
5. В коммерческом контуре P1–P3 — пилоты; в исследованиях R1–R19 P1–P4 — инвестиционные периметры.
6. `INVESTMENT_PROJECTS_MAGADAN_REGISTRY.csv` исторически содержит неэкранированные запятые в `notes`. Для строгого машинного разбора требуется отдельная миграция схемы; скрытое переформатирование единого исторического файла не выполнялось.
