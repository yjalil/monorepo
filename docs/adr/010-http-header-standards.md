# ADR-010: HTTP Header Standards

## Status
Active

## Context
HTTP headers provide metadata about requests and responses, including content negotiation, flow control, authentication, and protocol processing. Standard headers enable interoperability, while proprietary headers should be minimized to prevent vendor lock-in and complexity.

Headers must be consistently named and used correctly. For example, `Content-Location` and `Location` headers have different semantics affecting caching behavior. Flow tracking requires end-to-end header propagation across service boundaries.

## Decision
**APIs must use standard HTTP headers correctly and follow naming conventions.** Proprietary headers are discouraged except for domain-specific generic context that must pass end-to-end through service chains.

### Header Naming Convention
Use kebab-case with uppercase separate words (following RFC 2616, RFC 4229, RFC 9110):
```
If-Modified-Since
Accept-Encoding
Content-Type
X-Flow-ID
```

### Standard Headers Usage

#### Content Headers
Use `Content-*` prefix headers correctly:
- `Content-Type`: Media type of body
- `Content-Length`: Body length in bytes
- `Content-Encoding`: Compression/encryption applied
- `Content-Language`: Human language of content
- `Content-Disposition`: File download behavior

#### Location Headers
- `Location`: Use for resource location in create/redirect responses (preferred)
- `Content-Location`: Avoid due to caching complexity (discouraged)

#### Conditional Request Headers
- `ETag`: Entity version identifier (hash, timestamp, or version number)
- `If-Match`: Precondition for updates (prevents lost updates)
- `If-None-Match`: Precondition for creates (prevents duplicates)
- Return `412 Precondition Failed` when condition fails

#### Processing Preferences
- `Prefer`: Client processing preferences (RFC 7240)
- `Preference-Applied`: Server response indicating applied preference

#### Idempotency
- `Idempotency-Key`: Client-specific unique request key for safe retries
- Store key with response for 24 hours
- Return same response for duplicate keys
- Reject changed requests with same key using `400`

### Proprietary Headers (Exceptions Only)

Allowed only for domain-specific generic context:
- `X-Flow-ID`: Request tracking across service chain (required)
- `X-Tenant-ID`: Multi-tenant platform identification
- `X-Sales-Channel`: Retailer consumer segment
- `X-Frontend-Type`: Application type (mobile-app, browser)
- `X-Device-Type`: Device category (smartphone, tablet, desktop)
- `X-Device-OS`: Platform (iOS, Android, Windows)

All proprietary headers must propagate end-to-end unchanged.

### Flow ID Requirements
Services must:
- Accept `X-Flow-ID` header in requests
- Create new Flow ID if none provided
- Propagate Flow ID to all downstream calls and events
- Write Flow ID to logs and traces

Allowed formats: UUID, base64, base64url, or alphanumeric string (max 128 chars)

## Consequences

### Positive
- Interoperability via standard headers
- Clear semantics for content and location
- Optimistic locking prevents lost updates
- Idempotency enables safe retries
- Flow tracking facilitates debugging
- End-to-end context propagation

### Negative
- ETag implementation requires version tracking
- Idempotency-Key requires cache infrastructure
- Hard transaction semantics for reliable idempotency
- Proprietary headers require documentation

## Mechanical Enforcement

### Rule ID: API-HEADER-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#132
    description: Header names must use kebab-case with uppercase words
    message: "Use kebab-case with uppercase separate words for header names (e.g., Content-Type, X-Flow-ID)"
    given: "$.paths..parameters[?(@.in == 'header')].name"
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^([A-Z][a-z0-9]*-)*[A-Z][a-z0-9]*$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#180
    description: Prefer Location over Content-Location
    message: "Use Location header instead of Content-Location for resource location"
    given: "$.paths..responses..headers"
    severity: warn
    then:
      field: Content-Location
      function: falsy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#183
    description: Avoid non-standard proprietary headers
    message: "Avoid proprietary headers. Use only specified X-Flow-ID, X-Tenant-ID, etc."
    given: "$.paths..parameters[?(@.in == 'header' && @.name =~ /^X-/)].name"
    severity: warn
    then:
      function: enumeration
      functionOptions:
        values:
          - X-Flow-ID
          - X-Tenant-ID
          - X-Sales-Channel
          - X-Frontend-Type
          - X-Device-Type
          - X-Device-OS
          - X-Mobile-Advertising-Id

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#233
    description: APIs must support X-Flow-ID header
    message: "RESTful API endpoints must support X-Flow-ID header for request tracking"
    given: "$.paths[*][*]"
    severity: error
    then:
      field: "parameters[?(@.name == 'X-Flow-ID')]"
      function: truthy
```

### Valid Examples
```yaml
paths:
  /users:
    post:
      parameters:
        - name: X-Flow-ID
          in: header
          required: false
          schema:
            type: string
            format: uuid
        - name: Idempotency-Key
          in: header
          required: false
          schema:
            type: string
      responses:
        '201':
          headers:
            Location:
              schema:
                type: string
              description: URL of created resource
            ETag:
              schema:
                type: string
              description: Entity version identifier

  /users/{id}:
    put:
      parameters:
        - name: If-Match
          in: header
          required: true
          schema:
            type: string
      responses:
        '200':
          headers:
            ETag:
              schema:
                type: string
        '412':
          description: Precondition Failed
```

### Violations
```yaml
paths:
  /users:
    post:
      parameters:
        - name: x_custom_header  # Wrong: use kebab-case
          in: header
        - name: X-My-Custom-Tracking  # Wrong: non-standard proprietary header
          in: header
      responses:
        '201':
          headers:
            content-location:  # Wrong: prefer Location
              schema:
                type: string

  /items:
    get:
      # Missing: X-Flow-ID parameter
      responses:
        '200':
          description: Success
```

## References
- [Zalando API Guidelines #132](https://opensource.zalando.com/restful-api-guidelines/#132)
- [Zalando API Guidelines #178](https://opensource.zalando.com/restful-api-guidelines/#178)
- [Zalando API Guidelines #180](https://opensource.zalando.com/restful-api-guidelines/#180)
- [Zalando API Guidelines #182](https://opensource.zalando.com/restful-api-guidelines/#182)
- [Zalando API Guidelines #183](https://opensource.zalando.com/restful-api-guidelines/#183)
- [Zalando API Guidelines #233](https://opensource.zalando.com/restful-api-guidelines/#233)
- RFC 9110 (HTTP Semantics)
- RFC 7240 (Prefer Header)