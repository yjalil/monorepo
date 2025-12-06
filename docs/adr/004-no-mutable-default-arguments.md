# ADR-004: No Mutable Default Arguments

## Status
Active

## Context
Python evaluates default argument values once at function definition time, not at call time. When a mutable object (list, dict, set, or custom object) is used as a default, it is shared across all function calls, leading to unexpected behavior where state persists between invocations.

This is one of Python's most common gotchas and causes subtle bugs that are difficult to diagnose.

## Decision
**Never use mutable objects as default argument values.** Use `None` as the default and construct the mutable object inside the function body.

### Mutable Types to Avoid as Defaults
- Lists: `[]`
- Dictionaries: `{}`
- Sets: `set()`
- Dataclass instances
- Custom mutable objects
- Function calls that return mutable objects: `datetime.now()`, `[]`, etc.

### Safe Defaults
- `None`
- Immutable types: `int`, `str`, `tuple`, `frozenset`, `True`, `False`
- Immutable dataclasses: `@dataclass(frozen=True)`

## Consequences

### Positive
- Eliminates entire class of subtle state-sharing bugs
- Functions behave predictably across multiple calls
- Clear intent: `None` signals "will be constructed if not provided"

### Negative
- Requires boilerplate `if x is None: x = []` pattern
- Slightly more verbose function bodies

## Mechanical Enforcement

### Rule ID: PY-DEFAULT-001

### Pattern
```yaml
rules:
  - id: py-default-001
    patterns:
      - pattern: |
          def $FUNC(..., $ARG=$DEFAULT, ...):
              ...
      - metavariable-pattern:
          metavariable: $DEFAULT
          pattern-either:
            - pattern: "[]"
            - pattern: "{}"
            - pattern: "set()"
    message: |
      Mutable default argument detected. Use None and construct inside function.
      See: docs/adr/004-no-mutable-default-arguments.md
    severity: ERROR
    languages: [python]
    
  - id: py-default-002
    patterns:
      - pattern: |
          def $FUNC(..., $ARG=$DEFAULT(...), ...):
              ...
      - metavariable-regex:
          metavariable: $DEFAULT
          regex: '^(?!dataclass$).*'
    message: |
      Function call as default argument is evaluated once at definition time.
      See: docs/adr/004-no-mutable-default-arguments.md#function-calls
    severity: WARNING
    languages: [python]
```

### Valid Examples
```python
✅ def process_items(items: list[str] | None = None) -> list[str]:
    """Process items with safe default."""
    if items is None:
        items = []
    items.append("processed")
    return items

✅ def configure(options: dict[str, Any] | None = None) -> Config:
    """Configure with safe default."""
    if options is None:
        options = {}
    return Config(**options)

✅ def add_listeners(callbacks: list[Callable] | None = None) -> None:
    """Add callbacks with safe default."""
    if callbacks is None:
        callbacks = []
    for callback in callbacks:
        register(callback)

✅ def create_user(name: str, tags: tuple[str, ...] = ()) -> User:
    """Tuples are immutable, safe as defaults."""
    return User(name=name, tags=tags)
```

### Violations
```python
❌ def process_items(items: list[str] = []) -> list[str]:
    """Dangerous: items list is shared across calls!"""
    items.append("processed")
    return items

# First call
result1 = process_items()  # ["processed"]

# Second call - items still has previous value!
result2 = process_items()  # ["processed", "processed"]

❌ def configure(options: dict[str, Any] = {}) -> Config:
    """Dangerous: options dict is shared across calls!"""
    options.setdefault("debug", False)
    return Config(**options)

❌ def log_event(timestamp: datetime = datetime.now()) -> None:
    """Dangerous: timestamp evaluated once at function definition!"""
    print(f"Event at {timestamp}")

# All calls log the same timestamp!
log_event()  # 2024-01-15 10:00:00
time.sleep(5)
log_event()  # Still 2024-01-15 10:00:00

❌ def create_config(settings: Settings = Settings()) -> Config:
    """Dangerous: Settings instance shared across calls!"""
    return Config(settings)
```

## References
- [Google Python Style Guide 2.11: Default Argument Values](https://google.github.io/styleguide/pyguide.html#211-default-argument-values)
- Python Common Gotchas: Mutable Default Arguments