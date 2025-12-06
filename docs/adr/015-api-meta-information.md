# ADR-015: API Meta Information

## Status
Active

## Context
API specifications need consistent metadata for discovery, lifecycle management, version tracking, and audience-appropriate governance. Without standardized meta information, teams cannot track API evolution, enforce appropriate quality standards per audience, or maintain stable naming across organizational changes.

API identifiers must be immutable to track specification evolution through versions. Audience classification determines required quality levels, review processes, and access control policies. Semantic versioning enables predictable compatibility expectations.

## Decision
**All API specifications must include standardized OpenAPI meta information fields.** This includes title, version, description, contact information, unique identifier, and target audience classification.

### Required OpenAPI Info Fields

#### Standard Fields
```yaml
openapi: 3.1.0
info:
  title: Parcel Service API
  version: 1.3.7
  description: API for managing parcel tracking and delivery
  contact:
    name: Parcel Team
    url: https://example.com/teams/parcel
    email: parcel-team@example.com
```

#### Extension Fields
```yaml
info:
  x-api-id: d0184f38-b98d-11e7-9c56-68f728c1ba70
  x-audience: company-internal
```

### Semantic Versioning (MAJOR.MINOR.PATCH)

Follow Semantic Versioning 2.0 rules 1-8 and 11:

**MAJOR version:** Increment for incompatible API changes (after consumer alignment)
**MINOR version:** Increment for backwards-compatible new functionality
**PATCH version:** Optionally increment for backwards-compatible bug fixes or editorial changes

**Restrictions:**
- Do not use pre-release versions (e.g., `1.0.0-alpha`)
- Do not use build metadata (e.g., `1.0.0+20240115`)
- May use `0.y.z` for initial API design

**Note:** This is the API specification document version, distinct from:
- OpenAPI Specification version (e.g., `openapi: 3.1.0`)
- API implementation version

### API Identifier (x-api-id)

**Format:** URN matching pattern `^[a-z0-9][a-z0-9-:.]{6,62}[a-z0-9]$`

**Properties:**
- Globally unique
- Immutable (never changes across API evolution)
- Enables version history tracking
- Supports automated compatibility checks

**Recommendation:** Use UUID (generated once at API creation) rather than human-readable URN to avoid temptation to change identifier during evolution.

**Critical:** Do not copy API identifier when copying specifications - generate new identifier immediately.

### API Audience (x-audience)

Classification of intended consumers (exactly one per specification):

**component-internal:**
- Team or product internal API
- Same functional component applications only
- Example: Internal helper services

**business-unit-internal:**
- Same business unit product portfolio
- Owned by specific business unit

**company-internal:**
- All company business units
- Example: Cross-BU integration APIs

**external-partner:**
- Business partners and company
- Restricted partner access

**external-public:**
- Public internet access
- Anyone can consume

**Note:** Smaller audiences are included in wider groups (no need to declare both). If API parts have different audiences, split into separate specifications.

### Functional Naming Schema

Pattern: `<functional-domain>-<functional-component>`

**Requirements by audience:**
- **Must** use: external-public, external-partner
- **Should** use: company-internal, business-unit-internal
- **May** use: component-internal

**Hostname convention:**
```
<functional-name>.zalandoapis.com
```

Legacy pattern (component-internal only):
```
<application-id>.<organization-unit>.zalan.do
```

## Consequences

### Positive
- API lifecycle tracking via immutable identifiers
- Audience-appropriate quality standards
- Predictable versioning expectations
- Stable naming across organizational changes
- Automated compatibility checks enabled
- Clear ownership and contact information

### Negative
- Must maintain identifier registry
- Cannot change API identifier (by design)
- Single audience per specification (may require splits)
- Functional naming adds complexity
- Legacy hostname patterns create exceptions

## Mechanical Enforcement

### Rule ID: API-META-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#218
    description: Must contain API title
    message: "API specification must include info/title"
    given: "$.info"
    severity: error
    then:
      field: title
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#218
    description: Must contain API version
    message: "API specification must include info/version"
    given: "$.info"
    severity: error
    then:
      field: version
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#116
    description: Version must follow semantic versioning
    message: "Use semantic versioning format: MAJOR.MINOR.PATCH"
    given: "$.info.version"
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#218
    description: Must contain API description
    message: "API specification must include info/description"
    given: "$.info"
    severity: error
    then:
      field: description
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#218
    description: Must contain contact information
    message: "API specification must include info/contact with name, url, and email"
    given: "$.info.contact"
    severity: error
    then:
      - field: name
        function: truthy
      - field: url
        function: truthy
      - field: email
        function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#215
    description: Must provide API identifier
    message: "API specification must include info/x-api-id"
    given: "$.info"
    severity: error
    then:
      field: x-api-id
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#215
    description: API identifier must match pattern
    message: "x-api-id must match pattern: ^[a-z0-9][a-z0-9-:.]{6,62}[a-z0-9]$"
    given: "$.info.x-api-id"
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^[a-z0-9][a-z0-9-:.]{6,62}[a-z0-9]$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#219
    description: Must provide API audience
    message: "API specification must include info/x-audience"
    given: "$.info"
    severity: error
    then:
      field: x-audience
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#219
    description: API audience must be valid value
    message: "x-audience must be one of: component-internal, business-unit-internal, company-internal, external-partner, external-public"
    given: "$.info.x-audience"
    severity: error
    then:
      function: enumeration
      functionOptions:
        values:
          - component-internal
          - business-unit-internal
          - company-internal
          - external-partner
          - external-public
```

### Valid Examples
```yaml
openapi: 3.1.0
info:
  title: Parcel Service API
  version: 1.3.7
  description: |
    API for managing parcel tracking and delivery.
    Provides endpoints for creating shipments, tracking parcels,
    and managing delivery preferences.
  contact:
    name: Parcel Services Team
    url: https://example.com/teams/parcel
    email: parcel-team@example.com
  x-api-id: d0184f38-b98d-11e7-9c56-68f728c1ba70
  x-audience: company-internal

servers:
  - url: https://parcel-service.zalandoapis.com
    description: Production server
```

### Violations
```yaml
openapi: 3.1.0
info:
  # Missing: title
  version: 1.0.0-beta  # Wrong: pre-release version
  # Missing: description
  contact:
    name: Team
    # Missing: url and email
  # Missing: x-api-id
  x-audience: internal  # Wrong: invalid audience value

servers:
  - url: https://api.example.com  # Wrong: not following naming convention
```

## References
- [Zalando API Guidelines #218](https://opensource.zalando.com/restful-api-guidelines/#218)
- [Zalando API Guidelines #116](https://opensource.zalando.com/restful-api-guidelines/#116)
- [Zalando API Guidelines #215](https://opensource.zalando.com/restful-api-guidelines/#215)
- [Zalando API Guidelines #219](https://opensource.zalando.com/restful-api-guidelines/#219)
- [Zalando API Guidelines #223](https://opensource.zalando.com/restful-api-guidelines/#223)
- [Semantic Versioning 2.0](https://semver.org/)
- [OpenAPI Info Object](https://spec.openapis.org/oas/latest.html#info-object)