# Еженедельный мониторинг источников — инструкция по установке

OAuth-токен текущей сессии не имеет scope `workflow`, поэтому файл workflow нельзя записать через API. **Действие владельца (2 минуты):** создать файл `.github/workflows/source-monitor.yml` с содержимым ниже (кнопка Add file → Create new file на GitHub) и закоммитить в main.

Реестр источников уже лежит в `data/public/MONITORED_SOURCES.json`. Логика: изменение SHA-256 источника = job падает = GitHub шлёт уведомление владельцу. Алерт — сигнал проверить источник, не факт.

```yaml
name: Source Monitor
on:
  schedule:
    - cron: '0 6 * * 1'   # еженедельно, понедельник 06:00 UTC
  workflow_dispatch:
permissions:
  contents: read
jobs:
  monitor:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - name: Check monitored public sources for changes
        run: |
          python3 - <<'EOF'
          import hashlib, json, os, sys, urllib.request
          reg = json.load(open("data/public/MONITORED_SOURCES.json", encoding="utf-8"))
          changed, errors = [], []
          for src in reg["sources"]:
              url, expect = src["url"], src.get("sha256")
              try:
                  req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 bering-source-monitor"})
                  data = urllib.request.urlopen(req, timeout=60).read()
                  actual = hashlib.sha256(data).hexdigest()
                  print(f"{src['name']}: sha256={actual[:16]}... bytes={len(data)}")
                  if expect and actual != expect:
                      changed.append(src["name"])
              except Exception as e:
                  errors.append(f"{src['name']}: {e}")
          with open(os.environ.get("GITHUB_STEP_SUMMARY","/dev/null"),"a") as s:
              s.write("## Source monitor\n")
              for c in changed: s.write(f"- CHANGED: {c}\n")
              for e in errors: s.write(f"- ERROR: {e}\n")
          if changed:
              print("CHANGED:", changed); sys.exit(1)
          if errors:
              print("ERRORS:", errors); sys.exit(2)
          print("All monitored sources unchanged.")
          EOF
```

Внимание: мониторинг работает только после восстановления GitHub Actions (issue #7).
