# Archived source extraction: archive/versions/V07/V7_research_notes.md

Extraction of the original file_00000000b5d081f4aed876e8e65c6c97. **Not the original binary document**. Read source and file manifest before citing.

# Берингов пролив: V7 — проверяемая исследовательская база
Дата: 23 октября 2026 года. Исследование не является утверждённым ТЭО, проектной сметой или инвестиционной рекомендацией.

## Что изменилось по сравнению с V6

- Сохранены 81 лист предыдущей модели и все значения/формулы; добавлено 18 аналитических листов (всего 99).
- Отдельный сетевой реестр Мохэ–Найба, Магадан–Чукотка, американских подходов и трансграничного стыка.
- Введены 50-летний коммерческий DCF, стресс-расчёт исторического optimism bias, спрос по физическим OD и матрица ответственности и права.
- Проверены ссылки и ограничения методик для 29 дополнительных документов; часть страниц может требовать специальных условий доступа.

## Новые источники и факты

КРДВ 2 сентября 2026 года сообщил о концепции Мохэ–Найба и примерных звеньях 1300 км (Нижний Бестях — Найба) и 1670 км (Нижний Бестях — Магадан). Не построенные линии, нет опубликованной независимой проверки спроса.

В официальной библиотеке правительства Юкона есть 143-страничный Business Case Alaska–Canada Rail Link (2006) от Ernst & Young / Macquarie / Partnerships BC. Исторические сценарии частного финансирования: 2.1–4.4 млрд USD, пробел в капитале: 6.7–9.0 млрд USD. Эти данные не описывают Берингов тоннель; ведущие консультанты предупреждали, что первичные прогнозы не были ими независимо проверены.

### Расчёты V7 (НЕ прогноз)

| Вход/результат | Значение | Статус |
|---|---:|---|
| CAPEX | 249.915 млрд USD | Историческая оценка инициатора InterBering |
| Строительство | 10 лет | Допущение: равные CAPEX в конце года |
| Эксплуатация | 40 лет | Допущение |
| Дисконт | 5% реальных USD | Допущение, не WACC |
| Груз | 30 млн оплачиваемых тонн в год | Допущение, без контрактов |
| Чистый вклад | 100 USD/тонну | Допущение, после переменных издержек |
| Постоянный OPEX | 1.5% CAPEX/год | Допущение |
| PV капитала | 192.978 млрд USD | Независимый расчёт |
| NPV | -200.865 млрд USD | Не включает социальные выгоды, рефинансирование, налоги, модернизации |
| Безубыточный вклад при 30 Mtpa | 735.597 USD/тонну | Не тариф, только математический порог |
| Механический cost stress | 301.965 / 331.865 млрд USD | Не является P50/P80 для Берингова тоннеля; может содержать двойной счёт резервов |

## Метод и формулы

PV_CAPEX = (CAPEX / N) × (1-(1+r)^(-N))/r.
PVFA_OPER = (1-(1+r)^(-T))/(r × (1+r)^N).
NPV = -PV_CAPEX + PVFA_OPER × [Cargo_Mtpa × USD_net_per_t / 1000 - CAPEX × OPEX_rate].

Классы источников: A — официальные госорганизации/операторы, B — профильные и научные публикации. Классификация не гарантирует актуальный доступ или полноценный аудит.

## Ограничения

**Нельзя считать завершённым:** комплексное ТЭО, инвестконтракты, сейсмо-гидрогеологическую модель, EIS, фактическую грузовую матрицу с контрагентами, финансовое закрытие, схему доступа на земли/воды и независимую проектную смету. Без них невозможно заявить ни срок ввода, ни окупаемость.

### Доступность ссылок, проверенная в текущем сеансе

- Страницы USACE для Nome Phase 1A вернули HTTP 403 при автоматическом чтении; это ограничение доступа, не доказательство отсутствия документа.
- Журнал Nature/Scientific Data для IBCAO выдал перенаправление на недоступный шлюз; библиографическая запись сохранена, текст доступен из прежних научных результатов.
- Архивный ресурс Госдепартамента по границе 1990 года в текущем обращении вернул служебную ошибку; для проверки нужен архив/UN Treaty Collection.
- КРДВ, исходный Yukon PDF, PMI и HM Treasury открывались и содержимое сверено.

## Реестр дополнительных источников V7 (29 записей)
**V7-S01 — International Corridor Mohe–Naiba announcement** (KRDV, 2026-09-02).
URL: https://erdc.ru/en/news/na-dalnem-vostoke-postroyat-mezhdunarodnyy-transportnyy-koridor-mokhe-nayba-/
Документально устанавливает: 1,300 km N. Bestyakh–Naiba, ~1,670 km N. Bestyakh–Magadan, new cross-border link with China. Ограничение: Concept; does not establish funding, built track, firm shipping commitments.

**V7-S02 — ACRL Business Case Report** (E&Y / Macquarie / Partnerships BC, 2006-10-31).
URL: https://emrlibrary.gov.yk.ca/emrlibrary/EcDev/Alaska_Canada_Rail_Link/background-files/C-Final%20Business%20Case%20Report_PBC.pdf
Документально устанавливает: $2.1–4.4bn theoretically private-financeable, $6.7–9.0bn model funding gap. Ограничение: Historic ACRL-only conditional models; stage-one assumptions not independently audited; not Bering estimate.

**V7-S03 — The Green Book (2026)** (HM Treasury UK, 2026-02-05).
URL: https://www.gov.uk/government/publications/the-green-book--2/the-green-book-2026
Документально устанавливает: Compare options, monetised/unmonetised impacts, public funding costs, optimism bias. Ограничение: UK guidance is method reference, not Russia/US statutory discount rate.

**V7-S04 — Reference-class forecasting rail and fixed-link optimism** (Bent Flyvbjerg / PMI, 2006).
URL: https://www.pmi.org/learning/library/nobel-project-management-reference-class-forecasting-8068
Документально устанавливает: Historical uplifts: fixed links 23% / 55%, rail 40% / 57% (two reported empirical quantiles). Ограничение: Reference class not calibrated for Bering; avoid double counting existing contingencies.

**V7-S05 — Climate damages Alaska public infrastructure** (Melvin et al / PNAS, 2017).
URL: https://www.pnas.org/content/pnas/114/2/E122.full.pdf
Документально устанавливает: 2015–2099 discounted damages under different RCPs, lowered by proactive adaptation. Ограничение: Historic climate scenarios and 2015-dollar baselines; not tunnel-specific costs.

**V7-S06 — Point Lay thaw field study** (USGS, 2025-08-04).
URL: https://www.usgs.gov/publications/climate-change-and-infrastructure-development-drive-ice-rich-permafrost-thaw-point-lay
Документально устанавливает: ~60 bores; observed thaw and excess ground ice in a specific Alaska community. Ограничение: One community; cannot extrapolate these soil parameters to all tunnel approaches.

**V7-S07 — Shishmaref planning / erosion** (Alaska Department of Commerce, accessed 2026).
URL: https://www.commerce.alaska.gov/web/dcra/ResiliencePlanningLandManagement/ShishmarefInter-AgencyPlanningWorkGroup
Документально устанавливает: Coastal relocation planning and hazards, erosion and thaw. Ограничение: Local adaptation case; economic benefits not measured for Bering corridor.

**V7-S08 — Coast Guard Bering Strait port-access study** (US Coast Guard, 2014).
URL: https://navcen.uscg.gov/sites/default/files/pdf/PARS/Bering_Strait_PARS_General.pdf
Документально устанавливает: Navigation density and subsistence uses; routing risk study. Ограничение: Vessel safety context, not rail demand or construction approval.

**V7-S09 — NOAA 2025 Arctic Report Card ecosystem** (NOAA, 2025).
URL: https://arctic.noaa.gov/report-card/report-card-2025/warming-waters-and-borealization-restructuring-ecosystem-dynamics-in-the-northern-bering-and-chukchi-seas-2002-2022/
Документально устанавливает: Warming impacts on marine species and subsistence food security. Ограничение: Regional trends not quantitative damage estimate from proposed tunnel.

**V7-S10 — NOAA vessel transit counts (AIS, 2025)** (NOAA Office for Coastal Management, 2026-05-18).
URL: https://www.fisheries.noaa.gov/inport/item/79556/full-list
Документально устанавливает: Geospatial annual vessel passages, 100m GIS raster. Ограничение: Grid-cell counts are not unique ships or tonnes.

**V7-S11 — UK Channel Tunnel Rail Link postmortem** (National Audit Office, 2005).
URL: https://www.nao.org.uk/reports/progress-on-the-channel-tunnel-rail-link/
Документально устанавливает: Revenue forecasts below expectations; government-backed restructuring. Ограничение: CTRL is UK rail connection not same asset as subsea Channel Tunnel.

**V7-S12 — Channel Tunnel case study** (Global Infrastructure Hub, 2020).
URL: https://www.gihub.org/connectivity-across-borders/case-studies/the-channel-tunnel/
Документально устанавливает: Debt restructuring, usage contract and banking lessons. Ограничение: Historic currencies, costs, markets and governance.

**V7-S13 — Gotthard Base Tunnel costs & length** (Swiss Federal Department DETEC, 2025/2026).
URL: https://www.uvek.admin.ch/en/nrla
Документально устанавливает: 57.1 km, actual reported CHF 12.2bn. Ограничение: Alpine geology and scope differ from maritime tunnelling.

**V7-S14 — Ryfast road tunnel complex** (Norwegian Public Roads Administration, 2020-04-22).
URL: https://www.vegvesen.no/om-oss/presse/aktuelt/nasjonalt/norges-storste-veiprosjekt-apnes-i-stavanger-onsdag
Документально устанавливает: 53 km tunnel excavations; complete project 11.8bn NOK (2020). Ограничение: Road tunnel system, not passenger/freight rail.

**V7-S15 — Russian SP 119.13330.2024** (Russian state standards register, 2024-08-02).
URL: https://protect.gost.ru/sp/details/3f0f2d22-9baf-42ce-aa30-1e2e215a9b2a
Документально устанавливает: Design standard rail gauge 1520mm. Ограничение: Standards applicability at border subject to design and bilateral agreement.

**V7-S16 — U.S.–USSR maritime boundary status** (U.S. Department of State archive, 2021–2025).
URL: https://2021-2025.state.gov/u-s-maritime-boundaries/
Документально устанавливает: 1990 agreement applied provisionally pending entry into force. Ограничение: Separate rail treaty, permanent construction permits and operation not established.

**V7-S17 — NEPA explained** (US Environmental Protection Agency, 2026-02-23).
URL: https://www.epa.gov/nepa/what-national-environmental-policy-act
Документально устанавливает: Relevant US federal decisions require environmental assessment processes. Ограничение: Project-specific responsible agency and decision trigger unknown.

**V7-S18 — Tribal consultation guidance** (U.S. Bureau of Indian Affairs, accessed 2026).
URL: https://www.bia.gov/service/tribal-consultations/what-tribal-consultation
Документально устанавливает: Government-to-government consultation and formal response obligations. Ограничение: Project footprint and affected Tribes must be identified, not presumed.

**V7-S19 — Port of Nome phase 1A award** (U.S. Army Corps of Engineers, 2025-08-15).
URL: https://www.poa.usace.army.mil/Media/News-Releases/Article/4276752/usace-awards-construction-contract-for-portion-of-port-of-nome-modification-pro/
Документально устанавливает: $399.4m for contracted phase 1A only. Ограничение: Not full port programme or railway and not tunnel approach.

**V7-S20 — Port of Nome status update** (U.S. Army Corps of Engineers, 2026-03-27).
URL: https://www.poa.usace.army.mil/Media/News-Stories/Article/4446254/assistant-secretary-of-the-army-for-civil-works-visits-nome/
Документально устанавливает: Phase 1A causeway 1,200ft, dock face 600ft; dredging Phase 2. Ограничение: Phase schedule can change; capital not full programme.

**V7-S21 — IBCAO 5.0 Arctic grid** (Scientific Data / International Bathymetric Chart, 2024).
URL: https://www.nature.com/articles/s41597-024-04278-w
Документально устанавливает: 100m cell size; >25% Arctic area backed by individual soundings. Ограничение: 100m grid does not mean 100m survey precision; insufficient for alignment design.

**V7-S22 — Bering Strait eastern-channel survey** (NOAA Fisheries, 2023-06-06).
URL: https://www.fisheries.noaa.gov/feature-story/strait-connecting-pacific-and-arctic-oceans-larger-previously-measured
Документально устанавливает: Detailed east-channel bathymetry; ~1m seabed elevation change over 1950–2010. Ограничение: Seabed erosion not same as rock fault displacement; west-channel different dataset.

**V7-S23 — Grouting and excavation Seikan Tunnel** (Society for Mining, Metallurgy & Exploration, 1981).
URL: https://onetunnel.org/documents/grouting-and-excavation-in-the-construction-of-the-seikan-tunnel
Документально устанавливает: Faults and groundwater handled via pilot tunnels, grouting, exploratory boreholes. Ограничение: Historical construction methods differ from current practice.

**V7-S24 — AIS crossings of Bering Strait 2010–24** (Marine Exchange of Alaska / Arctic Watch, 2025).
URL: https://arcticwatch.org/wp-content/uploads/2025/05/Arctic-Watch-Jan-2024-Workshop-Report.pdf
Документально устанавливает: AIS-identified directional passages 242 (2010), 665 (2024). Ограничение: Not count of unique vessels; only equipped and detected voyages; not rail cargo.

**V7-S25 — 2025 Alaska Railroad annual report** (Alaska Railroad Corporation, 2026).
URL: https://www.alaskarailroad.com/sites/default/files/Communications/Alaska_Railroad_Annual_Report_2025_Final.pdf
Документально устанавливает: Observed railroad operations and annual freight history. Ограничение: Railroad is not currently connected to Canada, not proxy for tunnel freight.

**V7-S26 — 1990 temporary maritime-boundary agreement** (UN Treaty Collection, 1990).
URL: https://treaties.un.org/Pages/showDetails.aspx?objid=0800000280075a22
Документально устанавливает: Agreement to abide by maritime boundary pending entry into force. Ограничение: Not permit to tunnel beneath boundary.

**V7-S27 — Bathymetry of Chukotka to Diomede Island** (USGS Science Data Catalog, 1976–1997).
URL: https://data.usgs.gov/datacatalog/data/USGS%3A41e77b48-6a66-40e3-ba50-4e8aeb472c92
Документально устанавливает: Old digitized bathymetry coverage mainly western side. Ограничение: Age and density; not site-level construction survey.

**V7-S28 — Marine AIS geospatial services** (NOAA Digital Coast, 2026).
URL: https://www.coast.noaa.gov/digitalcoast/data/vesseltraffic.html
Документально устанавливает: GIS AIS geospatial data available 2009–2026. Ограничение: No unique rail demand inference without OD and freight commodities.

**V7-S29 — Cross-border tunnel usage debt case** (UK National Audit Office, 2001).
URL: https://www.nao.org.uk/reports/department-of-the-environment-transport-and-the-regions-the-channel-tunnel-rail-link/
Документально устанавливает: Government guarantee exposure and uncertain wider benefit realisation. Ограничение: Different geographic and institutional baseline.

## Протокол проверки

{
  "date": "2026-10-23",
  "v6_sheets_preserved": 81,
  "v7_new_sheets": 18,
  "v7_total_sheets": 99,
  "v6_nonempty_cells_verified": 11028,
  "v6_formulas_verified": 392,
  "v6_cached_results_verified": 388,
  "v7_sources": 29,
  "v7_new_facts": 21,
  "v7_dcf_npv_bn": -200.8649502883204,
  "v7_30mt_break_even_usd_per_t": 735.5968522694636,
  "v7_rcf_stress_lower_bn": 301.965,
  "v7_rcf_stress_upper_bn": 331.865,
  "formula_errors": []
}