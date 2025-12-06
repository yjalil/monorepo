# ADR-008: API Deprecation and Sunset

## Status
Active

## Context
APIs evolve over time, requiring phasing out of endpoints, versions, or features. Uncontrolled shutdowns break existing integrations. Without clear deprecation communication, clients cannot plan migrations, leading to production outages when features are removed.

Deprecation requires coordination between producers and consumers. Producers must communicate sunset timelines, provide migration paths, and monitor usage to ensure safe transitions without breaking active clients.

## Decision
**API deprecation must be explicitly documented in specifications and communicated via HTTP headers.** Producers must obtain client consent before shutting down deprecated features and provide adequate migration time.

### Specification Requirements
Mark deprecated elements with `deprecated: true` in OpenAPI specification:
- Endpoints (operation objects)
- Parameters (parameter objects)
- Schemas (schema objects)
- Individual properties

Include in `description`:
- Reason for deprecation
- Sunset date (if planned)
- Replacement API/feature
- Migration guide

### HTTP Headers
During deprecation phase, add to responses:
- `Deprecation: <timestamp>` (RFC 9745) - when feature becomes deprecated
- `Sunset: <date-time>` (RFC 8594) - when feature will be removed

Format:
```
Deprecation: @1758095283
Sunset: Wed, 31 Dec 2025 23:59:59 GMT
```

If multiple elements deprecated, use earliest timestamp.

### Shutdown Process
1. Mark as deprecated in specification
2. Add deprecation/sunset headers to responses
3. Monitor API usage to track migration progress
4. Obtain consent from all clients on sunset date
5. For external partners: define and get consent on minimum deprecation lifespan
6. Only shut down after all clients migrated

### Client Requirements
- Must not start using deprecated APIs
- Should monitor `Deprecation` and `Sunset` headers
- Should build alerts for deprecation notifications

## Consequences

### Positive
- Prevents uncontrolled breaking changes
- Gives clients time to migrate
- Enables tracking migration progress
- Provides clear communication channel via headers
- External partners aware of lifecycle before adoption

### Negative
- Requires maintaining deprecated features during transition
- Additional monitoring infrastructure needed
- Coordination overhead with multiple clients
- Must track consent from all consumers

## Mechanical Enforcement

### Rule ID: API-DEPRECATE-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#187
    description: Deprecated elements must have description with migration guidance
    message: "Deprecated element must include sunset date and migration path in description"
    given: "$..deprecated[?(@property == 'deprecated' && @ == true)]^"
    severity: error
    then:
      field: description
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#189
    description: Deprecated operations should include Deprecation header
    message: "Deprecated operations should include Deprecation header in responses"
    given: "$.paths[*][*][?(@.deprecated == true)]"
    severity: warn
    then:
      field: responses.*.headers.Deprecation
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#189
    description: Deprecated operations should include Sunset header
    message: "Deprecated operations should include Sunset header in responses"
    given: "$.paths[*][*][?(@.deprecated == true)]"
    severity: warn
    then:
      field: responses.*.headers.Sunset
      function: truthy
```

### Valid Examples
```yaml
/users/{id}:
  get:
    deprecated: true
    description: |
      Deprecated as of 2025-06-01. Will be removed 2025-12-31.
      Use GET /v2/users/{id} instead.
      Migration guide: https://docs.example.com/migration/users-v2
    responses:
      '200':
        headers:
          Deprecation:
            schema:
              type: string
            example: "@1748736000"
          Sunset:
            schema:
              type: string
            example: "Tue, 31 Dec 2025 23:59:59 GMT"

components:
  schemas:
    User:
      properties:
        legacy_field:
          type: string
          deprecated: true
          description: |
            Deprecated since 2025-01-15. Use `new_field` instead.
            Will be removed in v3.0.0 (2026-06-01).
```

### Violations
```yaml
/users/{id}:
  get:
    deprecated: true
    description: "Get user by ID"
    # Missing: sunset date, replacement, migration guide

/orders:
  post:
    deprecated: true
    description: "Deprecated"
    # Missing: why deprecated, what to use instead
    responses:
      '200':
        description: Success
        # Missing: Deprecation and Sunset headers

components:
  schemas:
    Order:
      properties:
        old_status:
          type: string
          deprecated: true
          # Missing: description with migration path
```

## References
- [Zalando API Guidelines #187](https://opensource.zalando.com/restful-api-guidelines/#187)
- [Zalando API Guidelines #189](https://opensource.zalando.com/restful-api-guidelines/#189)
- [Zalando API Guidelines #191](https://opensource.zalando.com/restful-api-guidelines/#191)
- RFC 9745 (Deprecation Header)
- RFC 8594 (Sunset Header)