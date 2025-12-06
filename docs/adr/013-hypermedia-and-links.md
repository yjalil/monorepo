# ADR-013: Hypermedia and Links

## Status
Active

## Context
REST maturity levels define API sophistication from basic HTTP to full HATEOAS (Hypertext As The Engine Of Application State). Level 2 uses HTTP methods and status codes correctly but doesn't require hypermedia controls. Level 3 (HATEOAS) adds hypermedia for API navigation.

In service-oriented architectures with explicitly defined APIs (API First), HATEOAS adds complexity without clear benefit. Clients need API documentation regardless of hypermedia, and generic hypermedia clients remain theoretical. However, embedding links for resource relationships and pagination provides practical value without full HATEOAS.

## Decision
**APIs must implement REST maturity level 2 (proper HTTP method and status code usage) but are not required to implement level 3 (HATEOAS).** When embedding links, use standardized hypertext controls with full absolute URIs.

### REST Maturity Level 2 (Required)
- Use HTTP methods correctly (GET, POST, PUT, PATCH, DELETE)
- Return appropriate HTTP status codes
- Design resource-oriented endpoints
- Use HTTP headers properly

### REST Maturity Level 3 (Optional)
HATEOAS is not generally recommended due to:
- Client engineers find links in API documentation anyway
- Generic hypermedia clients are theoretical, not practical
- Domain model changes still require client updates
- Additional complexity without clear SOA value
- Limited OpenAPI tooling support

HATEOAS may be used if justified by specific use cases after evaluating tradeoffs.

### Hypertext Control Standard

When embedding links, use common hypertext control object:
```json
{
  "href": "https://api.example.com/users/123"
}
```

**Required attribute:**
- `href`: Full, absolute URI using HTTP(s) scheme

**Attribute naming:**
- Use snake_case (not hyphen-case)
- Convert IANA link relations: `version-history` → `version_history`
- Prefer names from IANA Link Relations Registry

**Extended controls** may add relationship-specific attributes:
```json
{
  "spouse": {
    "href": "https://api.example.com/persons/456",
    "since": "1996-12-19",
    "id": "456",
    "name": "Linda Mustermann"
  }
}
```

### Simplified Controls for Pagination

For pagination and self-references, use simple URI values with standard link relations:
```json
{
  "self": "https://api.example.com/users?page=2",
  "next": "https://api.example.com/users?page=3",
  "prev": "https://api.example.com/users?page=1",
  "first": "https://api.example.com/users?page=1",
  "last": "https://api.example.com/users?page=10"
}
```

### URI Requirements
- Always use full, absolute URIs (never relative)
- Include scheme, host, and full path
- Avoid client-side URI construction complexity
- Prioritize clarity over payload size (use gzip compression instead)

### Link Header Prohibition
Do not use RFC 8288 `Link` headers with JSON media types. Embed links directly in JSON payload for:
- Flexibility in link placement
- Precision in relationship definition
- Consistency with JSON structure
- Better tooling support

## Consequences

### Positive
- Predictable HTTP semantics (level 2)
- Clear resource relationships via embedded links
- Standardized link format across APIs
- No client-side URI construction needed
- Simple pagination navigation
- Avoids HATEOAS complexity without clear benefit

### Negative
- No automatic API discovery via hypermedia
- Clients depend on API documentation
- Cannot leverage generic HATEOAS clients
- Larger payload than relative URIs (mitigated by gzip)
- Links embedded in payload, not headers

## Mechanical Enforcement

### Rule ID: API-LINK-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#164
    description: Link objects must have href property
    message: "Hypertext control objects must contain 'href' property with absolute URI"
    given: "$..properties[?(@property =~ /_link$|_url$|^href$|^self$|^next$|^prev$|^first$|^last$/)]"
    severity: error
    then:
      field: type
      function: pattern
      functionOptions:
        match: "^(string|object)$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#217
    description: URIs must be absolute
    message: "All resource links must use full, absolute URIs"
    given: "$..properties.href"
    severity: error
    then:
      field: format
      function: pattern
      functionOptions:
        match: "^uri$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#166
    description: Do not use Link headers with JSON
    message: "Link headers (RFC 8288) must not be used with JSON media types"
    given: "$.paths[*][*].responses[*].headers"
    severity: error
    then:
      field: Link
      function: falsy
```

### Valid Examples
```yaml
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        manager:
          type: object
          description: Link to user's manager
          properties:
            href:
              type: string
              format: uri
              example: "https://api.example.com/users/456"
            name:
              type: string
              example: "Jane Doe"
          required:
            - href

    UserCollection:
      type: object
      properties:
        items:
          type: array
          items:
            $ref: '#/components/schemas/User'
        self:
          type: string
          format: uri
          example: "https://api.example.com/users?page=2"
        next:
          type: string
          format: uri
          example: "https://api.example.com/users?page=3"
        prev:
          type: string
          format: uri
          example: "https://api.example.com/users?page=1"

    HttpLink:
      type: object
      description: Common hypertext control
      properties:
        href:
          type: string
          format: uri
          description: Absolute URI using HTTP(s)
      required:
        - href
```

### Violations
```yaml
components:
  schemas:
    User:
      properties:
        profile_link:
          type: object
          properties:
            path:  # Wrong: must be 'href'
              type: string
            
        related:
          type: object
          properties:
            href:
              type: string  # Wrong: missing format: uri

        manager_url:
          type: string
          example: "/users/456"  # Wrong: relative URI

paths:
  /users:
    get:
      responses:
        '200':
          headers:
            Link:  # Wrong: Link headers prohibited with JSON
              schema:
                type: string
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserCollection'
```

## References
- [Zalando API Guidelines #162](https://opensource.zalando.com/restful-api-guidelines/#162)
- [Zalando API Guidelines #163](https://opensource.zalando.com/restful-api-guidelines/#163)
- [Zalando API Guidelines #164](https://opensource.zalando.com/restful-api-guidelines/#164)
- [Zalando API Guidelines #217](https://opensource.zalando.com/restful-api-guidelines/#217)
- [Zalando API Guidelines #166](https://opensource.zalando.com/restful-api-guidelines/#166)
- [Richardson Maturity Model](https://martinfowler.com/articles/richardsonMaturityModel.html)
- [IANA Link Relations Registry](https://www.iana.org/assignments/link-relations/link-relations.xhtml)
- RFC 8288 (Web Linking)