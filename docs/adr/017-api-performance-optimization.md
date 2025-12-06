# ADR-017: API Performance Optimization

## Status
Active

## Context
APIs serving large payloads or operating in high-traffic environments (particularly mobile networks) must minimize bandwidth usage and improve responsiveness. Mobile-first applications require careful attention to payload size and network efficiency. Without optimization techniques, APIs can cause poor user experience through slow response times, excessive data consumption, and service overload from unbounded collection requests.

Multiple proven techniques exist to reduce bandwidth: compression (gzip), field filtering to return partial responses, resource embedding to reduce round trips, pagination for large collections, and strategic caching. Each technique addresses different performance scenarios.

## Decision
**APIs should support bandwidth reduction techniques appropriate to their use case.** High-payload or high-traffic APIs must implement compression and consider field filtering, embedding, and pagination strategies.

### Compression (gzip)

**Servers and clients should support gzip content encoding** using `Accept-Encoding` request header and `Content-Encoding` response header for content negotiation.

Skip compression when:
- Content is already compressed (images, video)
- Server lacks resources for compression overhead

Most frameworks require manual activation (Spring Boot, Express, Gin, FastAPI).

**OpenAPI specification:**
```yaml
components:
  headers:
    Accept-Encoding:
      schema:
        type: string
      description: Indicates content encoding client can understand
      example: "gzip, deflate"
    Content-Encoding:
      schema:
        type: string
      description: Content encoding applied to response body
      example: "gzip"
```

### Field Filtering (Partial Responses)

**APIs should support partial responses via `fields` query parameter** to allow clients to request only needed fields, reducing payload size.

**Syntax (BNF grammar):**
```bnf
<fields>            ::= [ <negation> ] <fields_struct>
<fields_struct>     ::= "(" <field_items> ")"
<field_items>       ::= <field> [ "," <field_items> ]
<field>             ::= <field_name> | <fields_substruct>
<fields_substruct>  ::= <field_name> <fields_struct>
<field_name>        ::= <dash_letter_digit> [ <field_name> ]
```

**Examples:**
```http
# Full response
GET /users/123

Response: {"id": "123", "name": "John", "address": "...", "birthday": "..."}

# Filtered response
GET /users/123?fields=(name,friends(name))

Response: {"name": "John", "friends": [{"name": "Jane"}]}
```

**Critical:** Never use default values for `fields` parameter (principle of least astonishment).

### Resource Embedding

**APIs should allow optional embedding of sub-resources** via `embed` query parameter to reduce round trips when clients need related resources.

Use same BNF grammar as field filtering for embedding syntax.

**Example:**
```http
GET /orders/123?embed=(items)

Response:
{
  "id": "123",
  "_embedded": {
    "items": [
      {"position": 1, "sku": "1234-ABCD", "price": {"amount": 71.99, "currency": "EUR"}}
    ]
  }
}
```

**Implementation:** May use database joins, HTTP proxy embedding, or other optimization techniques.

### Caching

**APIs must document cacheable GET, HEAD, and POST endpoints** by declaring `Cache-Control`, `Vary`, and `ETag` headers when caching is supported.

**Default (no caching):**
```http
Cache-Control: no-cache, no-store, must-revalidate, max-age=0
```

**When supporting caching:**
```http
Cache-Control: private, must-revalidate, max-age=300
Vary: accept, accept-encoding
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**Cache support patterns:**
- Support `ETag` with `If-Match`/`If-None-Match` headers on cacheable endpoints
- Provide HEAD requests or GET with `If-None-Match` for update checks
- Return `304 Not Modified` (not `412`) on failed `If-None-Match` validation
- For collections: provide full collection GET endpoint with ETag support

**Restrictions:**
- Do not use `Expires` header (use `Cache-Control` only)
- Attach cache directly to service/gateway layer (not generic HTTP proxy)
- Carefully configure `Vary` header for correct cache key calculation

## Consequences

### Positive
- Reduced bandwidth usage (60-90% with compression and filtering)
- Faster response times, especially on mobile networks
- Fewer round trips with resource embedding
- Lower infrastructure costs from reduced data transfer
- Better user experience through improved responsiveness
- Protected services through pagination and caching

### Negative
- Implementation complexity for dynamic field filtering and embedding
- Manual framework configuration required for compression
- Caching adds complexity around consistency and invalidation
- Testing overhead for various combinations of optimizations
- CPU overhead for compression (usually negligible)
- Cache key complexity with multiple optimization parameters

## Mechanical Enforcement

### Rule ID: API-PERF-001

### OpenAPI Validation
```yaml
rules:
  - id: api-perf-001-compression
    description: High-traffic APIs should document compression support
    message: |
      Document Accept-Encoding and Content-Encoding headers for gzip support.
      See: docs/adr/017-api-performance-optimization.md
    severity: info
    given: $.paths[*][get,post,put,patch]
    
  - id: api-perf-001-filtering
    description: Large payload endpoints should support field filtering
    message: |
      Consider supporting 'fields' query parameter for partial responses.
      See: docs/adr/017-api-performance-optimization.md
    severity: info
    
  - id: api-perf-001-caching
    description: Cacheable endpoints must document cache headers
    message: |
      Document Cache-Control, Vary, and ETag headers for cacheable endpoints.
      See: docs/adr/017-api-performance-optimization.md
    severity: warning
```

### Valid Examples
```http
✅ Compressed response
GET /api/users HTTP/1.1
Accept-Encoding: gzip

HTTP/1.1 200 OK
Content-Encoding: gzip
Content-Type: application/json
[compressed data]

✅ Filtered fields
GET /api/users/123?fields=(name,email) HTTP/1.1

HTTP/1.1 200 OK
{"name": "John", "email": "john@example.com"}

✅ Embedded sub-resource
GET /api/orders/456?embed=(items,customer) HTTP/1.1

HTTP/1.1 200 OK
{
  "id": "456",
  "_embedded": {
    "items": [...],
    "customer": {...}
  }
}

✅ Cached response with validation
GET /api/products/789 HTTP/1.1
If-None-Match: "abc123"

HTTP/1.1 304 Not Modified
ETag: "abc123"
Cache-Control: private, must-revalidate, max-age=300
```

### Invalid Examples
```http
❌ Missing Content-Encoding header on compressed response
HTTP/1.1 200 OK
Content-Type: application/json
[gzip binary data without Content-Encoding header]

❌ Using default value for fields parameter
parameters:
  - name: fields
    default: "(id,name)"  # Violates principle of least astonishment

❌ Using Expires header instead of Cache-Control
HTTP/1.1 200 OK
Expires: Wed, 21 Oct 2025 07:28:00 GMT  # Don't use this

❌ Returning 412 instead of 304 for If-None-Match validation
GET /api/users/123 HTTP/1.1
If-None-Match: "abc123"

HTTP/1.1 412 Precondition Failed  # Should be 304
```

## References
- RFC 9110 Section 8.4 (Content-Encoding)
- RFC 9110 Section 12.5.3 (Accept-Encoding)
- RFC 9111 (HTTP Caching)
- RFC 7240 (Prefer Header)
- Zalando RESTful API Guidelines #155, #156, #157, #158, #227

## Related ADRs
- ADR-010: HTTP Header Standards
- ADR-016: Pagination
- ADR-014: JSON Payload Standards
