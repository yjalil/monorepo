# ADR-012: HTTP Status Codes

## Status
Active

## Context
HTTP status codes communicate the result of operations to clients. Misusing status codes breaks client expectations, prevents proper error handling, and violates HTTP semantics. For example, returning `200` for errors prevents clients from detecting failures, while using non-standard codes creates confusion.

Clients rely on status code categories (2xx success, 4xx client error, 5xx server error) for retry logic, error handling, and user experience decisions. Infrastructure components (proxies, caches, load balancers) also make routing decisions based on status codes.

## Decision
**APIs must use official HTTP status codes consistently with their intended semantics.** Use the most specific appropriate code, define all success and error responses, and support Problem JSON for error details.

### Common Status Codes

#### Success Codes (2xx)
- `200 OK`: General success, resource returned
- `201 Created`: Resource created (with `Location` header)
- `202 Accepted`: Asynchronous processing initiated
- `204 No Content`: Success without response body
- `207 Multi-Status`: Batch/bulk operations with per-item status

#### Client Error Codes (4xx)
- `400 Bad Request`: Malformed request or validation failure
- `401 Unauthorized`: Missing or invalid authentication (actually "unauthenticated")
- `403 Forbidden`: Valid auth but insufficient permissions
- `404 Not Found`: Resource does not exist
- `405 Method Not Allowed`: HTTP method not supported (document only if state-dependent)
- `406 Not Acceptable`: Requested content-type not available
- `409 Conflict`: Request conflicts with current resource state (document required)
- `410 Gone`: Resource permanently deleted
- `412 Precondition Failed`: Conditional request failed (`If-Match`, `If-None-Match`)
- `415 Unsupported Media Type`: Request content-type not supported
- `428 Precondition Required`: Conditional headers required
- `429 Too Many Requests`: Rate limit exceeded

#### Server Error Codes (5xx)
- `500 Internal Server Error`: Unexpected server problem
- `501 Not Implemented`: Endpoint not yet implemented
- `502 Bad Gateway`: Invalid response from upstream service
- `503 Service Unavailable`: Temporary unavailability (use `Retry-After` header)
- `504 Gateway Timeout`: Upstream service timeout

### Status Code Guidelines

#### Do Not Use
- `205 Reset Content`: Interactive use case, not REST
- `206 Partial Content`: Rare media streaming case
- `301/302/303/307/308`: Redirects (handle via proxy or deprecation)
- `408 Request Timeout`: Server-side timeout, not API use
- `417 Expectation Failed`: Technical, not API use
- `422 Unprocessable Content`: Redundant with `400`
- `423 Locked`: Pessimistic locking (prefer optimistic)
- `505 HTTP Version Not Supported`: Technical, not API use

#### Documentation Requirements
- Standard errors (`401`, `403`, `404`, `500`, `503`): Do not document unless endpoint-specific details exist
- Specific errors (`409`, `405`, `411`, `501`): Must document with clear conditions
- Success codes: Document all (exception: `200` is implicit)

### Batch/Bulk Operations
Always return `207 Multi-Status` for batch/bulk requests:
- Even if all items fail
- Even if processing is asynchronous
- Return `4xx`/`5xx` only for non-item-specific failures (e.g., overload)

Response structure:
```yaml
items:
  - id: "item-1"
    status: "success"
    description: "Created successfully"
  - id: "item-2"
    status: "failed"
    description: "Validation error: email required"
```

### Rate Limiting
Return `429 Too Many Requests` with either:

**Option 1: Retry-After header**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
```

**Option 2: X-RateLimit headers**
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 3600
```

### Problem JSON (RFC 9457)
Return `application/problem+json` for all `4xx` and `5xx` responses:
```json
{
  "type": "/problems/out-of-stock",
  "title": "Out of Stock",
  "status": 400,
  "detail": "Item 'SKU-123' is currently out of stock",
  "instance": "/orders/12345"
}
```

**Requirements:**
- Use relative URI references for `type` and `instance`
- Do not expose stack traces
- Clients must accept `application/problem+json` in `Accept` header
- Clients must be robust if Problem JSON not returned

## Consequences

### Positive
- Predictable client error handling
- Standard retry behavior via status codes
- Consistent error information via Problem JSON
- Clear batch operation results
- Rate limiting with retry guidance

### Negative
- Problem JSON not subset of `application/json` (requires explicit Accept header)
- Must maintain Problem JSON alongside OpenAPI schemas
- Batch responses always `207` (even total failures)
- Infrastructure may override status codes

## Mechanical Enforcement

### Rule ID: API-STATUS-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#243
    description: Must use official HTTP status codes
    message: "Only use official HTTP status codes defined in RFC 9110"
    given: "$.paths[*][*].responses.*~"
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^(1[0-9]{2}|2[0-9]{2}|3[0-9]{2}|4[0-9]{2}|5[0-9]{2}|default)$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#151
    description: Must define success and error responses
    message: "All operations must define success responses and relevant error responses"
    given: "$.paths[*][*]"
    severity: error
    then:
      field: responses
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#176
    description: Error responses should support Problem JSON
    message: "4xx and 5xx responses should include application/problem+json content type"
    given: "$.paths[*][*].responses[?(@property >= 400)]"
    severity: warn
    then:
      field: "content.application/problem+json"
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#220
    description: Use most specific HTTP status code
    message: "Use the most specific appropriate status code (e.g., 409 not 400 for conflicts)"
    given: "$.paths[*][*].responses"
    severity: info
    then:
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#152
    description: Batch operations must return 207
    message: "Batch/bulk operations must return 207 Multi-Status"
    given: "$.paths[*].post[?(@.requestBody..type == 'array')].responses"
    severity: warn
    then:
      field: "207"
      function: truthy
```

### Valid Examples
```yaml
paths:
  /users:
    post:
      summary: Create user
      responses:
        '201':
          description: Created
          headers:
            Location:
              schema:
                type: string
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '400':
          description: Validation failed
          content:
            application/problem+json:
              schema:
                $ref: 'https://opensource.zalando.com/restful-api-guidelines/models/problem-1.0.1.yaml#/Problem'
        default:
          description: Unexpected error
          content:
            application/problem+json:
              schema:
                $ref: 'https://opensource.zalando.com/restful-api-guidelines/models/problem-1.0.1.yaml#/Problem'

  /users/{id}:
    get:
      responses:
        '200':
          description: Success
        '404':
          description: User not found
          content:
            application/problem+json:
              schema:
                $ref: '#/components/schemas/Problem'

    put:
      responses:
        '200':
          description: Updated
        '409':
          description: Version conflict
          content:
            application/problem+json:
              schema:
                $ref: '#/components/schemas/Problem'
        '412':
          description: Precondition failed

  /batch/users:
    post:
      summary: Batch create users
      responses:
        '207':
          description: Multi-Status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatchResponse'
```

### Violations
```yaml
paths:
  /users:
    post:
      responses:
        '200':  # Wrong: should be 201 for creation
          description: Created

    get:
      responses:
        '200':
          description: Success
        # Missing: default error response

  /items/{id}:
    put:
      responses:
        '200':
          description: Success
        '400':
          content:
            application/json:  # Wrong: should use application/problem+json
              schema:
                type: object

  /batch/process:
    post:
      responses:
        '200':  # Wrong: batch should return 207
          description: Processed
```

## References
- [Zalando API Guidelines #243](https://opensource.zalando.com/restful-api-guidelines/#243)
- [Zalando API Guidelines #150](https://opensource.zalando.com/restful-api-guidelines/#150)
- [Zalando API Guidelines #151](https://opensource.zalando.com/restful-api-guidelines/#151)
- [Zalando API Guidelines #152](https://opensource.zalando.com/restful-api-guidelines/#152)
- [Zalando API Guidelines #176](https://opensource.zalando.com/restful-api-guidelines/#176)
- RFC 9110 (HTTP Semantics)
- RFC 9457 (Problem Details)