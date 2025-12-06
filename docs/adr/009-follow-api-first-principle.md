# ADR-009: Follow API First Principle

## Status
Active

## Context
APIs represent contracts between services and clients. Implementing code before defining the API contract leads to inconsistent designs driven by implementation details rather than client needs. Without upfront API design, teams cannot gather early feedback, ensure consistency with standards, or validate usability before significant development investment.

API specifications must be durable and versionable. Remote references to API fragments can break specifications if the referenced content changes or becomes unavailable.

## Decision
**APIs must be designed and specified before implementation.** Use OpenAPI as the specification language, subject specifications to version control, and obtain peer review before coding.

### Requirements
- Define API using OpenAPI specification before writing implementation code
- Use single self-contained YAML file for specifications
- Prefer OpenAPI 3.1 (fully JSON Schema compliant)
- Store specifications in version control (git)
- Apply automated linting for guideline compliance
- Obtain peer review for component-external APIs (`x-api-audience != component-internal`)

### Self-Contained Specifications
API specifications must be self-contained without references to local or remote content, except for:
- Durable, immutable API fragment sources (guideline-defined reusable components)
- Internal API repository for published, immutable specification revisions

### Language
Write all API specifications using U.S. English for consistency.

## Consequences

### Positive
- Client needs drive design, not implementation constraints
- Early feedback prevents costly rework
- Specifications serve as living documentation
- Automated validation ensures guideline compliance
- Version control provides change history
- Self-contained specs remain stable and portable

### Negative
- Upfront design effort before coding
- Requires discipline to resist implementation-first approach
- Additional review process overhead
- Self-contained requirement increases file size

## Mechanical Enforcement

### Rule ID: API-FIRST-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#101
    description: API specifications must use OpenAPI format
    message: "API must be defined using OpenAPI specification"
    given: "$"
    severity: error
    then:
      field: openapi
      function: truthy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#101
    description: Prefer OpenAPI 3.1 for new APIs
    message: "Use OpenAPI 3.1.x for new API specifications"
    given: "$.openapi"
    severity: warn
    then:
      function: pattern
      functionOptions:
        match: "^3\\.1\\."

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#234
    description: Avoid non-durable remote references
    message: "Use only durable, immutable remote references or make specification self-contained"
    given: "$..$ref"
    severity: error
    then:
      function: pattern
      functionOptions:
        notMatch: "^https?://(?!opensource\\.zalando\\.com/restful-api-guidelines/).*"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#102
    description: API should include external documentation link
    message: "Provide link to API user manual in externalDocs"
    given: "$"
    severity: warn
    then:
      field: externalDocs.url
      function: truthy
```

### Valid Examples
```yaml
openapi: 3.1.0
info:
  title: User Service API
  version: 1.0.0
  description: Manages user accounts and profiles
externalDocs:
  description: User Service API Manual
  url: https://docs.example.com/apis/user-service

paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'

components:
  schemas:
    User:
      type: object
      required:
        - id
        - email
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
```

### Violations
```yaml
# Missing OpenAPI version
info:
  title: User Service API

# Non-durable remote reference
components:
  schemas:
    User:
      $ref: 'https://github.com/example/schemas/user.yaml#/User'

# Local file reference (not self-contained)
components:
  schemas:
    User:
      $ref: '../schemas/user.yaml#/User'

# Using OpenAPI 2.0 (Swagger) for new API
swagger: '2.0'
info:
  title: User Service API
```

## References
- [Zalando API Guidelines #100](https://opensource.zalando.com/restful-api-guidelines/#100)
- [Zalando API Guidelines #101](https://opensource.zalando.com/restful-api-guidelines/#101)
- [Zalando API Guidelines #234](https://opensource.zalando.com/restful-api-guidelines/#234)
- [OpenAPI Specification 3.1](https://spec.openapis.org/oas/v3.1.0)