<p align="center">
  <img src="assets/logo.png" alt="Teamster" width="480">
</p>

<p align="center">
  <strong>Role-based orchestration and workflow toolkit for AI agents</strong>
</p>

<p align="center">
  Skills · Role Router · Work Contracts · Verification · Multi-Agent Workflows
</p>

---

Этот каталог содержит переносимую схему построения, проверки и безопасного обновления роутера ролей агентов. В материалы намеренно не включены названия провайдеров, моделей, проектов, репозиториев, URL, ключи, логи сессий и персональные данные.

## Цели

Схема решает четыре задачи:

1. выбрать semantic role для задачи;
2. выбрать модель по неизменяемой reference-конфигурации и fallback-цепочке;
3. отделить краткую проверку доступности от оценки качества роли;
4. безопасно выпустить временный session router без автоматической активации.

## Содержимое

- `examples/reference-router.template.json` — обезличенный шаблон reference router;
- `examples/session-router-report.template.json` — формат redacted отчёта;
- `templates/work-contract.md` — контракт делегирования;
- `methodology/api-smoke.md` — быстрый API smoke-test;
- `methodology/role-fit.md` — полное role-fit тестирование;
- `methodology/native-fixtures.md` — требования к native fixtures и executor;
- `policies/production-safety.md` — правила безопасности и активации;
- `policies/evidence-and-privacy.md` — требования к доказательствам и приватности;
- `skills/` — два reusable Agent Skills;
- `FIRST-RUN.md` — пошаговый первый запуск;
- `RESULTS-AND-LESSONS.md` — обезличенные результаты развития workflow.

## Архитектура

```text
immutable reference router
          |
          +--> model API smoke
          +--> tool protocol (если нужен)
          +--> native agent fixtures (если доступны)
          +--> role-specific fixtures
          +--> independent review
          |
          +--> ручное решение о reference router

reference router + свежая availability probe
          |
          +--> generate-only session router
                    |
                    +--> ручная проверка
                    +--> ручная активация при отдельном approval
```

Production router, его state и reference router должны быть разными артефактами. Доступность модели не является доказательством пригодности к роли.

## Быстрый старт

1. Скопируйте шаблоны и замените только placeholder-значения во внутренней среде.
2. Определите десять ролей: `scout`, `coder`, `heavy-coder`, `test-writer`, `fixer`, `debugger`, `requirements`, `reviewer`, `corporate-architect`, `vision`.
3. Для каждой роли задайте непустую ordered fallback-цепочку с exact model IDs.
4. Настройте runtime adapter и env reference для credentials. Не записывайте секрет в JSON.
5. Выполните offline tests на fake gateway.
6. Запустите короткий smoke-test одной модели.
7. При успехе выполните role-fit только для нужных ролей.
8. Выпустите session router в новом приватном каталоге. При незакрытой роли router не создаётся.
9. Проверьте loader roundtrip и diff настроек.
10. Только после отдельного approval активируйте конфигурацию вручную.

Подробные команды зависят от конкретного agent runtime. Этот пакет намеренно не содержит provider-specific CLI.

## Основные инварианты

- exact identity важнее дружелюбного имени;
- все роли явно присутствуют и имеют непустые списки;
- fallback сохраняет reference order;
- пользовательские exclusions абсолютны;
- shared cooldown читается read-only;
- probe budget не смешивается с admission quota;
- кэш availability ограничен TTL и не обходит cooldown;
- `--force` обходит только кэш;
- при любой незакрытой роли нет loadable session router;
- production router и shared state не меняются автоматически;
- generated code не выполняется на host;
- стоимость и токены не участвуют в выборе модели.

## Не входит в пакет

- универсальный API-клиент для всех провайдеров;
- автоматическая активация при старте чата;
- автоматическая смена production router;
- передача корпоративных данных внешним моделям;
- утверждение, что маленькая synthetic выборка даёт универсальный рейтинг.
