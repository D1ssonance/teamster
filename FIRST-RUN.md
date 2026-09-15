# Первый запуск

## 1. Подготовьте runtime

Нужны:

- agent runtime с semantic-role adapter;
- exact model registry без секретов в экспортируемых файлах;
- runtime-only credential references;
- отдельные каталоги для reference, session outputs, cache и shared state;
- локальный fake gateway для offline tests;
- sandboxed executor для native fixtures, если тестируется код.

Не меняйте production router на этапе подготовки.

## 2. Создайте reference router

Начните с `examples/reference-router.template.json`.

Для каждой роли:

- укажите exact IDs;
- расположите их по приоритету;
- не смешивайте availability и role quality;
- сохраните все non-model settings;
- добавьте metadata о том, какие роли реально проверены.

Reference router должен быть immutable после принятия. Новые измерения записываются в assessment run, а не прямо в reference.

## 3. Запустите offline проверки

Минимум:

- schema validation;
- unknown/duplicate/missing model tests;
- all-role explicitness;
- exclusion tests;
- settings preservation;
- loader roundtrip;
- fake gateway cache, retry and fail-closed tests;
- privacy scan.

## 4. Запустите API smoke

Начните с одной модели и 1–3 deterministic cases. Заранее зафиксируйте:

- cap;
- timeout;
- retry policy;
- model ID;
- adapter/protocol;
- input hashes;
- expected output contract.

Live inference требует отдельного approval. Каждая попытка, включая retry, считается в cap.

## 5. Запустите role-fit

Выберите только роли, для которых есть fixture и acceptance criteria. Не объявляйте остальные роли проваленными: они остаются `unvalidated`.

Проверяйте exact identity и отсутствие fallback/substitution. После завершения нужен независимый review.

## 6. Выпустите session router

Availability refresh должен:

- читать reference;
- дедуплицировать модели;
- соблюдать reference order;
- учитывать shared cooldown read-only;
- пользоваться cache TTL не более пяти минут;
- не обходить cooldown при force;
- остановиться без router при незакрытой роли;
- записать redacted report даже при отказе.

Output directory должен быть новым, приватным и не совпадать с production/reference/state.

## 7. Активация

Активация только вручную после проверки:

- loader roundtrip;
- всех десяти ролей;
- непустых цепочек;
- сохранности non-model settings;
- exclusions;
- source/input hashes;
- reviewer independence policy.

Переменная окружения активации должна задаваться в том же runtime, где запускаются дочерние агенты. Наследование в глубоко вложенных процессах нужно проверить отдельно и не считать гарантированным.
