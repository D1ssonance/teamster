# Обезличенные результаты и lessons learned

## Что подтвердилось

- Semantic role routing лучше прямого выбора модели по памяти.
- Приоритетные fallback chains полезны, если порядок и причины выбора зафиксированы.
- API smoke быстро отделяет route/auth/rate-limit/incompatibility от quality.
- Native role fixtures часто информативнее API/tool tests для agent work.
- Отдельные debugger/fixer fixtures выявляют nonlocal state и transaction defects, которые не видны в обычном chat smoke.
- Immutable reference + transient availability session layer безопаснее постоянной перезаписи production config.
- Fail-closed all-role generation предотвращает запуск роутера с тихо восстановленными defaults.
- Exact loader roundtrip нужен: неполная role map может воскресить нежелательные default models.
- Cache должен иметь TTL, atomic writes, lock ownership, corruption/future-time rejection и защищённые пути.
- Shared cooldown нельзя обходить флагом force; probe budget и admission quota — разные механизмы.
- Independent reviewer нужен после успешной реализации, но reviewer не заменяет native verification.
- Результат агента без receipt не является доказательством.
- Interrupted coordination нельзя автоматически трактовать как model failure.

## Что не следует обещать

- маленькая synthetic выборка не доказывает универсальный рейтинг;
- API tool incompatibility не доказывает native-agent inability;
- text probe не доказывает vision capability;
- одна роль не наследует автоматически качество другой роли;
- fallback chain не гарантирует reviewer independence;
- production activation не должна быть побочным эффектом успешных тестов;
- nested child inheritance environment нужно проверять отдельно;
- path preflight без OS primitives не устраняет все TOCTOU races.

## Надёжный порядок улучшений

1. Сначала документированный API и фактический loader contract.
2. Затем offline fake-gateway tests.
3. Затем bounded smoke.
4. Затем role-specific deterministic fixtures.
5. Затем независимый review.
6. Затем отдельный approval на reference update или activation.

## Операционный принцип

Разделяйте качество, доступность, скорость, безопасность и координацию. Не превращайте отсутствие ответа, rate limit или падение инфраструктуры в нулевую оценку модели.

## Historical aggregate evidence (not a ranking)

An anonymized development campaign covered 24 candidates: 99 text cases / 116
HTTP attempts, 54 tool cases / 92 attempts, and 54 native sessions across nine
candidates. Nine saved fixes passed their hidden tests; diagnosis tasks produced
seven passes, one timeout and one incorrect diagnosis. These are historical
small-sample observations, not current availability or cross-role qualification.

The local offline regression suite grew from 95 to 125 passing tests, including
30 session-generator tests. A separate reference validator had 19 passing tests;
14 documented adapter-contract tests passed. An older broader adapter suite had
known failures/errors, so these successes never established universal runtime health.
The portable package does NOT include that executable harness or its private data;
these counts describe prior verification, not tests shipped in this directory.

A missing/empty freeze manifest was found in a native campaign. Inputs were checked
against a prior baseline instead; the limitation remained explicit. Some grading
rubrics were ambiguous, and interpretations were kept separate from raw scores.
Reviewers twice understated safety findings. Root required fixes for state override,
cache collisions and directory aliases instead of accepting the approval label.
Repeated missing handoffs delayed delivery; bounded escalation to direct root work
is preferable to endless replacement delegation.
