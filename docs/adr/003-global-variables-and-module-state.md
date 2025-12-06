# ADR-003: Global Variables and Module-Level State

## Status
Active

## Context
Global mutable state creates hidden dependencies between functions and makes code difficult to test and reason about. However, module-level constants and carefully managed internal state (like caches) serve legitimate purposes.

Python's module system allows variables at module scope, but unrestricted use leads to maintenance problems and unexpected behavior in multi-threaded or async contexts.

## Decision
**Avoid global variables. Use module-level constants and internal state sparingly.**

### Allowed Patterns

1. **Module-level constants**: Immutable configuration values
```python
   MAX_TIMEOUT = 30
   DEFAULT_ENCODING = "utf-8"
   API_BASE_URL = "https://api.example.com"
```

2. **Internal module state**: Mutable state prefixed with `_`, accessed only through module functions
```python
   _cache = {}
   
   def get_cached(key):
       return _cache.get(key)
   
   def set_cached(key, value):
       _cache[key] = value
```

### Forbidden Patterns
```python
❌ current_user = None      # Mutable global state
❌ request_count = 0        # Global counter
❌ is_debug_mode = True     # Mutable flag
```

### Alternative Approaches

- **Dependency injection**: Pass dependencies as function parameters
- **Context managers**: Use `with` statements for scoped state
- **Class instances**: Encapsulate state in objects
- **Configuration objects**: Load config once, pass around as needed

## Consequences

### Positive
- Code is easier to test (no hidden global state)
- Functions are self-contained and predictable
- Reduced bugs from unexpected state mutations
- Clear boundaries between immutable config and mutable state

### Negative
- Requires more explicit parameter passing
- Cache invalidation must be managed carefully
- Internal state still creates coupling within a module

## Mechanical Enforcement

No automated pattern detection. This rule requires code review judgment to distinguish legitimate constants from problematic globals.

**Review checklist:**
- Is the variable truly constant (immutable value)?
- If mutable, is it prefixed with `_` and accessed through functions?
- Could this state be passed as a parameter instead?
- Is this creating hidden coupling between functions?

## References
- [Google Python Style Guide 2.5: Global Variables](https://google.github.io/styleguide/pyguide.html#25-global-variables)

## Examples

### Good: Cache with controlled access
```python
_user_cache: dict[str, User] = {}

def get_user(user_id: str) -> User | None:
    """Retrieve user from cache or None if not found."""
    return _user_cache.get(user_id)

def cache_user(user: User) -> None:
    """Store user in cache."""
    _user_cache[user.id] = user

def clear_user_cache() -> None:
    """Clear all cached users."""
    _user_cache.clear()
```

### Bad: Exposed mutable state
```python
current_session = None  # Global mutable, no access control

def login(user):
    global current_session
    current_session = create_session(user)

def logout():
    global current_session
    current_session = None
```

### Good: Pass state explicitly
```python
def process_request(request: Request, session: Session) -> Response:
    """Process request with explicit session dependency."""
    user = session.get_user()
    return create_response(user)
```