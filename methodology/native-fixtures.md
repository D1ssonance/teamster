# Native fixtures и executor

Native tests должны проверять observable behavior, а не стиль ответа.

## Требования

- deterministic synthetic fixture;
- seeded buggy/correct/partial-fix variants;
- exact model identity;
- no fallback/substitution;
- bounded wall time and attempt count;
- separate quality verdict and elapsed time;
- no host execution of generated code;
- approved hardened sandbox: no network, non-root, read-only root where possible, resource limits, capability drop, pinned image digest;
- receipt with executor hash, fixture hash, input hash, exit status and scope.

## Recovery

Interrupted run не означает model failure. Reconstruct completed cases from disk receipts. Не rerun completed model cases. Corrupt budget/state должен fail closed; нельзя удалять lock или поднимать cap.
