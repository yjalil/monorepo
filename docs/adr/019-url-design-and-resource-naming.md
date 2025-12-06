# ADR-019: URL Design and Resource Naming

## Status
Active

## Context
RESTful APIs use URLs to identify and access resources. Inconsistent URL design leads to confusion, implementation errors, and poor developer experience. URLs must be readable, predictable, and follow REST principles where resources (nouns) are identified through paths and operations are expressed through HTTP methods (verbs).

Common URL design problems include: mixing actions/verbs in paths, inconsistent casing conventions, overly nested structures, non-normalized paths with empty segments or trailing slashes, exposing database structure rather than business domain, and unclear resource boundaries. Each of these undermines API usability and maintainability.

## Decision
**APIs must follow standardized URL design principles for resource naming, path structure, and query parameters.** Use domain-specific nouns for resources, kebab-case for path segments, snake_case for query parameters, and avoid verbs in URLs.

### Base Path

**Do not use `/api` as base path.** All public resources should be under root `/`.

For non-public internal APIs, maintain separate specifications with distinct <<219, API audience>> classification. Base path is deployment configuration specified in OpenAPI server object.

### Resource Names

**Pluralize resource names:**
```http
✅ /orders
✅ /customers
❌ /order
❌ /customer
```

**Exception:** Resource singletons modeled as collections with cardinality 1 (`maxItems=minItems=1`), and pseudo-identifier `self` for authorization-derived identifiers.

### Path Segment Casing

**Use kebab-case for path segments** matching regex `^[a-z][a-z\-0-9]*$`:
```http
✅ /shipment-orders/{shipment-order-id}
❌ /shipmentOrders/{shipmentOrderId}
❌ /shipment_orders/{shipment_order_id}
```

First character must be lowercase letter, followed by letters, digits, or dashes.

### Resource Identifiers

**Use URL-friendly identifiers** matching regex `[a-zA-Z0-9:._\-/]*`:
- ASCII letters, numbers, underscore, minus, colon, period
- Slashes only for compound keys (see below)
- Never empty (prevents ambiguous paths)

```http
✅ /users/abc123
✅ /users/user:external:12345
❌ /users/
❌ /users/user@example.com
```

### Path Normalization

**Use normalized paths without empty segments or trailing slashes:**
```http
✅ /orders/{order-id}
❌ /orders/{order-id}/
❌ /orders//{order-id}
```

**Implementation:** Services should normalize paths by removing duplicate and trailing slashes before processing to handle non-compliant clients robustly, or reject non-normalized paths with clear error.

### Verb-Free URLs

**Keep URLs verb-free** - actions belong in HTTP methods, not paths:
```http
✅ PUT /article-locks/{article-id}
❌ POST /articles/{article-id}/lock

✅ POST /order-cancellations
❌ POST /orders/{order-id}/cancel
```

Think of resources as letter boxes receiving messages rather than actions to perform.

### Domain-Specific Names

**Use domain-specific resource names** from business domain model:
```http
✅ /sales-order-items
❌ /order-items  (too generic)
❌ /items  (far too generic)
```

Reduces need for external documentation and makes API self-descriptive.

### Resource Structure

**Identify resources and sub-resources via path segments:**
```http
/resources/{resource-id}/sub-resources/{sub-resource-id}
```

Each sub-path should be valid reference to resource or resource set:
```http
✅ /shopping-carts/de:1681e6b88ec1/items/1
✅ /shopping-carts/de:1681e6b88ec1
✅ /shopping-carts
```

**Exception:** Use `self` pseudo-identifier when resource ID comes from authorization:
```http
/employees/self
/employees/self/personal-details
```

### Compound Keys

**May expose compound keys in natural form with slashes:**
```http
/shopping-carts/{country}/{session-id}
/article-size-advices/{sku}/{sales-channel}
/api-specifications/{repository-name}/{artifact-name}:{tag}
```

**Critical:** Apply compound key abstraction consistently - expose as opaque technical ID in responses:
```http
# Search with components
GET /article-size-advices?skus=sku-1&sales_channel_id=sid-1
=> {"items": [{"id": "id-1", ...}]}

# Access with opaque ID
GET /article-size-advices/id-1
=> {"id": "id-1", "sku": "sku-1", "sales_channel_id": "sid-1", ...}

# Create with components
POST /article-size-advices {"sku": "sku-1", "sales_channel_id": "sid-1", ...}
=> {"id": "id-1", ...}
```

### Nested vs Non-Nested URLs

**Nested URLs:** Use when sub-resource only accessible via parent and cannot exist independently:
```http
/shopping-carts/de/1681e6b88ec1/cart-items/1
```

**Non-nested URLs:** Use when resource has globally unique ID and can be accessed directly:
```http
/customers/1637asikzec1
/sales-orders/5273gh3k525a
```

### Resource Limits

**Limit number of resource types (4-8 recommended):**
- Resource type = set of highly related resources (collection, members, direct sub-resources)
- More types suggest need for API splitting into separate domains
- One API should model complete business processes

**Limit sub-resource nesting (≤3 levels):**
```http
✅ /resources/{id}/sub-resources/{sub-id}/items/{item-id}
❌ /resources/{id}/sub/{sub-id}/nested/{nested-id}/deep/{deep-id}
```

More nesting increases complexity and URL length (browser limit: 2000 chars).

### Query Parameters

**Use snake_case (never camelCase) for query parameters:**
```http
✅ ?sales_channel_id=123
❌ ?salesChannelId=123
```

**Conventional query parameters:**
- `q` - Default search query (with entity-specific alias like `sku`)
- `sort` - Comma-separated fields with `+`/`-` prefix: `?sort=+id,-created_at`
- `fields` - Field filtering for partial responses (see ADR-017)
- `embed` - Sub-entity expansion (see ADR-017)
- `offset` - Numeric offset for pagination
- `cursor` - Opaque page pointer for cursor-based pagination
- `limit` - Page size limit

## Consequences

### Positive
- **Predictable URLs:** Consistent conventions enable intuitive API navigation
- **Self-documenting:** Domain-specific names reduce documentation needs
- **Clean separation:** Verbs in HTTP methods, nouns in paths
- **URL safety:** ASCII-only identifiers avoid encoding issues
- **Maintainable:** Limited nesting and resource types keep complexity manageable
- **Interoperable:** Standard query parameters enable tooling and client libraries

### Negative
- **Strictness overhead:** Teams must learn and follow multiple conventions
- **Refactoring limits:** Compound keys exposed in URLs harder to evolve
- **Naming discussions:** Domain-specific names require business alignment
- **Path normalization:** Not all frameworks support out-of-the-box
- **Query case mismatch:** snake_case queries vs kebab-case paths

## Mechanical Enforcement

### Rule ID: API-URL-001

### OpenAPI Validation
```yaml
rules:
  - id: api-url-001-no-api-prefix
    description: Do not use /api as base path
    message: |
      Avoid /api base path. Use root / for public APIs.
      See: docs/adr/019-url-design-and-resource-naming.md
    severity: warning
    given: $.servers[*].url
    then:
      function: pattern
      functionOptions:
        notMatch: "/api(/|$)"

  - id: api-url-001-kebab-case-paths
    description: Path segments must use kebab-case
    message: |
      Path segments must match ^[a-z][a-z0-9-]*$ (kebab-case).
      See: docs/adr/019-url-design-and-resource-naming.md
    severity: error
    given: $.paths.*~
    then:
      function: pattern
      functionOptions:
        match: "^(/[a-z][a-z0-9-]*|/\\{[a-z][a-z0-9-]*\\})+/?$"

  - id: api-url-001-no-trailing-slash
    description: Paths must not have trailing slashes
    message: |
      Remove trailing slash from path.
      See: docs/adr/019-url-design-and-resource-naming.md
    severity: error
    given: $.paths.*~
    then:
      function: pattern
      functionOptions:
        notMatch: ".+/$"

  - id: api-url-001-plural-resources
    description: Resource names should be pluralized
    message: |
      Use plural resource names (e.g., /orders not /order).
      See: docs/adr/019-url-design-and-resource-naming.md
    severity: warning
    given: $.paths.*~
    then:
      function: pattern
      functionOptions:
        # Check common singular forms
        notMatch: "/(order|customer|product|item|user|account)(/|$|\\{)"

  - id: api-url-001-no-verbs
    description: URLs should not contain action verbs
    message: |
      Remove verbs from URL. Use HTTP methods for actions.
      See: docs/adr/019-url-design-and-resource-naming.md
    severity: error
    given: $.paths.*~
    then:
      function: pattern
      functionOptions:
        notMatch: "/(create|update|delete|cancel|lock|unlock|activate|deactivate|submit|approve|reject)(/|$|\\{)"

  - id: api-url-001-snake-case-params
    description: Query parameters must use snake_case
    message: |
      Query parameters must use snake_case (not camelCase).
      See: docs/adr/019-url-design-and-resource-naming.md
    severity: error
    given: $.paths[*][*].parameters[?(@.in=="query")].name
    then:
      function: pattern
      functionOptions:
        match: "^[a-z][a-z0-9_]*$"

  - id: api-url-001-nesting-depth
    description: Limit URL nesting to 3 levels
    message: |
      URL nesting too deep (max 3 sub-resource levels).
      See: docs/adr/019-url-design-and-resource-naming.md
    severity: warning
    given: $.paths.*~
    then:
      function: pattern
      functionOptions:
        # More than 4 path segments (excluding root)
        notMatch: "^(/[^/]+){5,}"
```

### Valid Examples
```http
✅ Clean resource path with kebab-case
GET /sales-orders/{order-id}

✅ Nested sub-resource (2 levels)
GET /customers/{customer-id}/addresses/{address-id}

✅ Self pseudo-identifier
GET /employees/self/personal-details

✅ Compound key
GET /shopping-carts/{country}/{session-id}

✅ Query with snake_case
GET /orders?sort=+created_at&sales_channel_id=web

✅ Verb-free with HTTP method expressing action
PUT /article-locks/{article-id}
DELETE /article-locks/{article-id}

✅ Domain-specific resource name
GET /shipment-orders/{shipment-order-id}
```

### Invalid Examples
```http
❌ /api base path
GET /api/orders

❌ camelCase in path
GET /shipmentOrders/{orderId}

❌ Trailing slash
GET /orders/

❌ Empty path segment
GET /orders//123

❌ Singular resource name
GET /order/{order-id}

❌ Verb in URL
POST /orders/{order-id}/cancel
GET /articles/{article-id}/lock

❌ camelCase query parameter
GET /orders?salesChannelId=web

❌ Too much nesting (4+ levels)
GET /customers/{id}/orders/{order-id}/items/{item-id}/options/{option-id}

❌ Non-domain-specific naming
GET /items/{id}  # Too generic
GET /data/{id}   # Meaningless
```

## Implementation Guidance

### Path Design Process
1. Identify domain entities (nouns from ubiquitous language)
2. Determine resource relationships (nested vs independent)
3. Apply pluralization consistently
4. Use kebab-case for multi-word resources
5. Limit nesting depth to 3 levels
6. Verify no verbs appear in paths

### Resource Identifier Strategy
- Generate opaque IDs (UUIDs) for primary identifiers
- Use compound keys only when natural business identifier
- Abstract compound keys in responses as opaque technical IDs
- Validate identifiers match URL-friendly pattern

### Path Normalization Implementation
```python
# Example: Normalize before routing
def normalize_path(path: str) -> str:
    # Remove duplicate slashes
    while '//' in path:
        path = path.replace('//', '/')
    # Remove trailing slash (except root)
    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]
    return path
```

## References
- Zalando RESTful API Guidelines #134, #135, #136, #138, #139, #140, #141, #142, #143, #145, #146, #147, #228, #241
- REST Architectural Style (Roy Fielding)
- RFC 3986 (URI Generic Syntax)

## Related ADRs
- ADR-016: Pagination
- ADR-017: API Performance Optimization
- ADR-014: JSON Payload Standards
