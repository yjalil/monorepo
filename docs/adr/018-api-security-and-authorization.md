# ADR-018: API Security and Authorization

## Status
Active

## Context
Every API endpoint exposes data or functionality that requires protection from unauthorized access. Without proper authentication and authorization, APIs are vulnerable to data breaches, unauthorized modifications, and abuse. APIs must implement security consistently and make authorization requirements explicit in their specifications.

Different APIs have different authorization needs: internal APIs typically use JWT bearer tokens from platform IAM, while customer-facing APIs may use OAuth 2.0 flows. Permission granularity must balance security requirements against complexity - too many fine-grained permissions become unmanageable, while too few create excessive access.

Data classification determines whether endpoints require specific permissions: orange/red classified data requires explicit scopes, while green/yellow data may use the default `uid` scope. Permission naming must be consistent across the organization to enable centralized management and auditing.

## Decision
**Every API endpoint must be protected with authentication and authorization defined in the OpenAPI specification.** Use bearer token authentication for internal APIs and appropriate OAuth 2.0 flows for customer-facing APIs. Define and assign specific permissions (scopes) based on data classification.

### Authentication Schemes

**Bearer Authentication (Internal APIs - Default):**
Use for platform IAM JWT tokens based on OAuth 2.0 RFC 6750.

```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

Apply to endpoints with required scopes:
```yaml
security:
  - BearerAuth: [api-repository.read]
```

**OAuth 2.0 (Customer/Partner APIs):**
Use full OAuth 2.0 authorization flows (RFC 6749) when needed:
```yaml
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.example.com/oauth/authorize
          tokenUrl: https://auth.example.com/oauth/token
          scopes:
            read: Read access
            write: Write access
```

**Critical:** Do not use `oauth2` typed security scheme if service only implements simple bearer tokens (exposes unnecessary auth server details and redirection).

### Permission (Scope) Assignment

**Required permissions:**
Endpoints exposing orange/red classified data must have specific scopes:
```yaml
paths:
  /business-partners/{partner-id}:
    get:
      summary: Retrieves information about a business partner
      security:
        - BearerAuth: [business-partner-service.read]
```

**Pseudo permission (uid):**
Use `uid` to explicitly indicate unrestricted access when:
- All exposed data is classified as green/yellow
- Authorization provided at individual object level (not endpoint level)

```yaml
security:
  - BearerAuth: [uid]
```

**Note:** `Authorization` header does not need explicit definition on each endpoint - it's implicitly defined via the security section.

### Permission Naming Convention

Permissions must follow standardized naming pattern:

**BNF Grammar:**
```bnf
<permission> ::= <standard-permission> |
                 <resource-permission> |
                 <pseudo-permission>

<standard-permission> ::= <application-id>.<access-mode>
<resource-permission> ::= <application-id>.<resource-name>.<access-mode>
<pseudo-permission>   ::= uid

<application-id>      ::= [a-z][a-z0-9-]*
<resource-name>       ::= [a-z][a-z0-9-]*
<access-mode>         ::= read | write
```

**Examples:**

| Application ID | Resource ID | Access Mode | Permission |
|---|---|---|---|
| order-management | sales-order | read | `order-management.sales-order.read` |
| order-management | shipment-order | read | `order-management.shipment-order.read` |
| fulfillment-order | - | write | `fulfillment-order.write` |
| business-partner-service | - | read | `business-partner-service.read` |

**Guideline:** Prefer component-specific permissions without resource extensions to avoid excessive permission fragmentation. Read/write access modes are sufficient for most use cases.

**Note:** This convention applies to Platform IAM tokens for service-to-service communication. For other IAM systems (e.g., Partner IAM), follow their existing conventions.

## Consequences

### Positive
- **Explicit security:** Every endpoint's authorization requirements documented in spec
- **Consistent authentication:** Standardized bearer token approach for internal APIs
- **Flexible authorization:** Appropriate OAuth 2.0 flows for different audiences
- **Manageable permissions:** Naming convention enables centralized registry and auditing
- **Clear data protection:** Explicit pseudo-permission indicates unrestricted endpoints
- **Audit trail:** Permission names enable tracking access patterns

### Negative
- **Configuration overhead:** Every endpoint requires security definition
- **Permission management:** Must coordinate permission naming across organization
- **Migration complexity:** Existing APIs must adopt naming conventions
- **Granularity tradeoff:** Balance between security and permission proliferation
- **Documentation burden:** Must document data classification for permission decisions

## Mechanical Enforcement

### Rule ID: API-SEC-001

### OpenAPI Validation
```yaml
rules:
  - id: api-sec-001-security-defined
    description: All endpoints must have security requirements
    message: |
      Every API endpoint must define authentication and authorization.
      See: docs/adr/018-api-security-and-authorization.md
    severity: error
    given: $.paths[*][get,post,put,patch,delete]
    then:
      field: security
      function: truthy

  - id: api-sec-001-bearer-auth
    description: Security scheme should use bearer authentication for internal APIs
    message: |
      Use http bearer authentication for internal APIs.
      See: docs/adr/018-api-security-and-authorization.md
    severity: warning
    given: $.components.securitySchemes[*]
    then:
      field: type
      function: pattern
      functionOptions:
        match: "^(http|oauth2)$"

  - id: api-sec-001-permission-naming
    description: Permission names must follow naming convention
    message: |
      Permission names must match pattern: <app-id>[.<resource>].<read|write> or 'uid'
      See: docs/adr/018-api-security-and-authorization.md
    severity: error
    given: $.paths[*][*].security[*].*[*]
    then:
      function: pattern
      functionOptions:
        match: "^([a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)?\.(read|write)|uid)$"
```

### Valid Examples
```yaml
✅ Bearer authentication with standard permission
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

paths:
  /orders:
    get:
      security:
        - BearerAuth: [order-management.read]

✅ Bearer authentication with resource-specific permission
paths:
  /orders/{id}/items:
    post:
      security:
        - BearerAuth: [order-management.order-item.write]

✅ Pseudo permission for unrestricted access
paths:
  /health:
    get:
      security:
        - BearerAuth: [uid]

✅ OAuth 2.0 for customer-facing API
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.example.com/authorize
          tokenUrl: https://auth.example.com/token
          scopes:
            customer.profile.read: Read customer profile
```

### Invalid Examples
```yaml
❌ No security defined on endpoint
paths:
  /orders:
    get:
      summary: Get orders
      # Missing security section

❌ Invalid permission naming (camelCase)
paths:
  /orders:
    get:
      security:
        - BearerAuth: [orderManagement.read]  # Should be order-management.read

❌ Invalid permission naming (invalid characters)
paths:
  /products:
    get:
      security:
        - BearerAuth: [product_service.read]  # Should use hyphens, not underscores

❌ Too many access modes
paths:
  /data:
    get:
      security:
        - BearerAuth: [data-service.admin]  # Should be .read or .write

❌ Using oauth2 scheme for simple bearer token
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        implicit:  # Don't use if not fully supporting OAuth 2.0
          authorizationUrl: https://auth.example.com
          scopes:
            read: Read access
```

## Implementation Guidance

### Permission Design
1. **Start with standard permissions:** Use `<app-id>.<access-mode>` for most endpoints
2. **Add resource specificity only when needed:** Use `<app-id>.<resource>.<access-mode>` only for genuine security differentiation
3. **Use uid explicitly:** Don't leave endpoints without security - use `uid` to indicate intentionally unrestricted access
4. **Align with data classification:** Orange/red data requires specific permissions, green/yellow may use `uid`

### Security Scheme Selection
- **Internal APIs:** Use bearer authentication with Platform IAM JWT tokens
- **Customer-facing APIs:** Use appropriate OAuth 2.0 flow (authorization code, client credentials)
- **Partner APIs:** Follow partner IAM system conventions

### Authorization Header
- Implicitly defined via security section - no need to explicitly document `Authorization` header on each endpoint
- Format: `Authorization: Bearer <token>`
- Framework handles header parsing and validation

## References
- RFC 6750 (OAuth 2.0 Bearer Token Usage)
- RFC 6749 (OAuth 2.0 Authorization Framework)
- OpenAPI 3.0 Authentication Specification
- Zalando RESTful API Guidelines #104, #105, #225

## Related ADRs
- ADR-010: HTTP Header Standards
- ADR-015: API Meta Information
