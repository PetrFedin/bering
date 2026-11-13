# Bering V34 — GitHub Actions: сбой до выполнения шагов

**Срез: 13.11.2026.** Это read-only диагностическое руководство, не заявление, что сбой исправлен.

Репозиторий private. Для V33 SHA `6281b6cf42fb90b3ae776887bfd2cbd1d82b0c63` два jobs:
- [Shipment-quality run #43458443691](https://github.com/PetrFedin/bering/actions/runs/43458443691) — `failure`, job `131998678727`, `steps=null`, 1 Check Run annotation (текст недоступен).
- [Research QA run #43458443531](https://github.com/PetrFedin/bering/actions/runs/43458443531) — `failure`, job `131998677857`, `steps=null`, 2 Check Run annotations (тексты недоступны).

Это не доказательство падения Python. Причина до выполнения шагов может лежать в runner provisioning, доступе или billing/policies, но **точная причина не установлена**. Отдельное совпадение с сообщениями GitHub Community не доказывает причину Bering.

## Проверка владельцем без изменения настроек

1. Открыть указанные GitHub runs и секцию ошибок/аннотаций, сохранить **дословный текст** 1+2 аннотаций, UTC-время, run/job ID, runner labels.
2. Убедиться, что репозиторий использует разрешённые Actions, и посмотреть личные Settings → Billing & licensing → Budgets and alerts / Actions usage. Не включать расходы автоматически.
3. По результату решить, нужна ли проверка GitHub Status и поддержка GitHub; передать в Support ссылки на неудачные jobs и журнал отсутствия `Set up job`/steps. Не переходить в public и не регистрировать paid/self-hosted runner без оценки доступа/безопасности.
4. После устранения **конкретной доказанной причины** обеспечить реальный CI на том же финальном SHA с полным набором регрессионных тестов. Допуск к investment не выводится из CI GREEN сам по себе.

[GitHub Docs: troubleshooting workflows](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows). Документация описывает диагностику отказов и проверку billing/runner. Она не устанавливает конкретный Bering root cause.

**P0 CI — OPEN; Hosted GREEN — NOT VERIFIED.**
