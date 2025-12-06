# ADR-014: JSON Payload Standards

## Status
Active

## Context
JSON is the standard data interchange format for REST APIs. Without consistent conventions, APIs across teams use different naming styles (camelCase vs snake_case), handle null values inconsistently, represent enums differently, and structure common data types (money, addresses) in incompatible ways. This creates cognitive overhead for API consumers and prevents code reuse.

Standards for property naming, null semantics, common field types, and standard objects enable predictable API consumption and consistent tooling support.

## Decision
**APIs must use JSON as the payload format with consistent conventions for naming, types, and common structures.** Follow snake_case for properties, handle null/absent consistently, and use standard schemas for money, addresses, and common fields.

### JSON Requirements

**Mandatory:**
- Use JSON (RFC 7159) as payload format
- Top-level must be JSON object (not array) for extensibility
- Use UTF-8 encoding (RFC 7493)
- Contain only valid Unicode strings (no surrogates)
- Unique member names (no duplicates)
- Media type: `application/json` (or `application/problem+json` for errors)

**Optional:**
- Non-JSON formats (JPG, PNG, PDF, ZIP) for business-specific data
- Other formats (XML, CSV) only via content negotiation, additionally to JSON

### Naming Conventions

#### Property Names
Must use snake_case matching regex `^[a-z_][a-z_0-9]*$`:
```json
{
  "customer_number": "C-123",
  "sales_order_number": "SO-456",
  "billing_address": {...}
}
```

#### Array Names
Pluralize to indicate multiple values:
```json
{
  "users": [...],
  "order": {...}
}
```

#### Enum Values
Use UPPER_SNAKE_CASE:
```json
{
  "status": "PAYMENT_PENDING",
  "type": "SHIPPING_ADDRESS"
}
```

Exception: External case-sensitive values (ISO language codes, sort parameters)

#### Date/Time Properties
Must contain type indicators or end with `_at`:
```json
{
  "created_at": "2025-01-15T10:30:00Z",
  "arrival_date": "2025-02-01",
  "checkout_time": "14:30:00Z"
}
```

### Null and Absent Properties

**Same semantics for null and absent:**
Properties marked `nullable` and not `required` must be handled identically whether absent or null:
```yaml
# Both {} and {"name": null} mean the same
name:
  type: string
  nullable: true
```

**Boolean properties:**
Never use null for booleans. Use enum if third state needed:
```yaml
# Wrong
accepted: null

# Right
acceptance_status:
  enum: [ACCEPTED, REJECTED, PENDING]
```

**Empty arrays:**
Use `[]`, never `null`:
```json
{
  "items": []
}
```

### Common Field Names

**Identity and References:**
- `id`: Opaque string (not number), unique, stable, never recycled
- `{xyz}_id`: Reference to another object (e.g., `partner_id`, `parent_node_id`)
- Exception: `customer_number` (legacy)

**Metadata:**
- `created_at`: Creation timestamp (format: date-time)
- `modified_at`: Last update timestamp (format: date-time)
- `e_tag`: Entity tag for embedded sub-resources

### Standard Objects

#### Money
```yaml
Money:
  type: object
  properties:
    amount:
      type: number
      format: decimal
      example: 19.99
    currency:
      type: string
      format: iso-4217
      example: EUR
  required:
    - amount
    - currency
```

**Critical:**
- Never inherit from Money (use composition)
- Never convert to float/double (use BigDecimal)
- Support unlimited precision for Bitcoin, etc.
- Reference: `https://opensource.zalando.com/restful-api-guidelines/models/money-1.0.0.yaml#/Money`

#### Address
```yaml
address:
  type: object
  properties:
    street:
      type: string
      example: "Schönhauser Allee 103"
    city:
      type: string
      example: "Berlin"
    zip:
      type: string
      example: "14265"
    country_code:
      type: string
      format: iso-3166-alpha-2
      example: "DE"
  required:
    - street
    - city
    - zip
    - country_code
```

#### Addressee
```yaml
addressee:
  type: object
  properties:
    salutation:
      type: string
      example: "Mr"
    first_name:
      type: string
      example: "Hans Dieter"
    last_name:
      type: string
      example: "Mustermann"
    business_name:
      type: string
      example: "Consulting Services GmbH"
  required:
    - first_name
    - last_name
```

### Maps
Define using `additionalProperties`:
```yaml
translations:
  type: object
  additionalProperties:
    type: string
  example:
    de: "Farbe"
    en-US: "color"
    en-GB: "colour"
```

Map keys don't follow snake_case (use natural domain format).

### Read/Write Schemas
Use single schema with:
- `readOnly`: Properties only in responses (e.g., `id`, `created_at`)
- `writeOnly`: Properties only in requests (e.g., `password`)

## Consequences

### Positive
- Consistent property naming across APIs
- Clear null semantics prevent client confusion
- Standard objects enable code reuse
- Snake_case improves readability
- Decimal prevents precision loss in money
- Single read/write schema reduces duplication

### Negative
- Snake_case differs from JavaScript conventions
- Null/absent same semantics limits expressiveness
- Money as closed type prevents extension
- Must sanitize unsupported Unicode for some tools (Postgres `\u0000`)

## Mechanical Enforcement

### Rule ID: API-JSON-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#118
    description: Property names must be snake_case
    message: "Use snake_case for property names (e.g., user_name not userName)"
    given: "$..properties.*~"
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^[a-z_][a-z_0-9]*$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#240
    description: Enum values must be UPPER_SNAKE_CASE
    message: "Use UPPER_SNAKE_CASE for enum values (e.g., PAYMENT_PENDING)"
    given: "$..enum[*]"
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^[A-Z][A-Z0-9_]*$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#235
    description: Date/time properties must indicate type in name
    message: "Date/time property names should contain 'date', 'time', 'timestamp' or end with '_at'"
    given: "$..properties[?(@.format == 'date' || @.format == 'date-time')]~"
    severity: warn
    then:
      function: pattern
      functionOptions:
        match: "(date|time|day|timestamp|_at)$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#122
    description: Booleans must not be nullable
    message: "Boolean properties must not be nullable - use enum if third state needed"
    given: "$..properties[?(@.type == 'boolean')]"
    severity: error
    then:
      field: nullable
      function: falsy

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#120
    description: Array property names should be plural
    message: "Array property names should be pluralized"
    given: "$..properties[?(@.type == 'array')]~"
    severity: warn
    then:
      function: pattern
      functionOptions:
        match: "s$"

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#174
    description: Use standard money object
    message: "Money should reference standard schema"
    given: "$..properties[?(@property =~ /(price|amount|cost|total)$/)]"
    severity: info
    then:
      field: $ref
      function: pattern
      functionOptions:
        match: "money.*yaml"
```

### Valid Examples
```yaml
components:
  schemas:
    Order:
      type: object
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
        customer_id:
          type: string
          format: uuid
        order_number:
          type: string
          example: "ORD-12345"
        status:
          type: string
          enum:
            - PENDING
            - CONFIRMED
            - SHIPPED
            - DELIVERED
        created_at:
          type: string
          format: date-time
          readOnly: true
        modified_at:
          type: string
          format: date-time
          readOnly: true
        items:
          type: array
          items:
            $ref: '#/components/schemas/OrderItem'
        grand_total:
          $ref: 'https://opensource.zalando.com/restful-api-guidelines/models/money-1.0.0.yaml#/Money'
        shipping_address:
          $ref: '#/components/schemas/Address'
        preferences:
          type: object
          additionalProperties:
            type: string
      required:
        - customer_id
        - items
```

### Violations
```yaml
components:
  schemas:
    Order:
      properties:
        orderId:  # Wrong: camelCase
          type: string
        
        orderStatus:  # Wrong: camelCase
          type: string
          enum:
            - pending  # Wrong: lowercase
            - Confirmed  # Wrong: mixed case
        
        created:  # Wrong: should be created_at
          type: string
          format: date-time
        
        isActive:  # Wrong: boolean naming
          type: boolean
          nullable: true  # Wrong: nullable boolean
        
        item:  # Wrong: should be plural
          type: array
          items:
            type: object
        
        price:  # Wrong: should use Money object
          type: number
        
        currency:  # Wrong: price and currency separate
          type: string
```

## References
- [Zalando API Guidelines #167](https://opensource.zalando.com/restful-api-guidelines/#167)
- [Zalando API Guidelines #118](https://opensource.zalando.com/restful-api-guidelines/#118)
- [Zalando API Guidelines #123](https://opensource.zalando.com/restful-api-guidelines/#123)
- [Zalando API Guidelines #173](https://opensource.zalando.com/restful-api-guidelines/#173)
- [Zalando API Guidelines #249](https://opensource.zalando.com/restful-api-guidelines/#249)
- RFC 7159 (JSON)
- RFC 7493 (I-JSON)