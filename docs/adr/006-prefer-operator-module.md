# ADR-006: Prefer Operator Module for Functional Operations

## Status
Active

## Context
Python supports both inline operators (`+`, `*`, `/`) and their functional equivalents in the `operator` module (`operator.add`, `operator.mul`, `operator.truediv`). When passing operations as first-class functions to `map()`, `reduce()`, `sorted()`, or similar functional programming constructs, the choice between lambda and operator module affects code clarity and maintainability.

Using lambda functions for simple operations creates anonymous functions that are harder to trace in debugging and less explicit in imports. The operator module provides named functions that make dependencies visible and operations greppable.

## Decision
**Use the `operator` module instead of lambda functions for built-in operations when passing them as first-class functions.**

### Use operator module when:
- Passing operations to `map()`, `reduce()`, `filter()`
- Using operations as key functions in `sorted()`, `min()`, `max()`
- Creating operation callbacks or functional pipelines

### Use direct operators when:
- Writing inline expressions: `result = a * b`
- Simple arithmetic in comprehensions: `[x * 2 for x in items]`

### Acceptable uses of `*`:
1. **Glob patterns**: `*.py`, `**/*.md` for file matching
2. **Unpacking**: `*args`, `**kwargs` in function signatures and calls
3. **Direct expressions**: `a * b` in normal arithmetic

## Consequences

### Positive
- **Import visibility**: `from operator import mul` shows operations upfront
- **Greppability**: Searching for `operator.mul` finds all uses of multiplication as function
- **Distinguishes protocol usage**: Makes `__mul__` override usage explicit
- **Consistency**: All functional operations use the same pattern
- **Easier to spot violations**: Scanning for `*` mostly shows glob/unpacking, not buried lambdas

### Negative
- Requires familiarity with operator module
- One more import to manage
- Slightly more verbose than lambda for newcomers

## Mechanical Enforcement

No automated pattern detection. This rule requires code review judgment to distinguish functional contexts from inline expressions.

**Review checklist:**
- Is an operation being passed as a function argument?
- Could `operator.X` replace a simple lambda?
- Would the operator module import improve clarity?

## References
- [Google Python Style Guide: Lambda Functions](https://google.github.io/styleguide/pyguide.html#219-lambda-functions)
- [Python operator module documentation](https://docs.python.org/3/library/operator.html)

## Examples

### Good: Operator module for functional operations
```python
from operator import mul, add, itemgetter
from functools import reduce

✅ # Reduce with multiplication
total = reduce(mul, numbers)

✅ # Sort by attribute
sorted_users = sorted(users, key=itemgetter('age'))

✅ # Map with operation
doubled = list(map(mul, numbers, [2] * len(numbers)))

✅ # Custom sorting with multiple keys
sorted_items = sorted(
    items,
    key=itemgetter('category', 'price')
)
```

### Good: Direct operators for inline expressions
```python
✅ # Simple arithmetic
result = a * b + c

✅ # Comprehensions
squares = [x * x for x in range(10)]

✅ # Inline calculations
total = sum(item.price * item.quantity for item in cart)
```

### Bad: Lambda for simple operations
```python
❌ # Lambda when operator.mul would work
total = reduce(lambda x, y: x * y, numbers)

❌ # Lambda for attribute access
sorted_users = sorted(users, key=lambda u: u.age)

❌ # Lambda for arithmetic
doubled = list(map(lambda x: x * 2, numbers))
```

### Clarification: Wildcard usage

The `*` character has distinct meanings in Python:
```python
✅ # File globbing - perfectly fine
files = Path(".").glob("**/*.py")

✅ # Unpacking - necessary and clear
def process(*args, **kwargs):
    items = [*list1, *list2]
    settings = {**defaults, **overrides}

✅ # Direct multiplication - fine in expressions
result = price * quantity

❌ # Import wildcard - forbidden (enforced by Ruff F403/F405)
from module import *
```

## Common operator module functions
```python
from operator import (
    # Arithmetic
    add, sub, mul, truediv, floordiv, mod, pow,
    
    # Comparison
    eq, ne, lt, le, gt, ge,
    
    # Logical
    and_, or_, not_,
    
    # Attribute/item access
    attrgetter, itemgetter, methodcaller,
)

# Usage examples
from functools import reduce

sum_all = reduce(add, numbers)
product = reduce(mul, values)
names = list(map(attrgetter('name'), users))
prices = list(map(itemgetter('price'), items))
```