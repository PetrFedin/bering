# BERING CORRIDOR — исследовательский репозиторий

**Россия · Якутия · Магадан · Чукотка · Берингов пролив · Аляска · Канада · США · Китай**

> Статус: **исследовательская программа**. Самостоятельный Магаданский логистический хаб — коммерческая проверка; железная дорога Нижний Бестях — Магадан — отдельное предТЭО; международный переход — **HOLD**. Публикации, сценарии, предварительные сметы и проектные мощности **не являются** утверждённым ТЭО, концессией, транспортным контрактом, разрешением или обязательством финансирования.

Этот репозиторий — единая карта знаний, исходных публичных источников и воспроизводимых расчётов проекта **Bering Corridor / Берингов коридор**. Последняя исследовательская итерация: **V14, 26.10.2026**.

## О чём проект

Исследуются четыре **разделённых периметра**:
1. **Существующая региональная логистика**: Магадан, Певек, Анадырь, портовое снабжение, северный завоз, склады, холодная цепь и улучшение работы терминалов.
2. **Наземный северо-восточный коридор**: Якутия → Магадан → потенциальные связи с Чукоткой, с независимым экономическим обоснованием каждого участка.
3. **Транзит из Китая**: Тунцзян–Нижнеленинское, Благовещенск, Владивосток, Хабаровск и сопоставление с морскими сервисами Китай–США.
4. **Межконтинентальный переход**: потенциальный тоннель/подводная связь через Берингов пролив и новые железные дороги в Аляске/Канаде; **нет действующего сквозного железнодорожного маршрута**.

## Навигация

- [Реестр исследований и версий](docs/VERSION_INDEX.md)
- [Текущий проверенный статус](docs/STATUS.md)
- [Архитектура сети и альтернатив](docs/CORRIDOR_NETWORK.md)
- [Коммерческая модель Магадана](docs/MAGADAN_HUB.md)
- [Три коммерческих пилота](docs/COMMERCIAL_PILOTS.md)
- [Экономическая методология](docs/ECONOMIC_METHOD.md)
- [Инженерные и юридические контрольные рубежи](docs/ENGINEERING_LEGAL_GATES.md)
- [Система доказательств и словарь данных](docs/EVIDENCE_STANDARD.md)
- [План разработки V15+](docs/ROADMAP.md)
- [Журнал решений](docs/DECISION_LOG.md)
- [Каталог доступных материалов и ограничений переноса](archive/FILE_MANIFEST.md)
- [Извлечённые тексты версий V7–V14](archive/versions/)
- [Машиночитаемые реестры](data/registries/)
- [Правила работы для аналитиков и ИИ](AGENTS.md)

## Что считать доказанным грузом

Любая оценка спроса имеет **два независимых фильтра**:

**1. Существование и возможность доставки**: конкретные отправитель, получатель, OD-маршрут, вид груза, единица измерения, фактический объём, документальные сроки, сравнимый door-to-door тариф и правовая допустимость.

**2. Дополнительность проекту**: объём действительно новый *или* перевод существующего груза создаёт положительную проверенную **групповую** инкрементальную маржу; двойной счёт и каннибализация вычтены. Перевод контейнера между двумя своими терминалами не создаёт автоматически нового спроса.

**Нет документа → нет подтверждённой выручки.** Незаполненное поле никогда не трактуется как нуль. Отчётные TEU, тонны, влажные тонны, штучный груз, мощность терминала, добыча руды, выручка и маржа не складываются как одна величина.

## V14: состояние коммерческой приёмки

- Пилоты: P1 — Владивосток–Магадан dry 40ft; P2 — reefer 40ft; P3 — Китай–Владивосток–Магадан.
- Есть публичные элементы тарифов SASCO / КМП и сведения о расписаниях, но **нет** полного комплекта реальных D2D предложений, накладных, счетов и подтверждений нового оплачиваемого объёма.
- Подготовлено **15 RFQ**: их отправка и ответы **не подтверждены**.
- **0/3** пилотов допущено к инвестиционному прогнозу.
- Разные сообщения об инвестиционном ТЛК «Магадан» содержат **30 тыс. и 150 тыс. TEU/год**. Пока не согласованы период, этапность, объекты и новая смета — не смешивать.
- Мастер-модель V14: **72 листа**, из которых 53 унаследованы из V13, 19 новых. Архивные извлечения не заменяют исполняемый .xlsx без отдельной проверки.

## Важно о формате хранилища

GitHub-архив содержит проверяемые **текстовые извлечения** из исследовательских DOCX/XLSX и переносимые исходные CSV. Исходные бинарные файлы перечислены в [манифесте](archive/FILE_MANIFEST.md) с SHA-256, когда локальный файл доступен. Если бинарник не перенесён, статус прямо указан как **NOT_COMMITTED_BINARY**, без заявления о резервном копировании файла. Тексты извлечений полезны для поиска и проверки исходных утверждений, но **не сохраняют формулы, стили и интерактивность исходного Excel**.

## Основные публичные первоисточники

- [SASCO — каботажные линии и тарифы](https://www.sasco.ru/)
- [Камчатское морское пароходство — Владивосток–Магадан](https://kasco.su/schedule_vvo-mag/)
- [Магаданский морской торговый порт — тарифы](https://www.magadanport.ru/klientam/tarify/)
- [FESCO — клиентские сервисы](https://www.fesco.ru/ru/clients/container/)
- [Alaska Railroad — грузовые перевозки](https://www.alaskarailroad.com/freight)
- [USGS — геология и вечная мерзлота](https://www.usgs.gov/)
- [NOAA — данные по Арктике](https://www.noaa.gov/)
- [IMO — Polar Waters](https://www.imo.org/en/OurWork/Safety/Pages/polar-code.aspx)

**Правовой и методологический дисклеймер**: все числа в сценариях подлежат сверке с первоисточниками, датами, единицами, валютой, НДС и периметром проекта. Данные прошлых версий сохраняются с историческими датами, а не выдаются за текущие.



## Research repository completeness receipt — 26 October 2026

**GitHub:** searchable V7–V14 historical research, all 100 sheet sections from indexed V7, reconstructed 53-sheet V13 and 72-sheet V14 text snapshots, 11 normalized CSV registries, evidence rules, network/economics/safety/legal chapters, SHA-256 manifest, seven open implementation issues and research validation workflow.

**Original binaries:** 31 byte-preserved original V8–V14 source files are in a **separate ChatGPT-downloadable ZIP** (SHA-256 `1f85d70dd2733d2f4d3b9e6bb8312bbe7c7bde96e7ccd0d48bced2c04ea16217`). The ZIP is **not in GitHub**, and files are not equivalent to searchable conversions. See [source manifest](archive/FILE_MANIFEST.md) and [binary import issue](https://github.com/PetrFedin/bering/issues/1).

**Source gaps:** V1–V6 stand-alone binaries and V7 source binaries not recovered. Some additional V4/V7 Library documents only indexed as search snippets; see [unrecovered source list](archive/UNRECOVERED.md).

**Formula QA:** 2,605 workbook formula cells across seven originals; 70 cached results are missing, including 35 in V14. See [QA report](docs/QA_WORKBOOKS.md). **GitHub Actions CI currently fails and is not certified**; see [CI issue](https://github.com/PetrFedin/bering/issues/7).

**Commercial status:** no full signed new cargo commitments for P1/P2/P3, no RFQs sent. Tunnel HOLD; standalone Magadan hub remains a separate investment research question.

For a detailed release receipt and process to add original source files, see [delivery status](docs/DELIVERY_STATUS.md).
