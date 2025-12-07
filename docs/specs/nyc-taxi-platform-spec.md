# NYC Taxi Analytics Platform - Project Specification

## Overview

A taxi data platform serving three distinct user groups with the NYC taxi trip dataset (1.5B+ trips, 2009-2024).

---

## Product 1: Public Fare Estimation Service

**Target User:** General public planning taxi trips

**Core Value:** "What will my taxi ride cost?"

### Features

**Fare Estimation:**
- Predict fare from pickup location to dropoff location
- Show fare ranges based on time of day/week
- Display typical trip duration
- Compare costs at different times ("$5 cheaper if you wait 2 hours")

**Historical Patterns:**
- "What's the typical fare from JFK to Times Square?"
- "How much do taxis cost in this neighborhood?"
- Seasonal variation insights

**Use Cases:**
- Tourist planning trip budget
- Commuter comparing taxi vs rideshare costs
- Event attendee estimating travel costs

---

## Product 2: Self-Service Analytics Platform

**Target User:** Data analysts, urban planners, business intelligence teams

**Core Value:** "Explore taxi data without writing code"

### Features

**Interactive Query Builder:**
- Filter trips by date range, location, fare, distance
- Complex geo queries (trips within polygon, radius from point)
- Time-based filters (peak hours, weekdays vs weekends)
- Chained filters (trips > $50 AND > 10 miles AND to airport zones)

**Pre-Built Visualizations:**
- Heatmaps (pickup/dropoff density, fare distribution by zone)
- Time series (trips per hour/day/month)
- Zone comparisons (Manhattan vs Brooklyn patterns)
- Route analysis (most common origin-destination pairs)

**Data Export:**
- Export filtered datasets (CSV, Parquet, JSON)
- Scheduled exports (daily/weekly aggregations)
- API access for programmatic queries

**Custom Dashboards:**
- Build and save custom views
- Share dashboards with team members
- Embed visualizations in reports

**Analysis Examples:**
- "Show me fare trends during COVID-19 lockdowns"
- "Generate heatmap of Friday night pickups in Manhattan"
- "Compare taxi usage before/after subway fare increase"
- "Identify high-demand routes for fleet optimization"

---

## Product 3: Regulatory Oversight Dashboard

**Target User:** NYC TLC officials, city administrators

**Core Value:** "Monitor and audit taxi operations"

### Features

**Outlier Detection:**
- Flag suspicious trips (unusually high fares, impossible routes)
- Review flagged trips with full details
- Mark trips as reviewed/investigated

**Access Management:**
- Approve/deny analyst account requests
- Manage user permissions
- Audit data access logs

**System Health:**
- Monitor API usage
- Track heatmap generation jobs
- View data ingestion pipeline status

**Full Detail Access:**
- Exact coordinates (not anonymized)
- Driver/vehicle identifiers
- Payment method details

---

## User Access Levels

| Feature | Public | Analysts | Officials |
|---------|--------|----------|-----------|
| Fare estimation | ✅ | ✅ | ✅ |
| Aggregate statistics | ✅ | ✅ | ✅ |
| Individual trip queries | ❌ | ✅ (anonymized) | ✅ (full details) |
| Custom visualizations | ❌ | ✅ | ✅ |
| Data export | ❌ | ✅ | ✅ |
| Outlier review | ❌ | ❌ | ✅ |
| User management | ❌ | ❌ | ✅ |

**Anonymization (Analysts):**
- Coordinates rounded to ~100m grid
- No driver/vehicle identifiers
- Payment methods grouped (card/cash/unknown)

---

## Core API Capabilities

### Fare Estimation
```
POST /api/estimates/fare
{
  "pickup_location": {"lat": 40.7589, "lon": -73.9851},
  "dropoff_location": {"lat": 40.6413, "lon": -73.7781},
  "datetime": "2024-12-15T18:00:00Z"
}
→ Returns predicted fare range, duration, historical patterns
```

### Trip Queries
```
GET /api/trips?pickup_date_range=2020-01-01/2020-01-31&zone_id=161
→ Returns paginated trip list (authorization-filtered)
```

### Analytics/Heatmaps
```
POST /api/heatmaps
{
  "date_range": "2020-01-01/2020-01-31",
  "metric": "avg_fare",
  "resolution": "100m"
}
→ Returns 202 Accepted with job tracking URL
```

### Statistics
```
GET /api/statistics/by-zone?zone_id=161&month=2020-01
→ Returns aggregate metrics for zone
```

---

## Technical Goals

This project serves as a **comprehensive test of all Architecture Decision Records (ADRs)**:

**Python Standards (ADRs 001-006):**
- Import patterns, docstrings, dataclasses, operator module usage

**API Design (ADRs 007-019):**
- Standard formats, pagination, performance optimization, security, URL design

**Django Implementation (ADRs 020-025):**
- Framework selection, OpenAPI generation, headers, deprecation, performance, pagination

**Real-World Validation:**
- 1.5B+ trips expose pagination/performance issues
- Real money values test decimal precision
- Timezone data tests datetime handling
- Complex authorization tests security patterns
- Async processing tests job queue patterns

---

## Success Criteria

### Functional
- ✅ Public users get accurate fare estimates
- ✅ Analysts can build dashboards without writing code
- ✅ Officials can review flagged trips and manage access

### Technical
- ✅ Cursor pagination handles 100M+ trips without timeout
- ✅ Field filtering reduces payload size 80%+
- ✅ Heatmap generation processes 10M trips in <60 seconds
- ✅ No fare precision loss (Decimal everywhere)
- ✅ Authorization correctly filters data by role
- ✅ All 25 ADRs mechanically enforced via Semgrep

### Quality
- ✅ OpenAPI spec validates in CI
- ✅ Pre-commit hooks catch violations before review
- ✅ Real data edge cases handled (nulls, outliers, invalid coordinates)
- ✅ Performance benchmarks met (query times, throughput)

---

## Out of Scope (For Now)

- Real-time trip tracking (we have historical data only)
- Driver/passenger matching (not a dispatch system)
- Payment processing (analysis only, not transactions)
- Mobile apps (API-first, clients can be built later)
- Machine learning model training (analysts export data for external training)

---

## Dataset

**NYC TLC Trip Record Data:**
- 1.5B+ taxi trips (2009-2024)
- ~200GB of data
- Fields: pickup/dropoff datetime, locations, fare, distance, payment type, passenger count
- Real distribution problems, edge cases, and performance challenges

---

## Next Steps

1. **Phase 1 - Foundation:** Domain models, basic CRUD, authentication, cursor pagination
2. **Phase 2 - Analytics:** Heatmaps, statistics endpoints, async job processing
3. **Phase 3 - Fare Estimation:** Prediction model, confidence intervals, time-based variations
4. **Phase 4 - Polish:** Deprecation, idempotency, caching, full ADR compliance
