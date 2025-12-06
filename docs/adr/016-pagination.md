# ADR-016: Pagination

## Status
Active

## Context
APIs returning collections must protect services from overload and support efficient client iteration. Without pagination, returning large datasets causes memory exhaustion, slow response times, and poor user experience. Pagination techniques have different tradeoffs for usability, consistency under concurrent modifications, and performance with large datasets.

Offset-based pagination (`?offset=100&limit=20`) is simple but suffers from anomalies when data changes between requests and poor performance on large datasets. Cursor-based pagination uses opaque tokens pointing to page positions, providing stable iteration and better performance but less framework support.

## Decision
**APIs must support pagination for all collections potentially larger than a few hundred entries.** Prefer cursor-based pagination over offset-based. Use standardized response structure with navigation links and avoid total result counts.

### Pagination Approach

**Preferred: Cursor-based pagination**
- Opaque cursor encodes page position
- Better performance on large datasets and NoSQL
- Stable under concurrent data changes
- Cursor encodes: position, direction, filters, validation hash

**Alternative: Offset-based pagination**
- Use only when jumping to specific page required
- Acknowledge limitations: anomalies under data changes, poor performance at scale

**Critical:** Cursors must be opaque to clients (never inspected or constructed by client code).

### Standard Response Structure
```yaml
ResponsePage:
  type: object
  required:
    - items
  properties:
    self:
      type: string
      format: uri
      description: Link to current page
    first:
      type: string
      format: uri
      description: Link to first page
    prev:
      type: string
      format: uri
      description: Link to previous page (omit if first page)
    next:
      type: string
      format: uri
      description: Link to next page (omit if last page)
    last:
      type: string
      format: uri
      description: Link to last page
    query:
      type: object
      description: Applied query filters (for GET-with-body)
    items:
      type: array
      description: Page content
```

### Pagination Links (Preferred)

Use full URIs for navigation:
```json
{
  "self": "https://api.example.com/users?cursor=abc123",
  "first": "https://api.example.com/users?cursor=first",
  "prev": "https://api.example.com/users?cursor=xyz789",
  "next": "https://api.example.com/users?cursor=def456",
  "last": "https://api.example.com/users?cursor=last",
  "items": [
    {"id": "user-1", "name": "Alice"},
    {"id": "user-2", "name": "Bob"}
  ]
}
```

### Query Parameters

Standard names (see ADR on query parameters):
- `cursor`: Page position token (cursor-based)
- `offset`: Starting position (offset-based)
- `limit`: Page size

### Total Count Handling

**Avoid providing total result counts** due to:
- Costly operations (full index scans)
- Difficult to cache for complex queries
- Expensive as datasets grow
- Clients integrate against counts, making removal difficult

If required, support via `Prefer: return=total-count` header.

### GET-with-Body Support

For complex queries using POST-as-GET:
- Include `query` object in response
- Clients can use `query` + pagination link for next page
- Ensures filter consistency across pages

## Consequences

### Positive
- Service protection from overload
- Efficient client iteration
- Cursor-based stable under data changes
- Better performance on large datasets
- Consistent pagination patterns across APIs
- Navigation links simplify client code

### Negative
- Cursor-based less familiar than offset
- Cannot jump to arbitrary page with cursors
- Must encode filters in cursor (implementation complexity)
- Opaque cursors harder to debug
- Total counts expensive (avoided by design)

## Mechanical Enforcement

### Rule ID: API-PAGE-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#159
    description: Collections should support pagination
    message: "Collection responses should include pagination links (next, prev, self)"
    given: "$.paths[*].get.responses.200.content.application/json.schema.properties"
    severity: warn
    then:
      field: items
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#248
    description: Pagination responses should include navigation links
    message: "Paginated responses should include self, first, prev, next, last links"
    given: "$.paths[*].get.responses.200.content.application/json.schema.properties[?(@property == 'items')]^"
    severity: warn
    then:
      - field: self
        function: truthy
      - field: next
        function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#161
    description: Pagination links should be full URIs
    message: "Pagination links must use format: uri"
    given: "$.paths[*].get.responses.200.content.application/json.schema.properties[?(@property =~ /(self|first|prev|next|last)/)]"
    severity: error
    then:
      field: format
      function: pattern
      functionOptions:
        match: "^uri$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#254
    description: Avoid total count in pagination
    message: "Avoid including 'total' or 'count' in pagination responses - use Prefer header if needed"
    given: "$.paths[*].get.responses.200.content.application/json.schema.properties"
    severity: warn
    then:
      field: total
      function: falsy
```

### Valid Examples
```yaml
components:
  schemas:
    UserPage:
      type: object
      required:
        - items
      properties:
        self:
          type: string
          format: uri
          example: "https://api.example.com/users?cursor=abc123"
        first:
          type: string
          format: uri
          example: "https://api.example.com/users?cursor=first"
        prev:
          type: string
          format: uri
          example: "https://api.example.com/users?cursor=xyz789"
        next:
          type: string
          format: uri
          example: "https://api.example.com/users?cursor=def456"
        last:
          type: string
          format: uri
          example: "https://api.example.com/users?cursor=last"
        items:
          type: array
          items:
            $ref: '#/components/schemas/User'

paths:
  /users:
    get:
      summary: List users with pagination
      parameters:
        - name: cursor
          in: query
          schema:
            type: string
          description: Opaque pagination cursor
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: Paginated user list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserPage'
```

### Violations
```yaml
components:
  schemas:
    UserList:
      type: object
      properties:
        users:  # Wrong: should be 'items' per standard
          type: array
          items:
            $ref: '#/components/schemas/User'
        total:  # Wrong: avoid total count
          type: integer
        page:  # Wrong: non-standard pagination field
          type: integer
        # Missing: self, first, prev, next, last links

    ProductPage:
      properties:
        items:
          type: array
          items:
            $ref: '#/components/schemas/Product'
        next:
          type: string  # Wrong: missing format: uri
        prev:
          type: integer  # Wrong: should be string with format: uri

paths:
  /orders:
    get:
      parameters:
        - name: page  # Wrong: non-standard, use 'cursor' or 'offset'
          in: query
          schema:
            type: integer
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array  # Wrong: should be object with pagination fields
                items:
                  $ref: '#/components/schemas/Order'
```

## References
- [Zalando API Guidelines #159](https://opensource.zalando.com/restful-api-guidelines/#159)
- [Zalando API Guidelines #160](https://opensource.zalando.com/restful-api-guidelines/#160)
- [Zalando API Guidelines #161](https://opensource.zalando.com/restful-api-guidelines/#161)
- [Zalando API Guidelines #248](https://opensource.zalando.com/restful-api-guidelines/#248)
- [Zalando API Guidelines #254](https://opensource.zalando.com/restful-api-guidelines/#254)
- [Twitter API Cursoring](https://dev.twitter.com/overview/api/cursoring)
- [Facebook Graph API Results](https://developers.facebook.com/docs/graph-api/results)