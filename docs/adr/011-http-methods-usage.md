# ADR-011: HTTP Methods Usage

## Status
Active

## Context
HTTP methods define the semantics of operations on resources. Misusing methods leads to unpredictable behavior, breaks caching, violates idempotency expectations, and causes client confusion. For example, using POST for reads prevents caching, while using GET for mutations violates safety guarantees.

Method properties (safe, idempotent, cacheable) are defined by RFC 9110 and must be honored for HTTP infrastructure to function correctly. Clients and intermediaries rely on these guarantees for retry logic, caching decisions, and request routing.

## Decision
**APIs must use HTTP methods according to their standardized semantics.** Methods must fulfill their defined properties: safe methods cannot have intended side effects, idempotent methods must produce the same effect regardless of repetition, and cacheable methods must support response reuse.

### Method Semantics

#### GET
- Purpose: Read single resource or collection
- Response: `200` (found), `404` (not found/empty collection)
- Must not have request body payload
- Safe, idempotent, cacheable

#### POST
- Purpose: Create resource(s) on collection endpoint
- Response: `201` (created) with `Location` header, `200`/`204` (if idempotent update), `202` (async)
- Resource identifier must not be in request body
- Not safe, not idempotent (unless designed for it), optionally cacheable
- Should consider idempotency using conditional key, secondary key, or `Idempotency-Key` header

#### PUT
- Purpose: Update (or create) entire resource
- Response: `200`/`204` (updated), `201` (created), `202` (async)
- Replaces entire resource at URL
- Not safe, idempotent, not cacheable
- Prefer POST for creation to maintain server control of identifiers

#### PATCH
- Purpose: Partial update of resource
- Response: `200`/`204` (updated), `202` (async)
- Requires patch document format (`application/merge-patch+json` or `application/json-patch+json`)
- Not safe, not idempotent (unless designed for it), not cacheable
- Preference order: (1) PUT with complete objects, (2) JSON Merge Patch, (3) JSON Patch, (4) POST

#### DELETE
- Purpose: Delete resource
- Response: `200`/`204` (deleted), `202` (async), `404` (not found), `410` (already deleted)
- After deletion, GET must return `404` or `410`
- Can use query parameters as filters
- Not safe, idempotent, not cacheable

#### HEAD
- Purpose: Retrieve headers only (no body)
- Identical semantics to GET but headers-only response
- Useful for checking resource updates via `ETag`
- Safe, idempotent, cacheable

#### OPTIONS
- Purpose: Inspect available operations
- Response: `Allow` header with comma-separated methods
- Safe, idempotent, not cacheable

### Idempotency Patterns

For POST and PATCH, consider idempotency using:

1. **Conditional Key**: `If-Match` header with resource version/hash (prevents concurrent updates)
2. **Secondary Key**: Unique business key in request body stored permanently (prevents duplicates)
3. **Idempotency Key**: `Idempotency-Key` header stored temporarily (ensures exact same response on retry)

### Special Cases

#### GET with Body
When query parameters exceed size limits:
1. Prefer URL-encoded query parameters
2. If impossible, use POST with body and document as `[GET with body payload]`

#### DELETE with Body
If DELETE requires non-filter data, use POST and document as `{DELETE-with-Body}`

#### Asynchronous Processing
Return `202` (accepted) with job resource:
- `POST /report-jobs` → `201` with job-id in `Location`
- `GET /report-jobs/{id}` → `200` with status
- `GET /reports/{id}` → `200` with result (when finished)

### Collection Format
Query parameters with multiple values:
- Comma-separated: `?param=value1,value2` (style: form, explode: false)
- Multiple parameters: `?param=value1&param=value2` (style: form, explode: true)

Headers with multiple values:
- Comma-separated: `Header: value1,value2` (style: simple, explode: false)

### Implicit Filtering
Document when responses are filtered based on authorization. API must explicitly state filtering is applied.

## Consequences

### Positive
- Predictable behavior across clients
- HTTP infrastructure (caching, proxies) works correctly
- Idempotency enables safe retries
- Clear resource lifecycle semantics
- Client developers can rely on standard method properties

### Negative
- PATCH requires choosing patch format
- Idempotency patterns add complexity
- GET with body requires special handling
- Asynchronous patterns require additional endpoints

## Mechanical Enforcement

### Rule ID: API-METHOD-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#148
    description: GET must not have request body
    message: "GET requests must not define requestBody"
    given: "$.paths[*].get"
    severity: error
    then:
      field: requestBody
      function: falsy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#148
    description: POST creating resources should return 201
    message: "POST operations should return 201 Created with Location header"
    given: "$.paths[*].post.responses"
    severity: warn
    then:
      field: "201"
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#148
    description: POST creating resources must include Location header
    message: "201 responses must include Location header"
    given: "$.paths[*].post.responses.201"
    severity: error
    then:
      field: headers.Location
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#154
    description: Collection parameters must define style and explode
    message: "Array parameters must explicitly set style and explode properties"
    given: "$.paths..parameters[?(@.schema.type == 'array')]"
    severity: error
    then:
      - field: style
        function: truthy
      - field: explode
        function: defined
```

### Valid Examples
```yaml
paths:
  /users:
    get:
      summary: List users
      parameters:
        - name: tags
          in: query
          schema:
            type: array
            items:
              type: string
          style: form
          explode: false
      responses:
        '200':
          description: Success
        '404':
          description: Collection not found

    post:
      summary: Create user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreate'
      responses:
        '201':
          description: Created
          headers:
            Location:
              schema:
                type: string
              description: URL of created user
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'

  /users/{id}:
    put:
      summary: Replace user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/User'
      responses:
        '200':
          description: Updated
        '201':
          description: Created

    patch:
      summary: Update user fields
      requestBody:
        required: true
        content:
          application/merge-patch+json:
            schema:
              $ref: '#/components/schemas/UserPatch'
      responses:
        '200':
          description: Updated

    delete:
      summary: Delete user
      responses:
        '204':
          description: Deleted
        '404':
          description: Not found
        '410':
          description: Already deleted
```

### Violations
```yaml
paths:
  /users:
    get:
      requestBody:  # Wrong: GET must not have body
        content:
          application/json:
            schema:
              type: object

    post:
      responses:
        '200':  # Wrong: should be 201 for creation
          description: Created
        '201':
          description: Created
          # Missing: Location header

  /users/{id}:
    delete:
      responses:
        '200':
          description: Deleted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        # Missing: 404 and 410 responses

  /search:
    get:
      parameters:
        - name: filters
          in: query
          schema:
            type: array
          # Missing: style and explode properties
```

## References
- [Zalando API Guidelines #148](https://opensource.zalando.com/restful-api-guidelines/#148)
- [Zalando API Guidelines #149](https://opensource.zalando.com/restful-api-guidelines/#149)
- [Zalando API Guidelines #229](https://opensource.zalando.com/restful-api-guidelines/#229)
- [Zalando API Guidelines #154](https://opensource.zalando.com/restful-api-guidelines/#154)
- RFC 9110 (HTTP Semantics)
- RFC 7396 (JSON Merge Patch)
- RFC 6902 (JSON Patch)