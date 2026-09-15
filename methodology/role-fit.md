# Методика полного role-fit тестирования

## Стадии

1. preflight и exact identity;
2. API smoke;
3. tools, если роль использует tools;
4. native agent, если runtime это поддерживает;
5. role-specific deterministic fixtures;
6. независимый review;
7. role matrix и recommendation.

## Role matrix

`validated` — все обязательные стадии прошли.

`partially_validated` — часть стадий прошла, gaps перечислены.

`unvalidated` — недостаточно evidence.

`unavailable` — route не дал usable response.

`incompatible` — протокол или request отвергнут.

`failed` — route работал, но role fixture провален.

## Минимальные fixtures

- `scout`: правильные files/symbols/edges без выдуманных ссылок;
- `requirements`: выявление material ambiguity и сохранение ограничений;
- `coder`, `heavy-coder`: implementation + targeted checks;
- `test-writer`: тест ловит seeded defect и проверяет production behavior;
- `debugger`: diagnosis совпадает с injected defect и trace/state;
- `fixer`: минимальный fix проходит buggy, correct и partial-fix variants;
- `reviewer`: seeded defect detection и severity;
- `corporate-architect`: evidence-based options/trade-offs;
- `vision`: реальный image/diagram input.

## Правила интерпретации

API healthy не означает role-qualified. Tool failure API не доказывает native failure. Vision text probe не доказывает vision capability. Небольшая synthetic выборка годится для reversible pilot, но не для универсального рейтинга.

## Повторы

Не повторяйте завершённые cases для улучшения оценки. Повтор разрешён только при ambiguity или plausibly transient failure. При восстановлении после interruption сначала сверяйте receipts и starts, затем решайте, что допустимо повторить.
