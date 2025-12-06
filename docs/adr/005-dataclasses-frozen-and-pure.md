# ADR-005: Dataclasses Must Be Frozen and Pure

## Status
Active

## Context
Dataclasses represent data structures, not behavior. Mixing data and complex logic leads to maintenance issues and violates the separation between data models and business logic. Mutable dataclasses create unexpected aliasing bugs where changes to one reference affect all references.

Additionally, dataclasses with side effects (I/O operations, timestamp generation) create hidden dependencies that make code difficult to test and reason about. A dataclass should be a transparent container for data, nothing more.

## Decision
All dataclasses must follow these rules:

1. **Frozen by default**: All dataclasses use `@dataclass(frozen=True)` for immutability
2. **Properties only**: Any methods must be `@property` decorators computing values from existing fields
3. **No side effects**: No I/O operations, no `datetime.now()`, no external calls

### Rationale

**Why frozen?**
- Prevents accidental mutation
- Makes data flow explicit (new data = new instance)
- Enables safe sharing across contexts
- Hashable by default (can use as dict keys, in sets)

**Why properties only?**
- Dataclasses are data containers, not service objects
- Complex behavior belongs in services or utilities
- Properties provide convenient derived values without adding state

**Why no side effects?**
- Accessing a field shouldn't trigger I/O
- `datetime.now()` creates non-deterministic data
- Side effects make testing difficult
- Violates principle of data as pure values

### When You Need Mutability

If you need evolving state, dataclasses are the wrong tool. Use instead:
- **Builder pattern**: Construct immutable result step by step
- **Dictionary**: For truly dynamic data
- **Class with explicit methods**: For stateful objects with behavior
- **Functional updates**: Create new frozen instances with changes

## Consequences

### Positive
- Data structures are predictable and safe to share
- No hidden side effects when accessing fields
- Clear separation: data in dataclasses, behavior in services/utils
- Easier testing (no mocking timestamps in data objects)

### Negative
- Cannot modify dataclasses in place (must create new instances)
- No convenient `__post_init__` for complex initialization
- Properties limited to pure computations

## Mechanical Enforcement

### Rule IDs
- PY-DATA-001: Dataclasses must be frozen
- PY-DATA-002: Dataclass methods must be properties
- PY-DATA-003: No datetime.now() in dataclasses

### Patterns
```yaml
rules:
  - id: py-data-001
    patterns:
      - pattern: |
          @dataclass
          class $CLASS:
              ...
      - pattern-not: |
          @dataclass(frozen=True)
          class $CLASS:
              ...
      - pattern-not: |
          @dataclass(..., frozen=True, ...)
          class $CLASS:
              ...
    message: |
      Dataclass must be frozen. Use @dataclass(frozen=True).
      See: docs/adr/005-dataclasses-frozen-and-pure.md#frozen-by-default
    severity: ERROR
    languages: [python]

  - id: py-data-002
    patterns:
      - pattern-inside: |
          @dataclass(...)
          class $CLASS:
              ...
      - pattern: |
          def $METHOD(self, ...):
              ...
      - pattern-not: |
          @property
          def $METHOD(self):
              ...
      - metavariable-regex:
          metavariable: $METHOD
          regex: '^(?!__).*'
    message: |
      Dataclass methods must be @property decorators. Move logic to services/utils.
      See: docs/adr/005-dataclasses-frozen-and-pure.md#properties-only
    severity: ERROR
    languages: [python]

  - id: py-data-003
    patterns:
      - pattern-inside: |
          @dataclass(...)
          class $CLASS:
              ...
      - pattern: dt.now()
    message: |
      No datetime.now() in dataclasses. Pass timestamps as constructor arguments.
      See: docs/adr/005-dataclasses-frozen-and-pure.md#no-side-effects
    severity: ERROR
    languages: [python]
```

### Valid Examples
```python
✅ @dataclass(frozen=True)
class User:
    """User data model."""
    first_name: str
    last_name: str
    email: str
    created_at: datetime
    
    @property
    def full_name(self) -> str:
        """Computed from existing fields."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def domain(self) -> str:
        """Pure computation from email field."""
        return self.email.split("@")[1]

✅ @dataclass(frozen=True)
class Order:
    """Order with computed total."""
    items: tuple[Item, ...]  # Immutable sequence
    tax_rate: Decimal
    
    @property
    def subtotal(self) -> Decimal:
        """Sum of item prices."""
        return sum(item.price for item in self.items)
    
    @property
    def total(self) -> Decimal:
        """Total with tax."""
        return self.subtotal * (1 + self.tax_rate)

✅ # Timestamp passed from outside
def create_user(name: str, email: str) -> User:
    """Create user with current timestamp."""
    return User(
        name=name,
        email=email,
        created_at=datetime.now()  # Side effect in service, not dataclass
    )
```

### Violations
```python
❌ @dataclass  # Missing frozen=True
class User:
    name: str
    email: str

❌ @dataclass(frozen=True)
class User:
    name: str
    created_at: datetime = datetime.now()  # Side effect in dataclass!

❌ @dataclass(frozen=True)
class Order:
    items: list[Item]
    
    def add_item(self, item: Item) -> None:  # Method, not property
        """This violates frozen anyway, but also shouldn't be a method."""
        self.items.append(item)

❌ @dataclass(frozen=True)
class User:
    name: str
    
    def save_to_db(self) -> None:  # I/O method in dataclass
        """Data models shouldn't know about persistence."""
        database.save(self)

❌ @dataclass(frozen=True)
class Report:
    data: dict
    
    @property
    def generated_at(self) -> datetime:
        """Side effect in property!"""
        return datetime.now()  # Different value each access!
```

## References
- /mnt/project/dataclasses-utils.md
- [Python dataclasses documentation](https://docs.python.org/3/library/dataclasses.html)

## Examples: Handling Mutability Needs

### Instead of mutable dataclass, use builder pattern:
```python
class UserBuilder:
    """Build user incrementally, produce frozen result."""
    def __init__(self):
        self._name = None
        self._email = None
    
    def with_name(self, name: str) -> "UserBuilder":
        self._name = name
        return self
    
    def with_email(self, email: str) -> "UserBuilder":
        self._email = email
        return self
    
    def build(self) -> User:
        return User(name=self._name, email=self._email)

# Usage
user = UserBuilder().with_name("Alice").with_email("alice@example.com").build()
```

### Instead of methods, use functions:
```python
@dataclass(frozen=True)
class Order:
    items: tuple[Item, ...]
    
    @property
    def total(self) -> Decimal:
        return sum(item.price for item in self.items)

# Business logic in service, not dataclass
def apply_discount(order: Order, discount: Decimal) -> Order:
    """Create new order with discounted items."""
    discounted_items = tuple(
        Item(name=i.name, price=i.price * (1 - discount))
        for i in order.items
    )
    return Order(items=discounted_items)
```