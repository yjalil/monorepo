# ADR-007: Use Standard Data Formats

## Status
Active

## Context
OpenAPI defines standard formats from ISO and IETF specifications for dates, times, numbers, and binary data. Using non-standard formats creates ambiguity in precision, encoding, and interpretation across clients and servers. Numeric timestamps (1460062925 vs 1460062925000) create precision ambiguity, while custom date formats require documentation and are error-prone.

Without standardized formats, clients may guess precision incorrectly, inadvertently change values, or misinterpret temporal data across timezones.

## Decision
**APIs must use OpenAPI standard formats for all date/time, numeric, and structured data types.** When defining properties, always specify the appropriate format alongside the type.

### Required Standard Formats

#### Temporal Data
- Dates: `string` with format `date` (RFC 3339: `"2019-07-30"`)
- Date-times: `string` with format `date-time` (RFC 3339: `"2019-07-30T06:43:40.252Z"`)
- Times: `string` with format `time` (RFC 3339: `"06:43:40.252Z"`)
- Durations: `string` with format `duration` (ISO 8601: `"P1DT3H4S"`)
- Periods: `string` with format `period` (ISO 8601: `"2022-06-30T14:52:44.276/PT48H"`)

#### Numeric Data
- 32-bit integers: `integer` with format `int32`
- 64-bit integers: `integer` with format `int64`
- Arbitrary precision integers: `integer` with format `bigint`
- Single precision: `number` with format `float`
- Double precision: `number` with format `double`
- Arbitrary precision decimal: `number` with format `decimal`

#### Localization & Commerce
- Country codes: `string` with format `iso-3166-alpha-2` (`"GB"`)
- Language codes: `string` with format `iso-639-1` (`"en"`)
- Language tags: `string` with format `bcp47` (`"en-DE"`)
- Currency codes: `string` with format `iso-4217` (`"EUR"`)
- Product codes: `string` with format `gtin-13` (`"5710798389878"`)

#### Binary & Encoded Data
- Binary data: `string` with format `binary` (base64url encoded)
- Byte data: `string` with format `byte` (base64url encoded)

### Date-Time Requirements
- Must use uppercase `T` separator between date and time
- Must use uppercase `Z` for UTC timezone
- Prefer UTC without local offsets (`2015-05-28T14:07:17Z`)
- Store all dates in UTC; localize in presentation layer only

### Numeric Format Requirement
Always specify format for `number` and `integer` types to prevent precision ambiguity.

## Consequences

### Positive
- Eliminates precision ambiguity in numeric types
- Ensures consistent date/time interpretation across timezones
- Enables automatic validation via OpenAPI tooling
- Language-specific type mapping becomes deterministic

### Negative
- More verbose than raw integers/timestamps
- Requires parsing effort for date strings
- Must document exceptions when standards don't fit

## Mechanical Enforcement

### Rule ID: API-FORMAT-001

### Patterns
```yaml
rules:
  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#238
    description: Date/time properties must use standard formats
    message: "Use 'date', 'date-time', 'time', 'duration', or 'period' format for temporal data"
    given: "$.paths..*.responses..*.content..*.schema..properties[?(@.type == 'string' && (@.description =~ /date|time|timestamp|duration|period/i))]"
    severity: error
    then:
      field: format
      function: enumeration
      functionOptions:
        values:
          - date
          - date-time
          - time
          - duration
          - period

  - documentationUrl: https://opensource.zalando.com/restful-api-guidelines/#171
    description: Number/integer types must specify format
    message: "Number types must have format: int32, int64, bigint, float, double, or decimal"
    given: "$.paths..*.responses..*.content..*.schema..properties[?(@.type == 'number' || @.type == 'integer')]"
    severity: error
    then:
      field: format
      function: truthy
```

### Valid Examples
```yaml
created_at:
  type: string
  format: date-time
  example: "2019-07-30T06:43:40.252Z"

price:
  type: number
  format: decimal
  example: "19.99"

country:
  type: string
  format: iso-3166-alpha-2
  example: "GB"
```

### Violations
```yaml
created_at:
  type: integer
  example: 1460062925

price:
  type: number
  example: 19.99

country:
  type: string
  example: "USA"
```

## References
- [Zalando API Guidelines #238](https://opensource.zalando.com/restful-api-guidelines/#238)
- [Zalando API Guidelines #171](https://opensource.zalando.com/restful-api-guidelines/#171)
- RFC 3339, RFC 4122, ISO 8601