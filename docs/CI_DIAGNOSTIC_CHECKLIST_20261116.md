# CI · Диагностический чек-лист GitHub Actions — 16.11.2026 (issue #7)

## Симптом (воспроизводимый)

На множестве SHA (V29–V36) workflow завершаются `failure` **до первого шага**: jobs API возвращает `steps=null`, `runner_id=0`, запрос логов — `404 BlobNotFound`, в check runs есть 1–2 аннотации, текст которых через API не читался. Локально на тех же SHA тесты проходят (до 443/443).

## Что уже исключено

- Actions включены, `allowed_actions=all`, self-hosted runners = 0 — само по себе не блокер.
- Исчерпание квоты artifact storage было причиной **одной** серии падений (устранено в V26, GREEN 01.11.2026, run 41347030976: 314/314). Текущие падения — другие: до шагов.
- Код и workflow-синтаксис: минимальный zero-dependency workflow (PR #10) тоже падал до шагов → проблема на уровне аккаунта/биллинга/политик, а не YAML.

## Что сделать владельцу в веб-интерфейсе (30 минут)

1. **Actions → любой failed run → job → свернутый блок «Annotations»** вверху страницы — скопировать дословный текст. Именно аннотация содержит причину («billing», «spending limit», «plan does not include…» и т.п.). Это единственный недостающий факт.
2. **github.com/settings/billing → Billing and plans → Actions & Packages**: проверить included minutes для приватных репозиториев и **spending limit = $0** (дефолт блокирует платные минуты после исчерпания бесплатных).
3. **Settings → Actions → General** репозитория: `Actions permissions`, `Workflow permissions`, нет ли организационной политики.
4. Если причина = биллинг: либо поднять spending limit, либо перевести репозиторий в public (Actions для public бесплатны без квоты минут), либо подключить бесплатный self-hosted runner на любом своём Mac/ПК (`Settings → Actions → Runners → New self-hosted runner`) — тогда workflow работают без биллинга.

## Временная мера в репозитории (уже в этом PR)

- `research-qa.yml` на main не использует `actions/upload-artifact` — квота артефактов не влияет.
- Все новые workflow пишут квитанции в Job Summary (`GITHUB_STEP_SUMMARY`), а не в artifacts.

## Критерий закрытия issue #7

- [ ] Дословный текст аннотации зафиксирован в issue #7.
- [ ] Устранена причина (billing / public / self-hosted runner).
- [ ] GREEN на едином SHA по workflow `research-qa.yml` + ссылка на run в README.
