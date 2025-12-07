# ADR-001: Import from Top-Level Modules

## Status
Active

## Context
When code is refactored and components move between modules, direct imports create widespread breaking changes. For example, moving `check_email` from `utils.validators` to `utils.email_validators` requires updating every file that imports it directly.

Additionally, qualified names make dependencies explicit at call sites, improving code readability and making it clear where functionality comes from.

## Decision
Import from the top-level module and use qualified names, rather than importing individual components.

**Exceptions:**
- `typing` module: Type hints are pervasive and don't represent runtime dependencies
- `collections.abc` module: Abstract base classes are protocol definitions, not implementations

## Consequences

### Positive
- Refactoring resilience: Moving components between modules only requires updating one import
- Explicit dependencies: Call sites show `validators.check_email()` instead of ambiguous `check_email()`
- Reduced import ceremony: One import per module instead of long lists of components

### Negative
- Slightly more verbose at call sites
- Standard library imports become less idiomatic (`enum.Enum` vs `Enum`)

## Mechanical Enforcement

### Rule ID: PY-IMPORT-001

### Pattern
```yaml
rules:
  - id: py-import-001
    patterns:
      - pattern: from $MODULE import $ITEM
      - pattern-not: from typing import $ITEM
      - pattern-not: from collections.abc import $ITEM
    message: |
      Import from top-level module instead of individual component.
      See: docs/adr/001-import-from-top-level-modules.md
    severity: ERROR
    languages: [python]
```

### Valid Examples
```python
✅ import dataclasses
   @dataclasses.dataclass
   class User: ...

✅ import enum
   class Status(enum.Enum): ...

✅ from utils import validators
   validators.check_email(email)

✅ from typing import Optional, List  # Exception
✅ from collections.abc import Sequence  # Exception
```

### Violations
```python
❌ from dataclasses import dataclass
   @dataclass
   class User: ...

❌ from enum import Enum
   class Status(Enum): ...

❌ from utils.validators import check_email
   check_email(email)
```

## References
- Google Python Style Guide: Imports