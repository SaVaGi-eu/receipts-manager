---
name: new-service
description: Scaffold the four files required for a new service — service class, dataclass model, route handlers, and pytest stub — following existing project conventions
---

You are scaffolding a new service for the receipts-manager project. Ask the user for the **service name** in snake_case (e.g. `tag`, `export`, `notification`) if not already provided.

## Files to create

Given service name `{name}` (e.g. `tag`), create the following four files:

### 1. `services/{name}_service.py`
Follow the pattern in `services/category_service.py`:
- Module docstring referencing the Jira ticket if known
- Class `{Name}Service` with `__init__(self, receipt_service)` storing `self._svc = receipt_service`
- At minimum a `get_{name}s()` method and one mutating method relevant to the service's domain
- Use `self._svc._lock` for writes, same as existing services

### 2. `models/{name}.py`
Follow the pattern in `models/item.py`:
- `@dataclass` class `{Name}` with typed fields and `field(default_factory=…)` for collections
- `@classmethod from_dict(cls, d: dict) -> "{Name}"` using `.get()` with sensible defaults
- `to_dict(self) -> dict` returning all fields

### 3. `routes/{name}_routes.py`
Create stub handlers (pure functions, no Flask imports needed — routes are registered in `app.py`):
```python
def handle_get_{name}s(service) -> tuple[int, dict]:
    ...

def handle_post_{name}(service, body: dict) -> tuple[int, dict]:
    ...
```
Return `(200, {"items": [...]})` / `(201, {"id": ..., "success": True})` shapes consistent with existing routes.

### 4. `tests/test_{name}_service.py`
Follow the pattern in existing test files:
- Import and instantiate `{Name}Service` with a mock or minimal `receipt_service`
- At least one happy-path test per public method
- Use `pytest.fixture` for the service instance

## After creating files

Remind the user to:
1. Register the new routes in `app.py` (import + `app.route(...)`)
2. Add the service instantiation in `app.py` alongside `ReceiptService`, `CategoryService`, etc.
3. Run `/run-tests` to confirm the new tests pass
