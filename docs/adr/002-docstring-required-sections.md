# ADR-002: Docstrings Must Include Required Sections

## Status
Active

## Context
Python's dynamic nature makes it difficult to understand function contracts without reading implementation code. Google Python Style Guide mandates comprehensive docstrings that document all parameters, return values, and exceptions. This enables developers to use functions confidently without inspecting their internals.

The standard library and many third-party packages fail to document raised exceptions, leading to unexpected errors in production. Enforcing complete docstrings at development time prevents these issues.

## Decision
All public functions must include Google-style docstrings with required sections based on the function's signature:

1. **Args section**: Required if function has parameters
2. **Returns section**: Required if function returns a value (not None)
3. **Raises section**: Required if function raises exceptions

Private functions (prefixed with `_`) are exempt but encouraged to follow the same pattern.

## Consequences

### Positive
- Function contracts are self-documenting
- Callers know what exceptions to handle
- Reduces time spent reading implementation code
- Catches undocumented error cases during development

### Negative
- Additional documentation burden
- Requires discipline to keep docstrings synchronized with code changes
- May feel verbose for simple functions

## Mechanical Enforcement

### Rule IDs
- PY-DOC-001: Functions with parameters must document Args
- PY-DOC-002: Functions with return values must document Returns
- PY-DOC-003: Functions that raise must document Raises

### Patterns
```yaml
rules:
  - id: py-doc-001
    patterns:
      - pattern: |
          def $FUNC($PARAM):
              """$DOCSTRING"""
              ...
      - metavariable-regex:
          metavariable: $DOCSTRING
          regex: '^(?!.*Args:).*$'
    paths:
      exclude:
        - "**/__init__.py"
        - "**/test_*.py"
        - "**/*_test.py"
    message: |
      Function has parameters but docstring missing 'Args:' section.
      See: docs/adr/002-docstring-required-sections.md#args-section
    severity: WARNING
    languages: [python]

  - id: py-doc-002
    patterns:
      - pattern: |
          def $FUNC(...):
              """$DOCSTRING"""
              ...
              return $VALUE
      - metavariable-regex:
          metavariable: $DOCSTRING
          regex: '^(?!.*Returns:).*$'
    paths:
      exclude:
        - "**/__init__.py"
        - "**/test_*.py"
        - "**/*_test.py"
    message: |
      Function returns a value but docstring missing 'Returns:' section.
      See: docs/adr/002-docstring-required-sections.md#returns-section
    severity: WARNING
    languages: [python]

  - id: py-doc-003
    patterns:
      - pattern: |
          def $FUNC(...):
              """$DOCSTRING"""
              ...
              raise $EXCEPTION
      - metavariable-regex:
          metavariable: $DOCSTRING
          regex: '^(?!.*Raises:).*$'
    paths:
      exclude:
        - "**/__init__.py"
        - "**/test_*.py"
        - "**/*_test.py"
    message: |
      Function raises exceptions but docstring missing 'Raises:' section.
      See: docs/adr/002-docstring-required-sections.md#raises-section
    severity: WARNING
    languages: [python]
```

### Valid Examples
```python
✅ def calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal:
    """Calculate total price including tax.
    
    Args:
        items: List of items to total.
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%).
    
    Returns:
        Total price with tax applied.
    
    Raises:
        ValueError: If tax_rate is negative.
    """
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)

✅ def _internal_helper():
    """Private function - docstring optional but recommended."""
    pass
```

### Violations
```python
❌ def calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal:
    """Calculate total price including tax."""
    # Missing: Args, Returns, Raises sections
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)

❌ def process_data(data):
    """Process the data.
    
    Returns:
        Processed data.
    """
    # Missing: Args section (has parameter)
    return data.strip()

❌ def validate_email(email: str) -> bool:
    """Check if email is valid.
    
    Args:
        email: Email address to validate.
    """
    # Missing: Returns section (returns bool)
    return "@" in email
```

## References
- [Google Python Style Guide 3.8: Comments and Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)