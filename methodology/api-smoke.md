# Методика быстрого API smoke-test

## Назначение

Smoke-test отвечает только на вопрос: «отвечает ли exact model через данный adapter сейчас?» Он не отвечает на вопрос о пригодности для роли.

## Протокол

1. Resolve exact provider/model/adapter identity.
2. Проверьте exclusions и approval на live inference.
3. Зафиксируйте manifest и hard attempt cap.
4. Используйте 1–3 deterministic cases.
5. Запускайте serially, если нет доказанной необходимости в concurrency.
6. Разрешите максимум один retry для timeout/network/transient 5xx.
7. Не retry 400, 401, 403, 404, 429.
8. Count every underlying HTTP attempt.
9. Redact report before writing.

## Классификация

Разделяйте:

- healthy;
- empty;
- truncated;
- incompatible request/model route;
- auth/permission;
- rate limited;
- transient server/network/timeout;
- malformed/unknown response.

Не превращайте unavailable в quality score 0.

## Отчёт

Храните exact ID, adapter, timestamp, cap, attempts, first-attempt success, retry recovery, latency, error categories, fixture/input hashes и ограничения. Не храните URL, headers, keys, raw body или raw exception.

## Для новых внешних моделей

Не подставляйте внешнюю модель в корпоративный harness только из-за похожего протокола. Используйте фактический adapter агента или отдельный локальный adapter с теми же safety guarantees.
