# Advanced Architectural Patterns

**Prerequisites:** You should have a working polyglot architecture (see [001-language-framework-choices.md](./001-language-framework-choices.md)) and be hitting specific scale problems.

⚠️ **Warning:** These patterns add significant complexity. Only use them when you have **measurable proof** you need them, not because they sound cool.

---

## Table of Contents

1. [CQRS (Command Query Responsibility Segregation)](#cqrs)
2. [Event Sourcing](#event-sourcing)
3. [Database Sharding](#database-sharding)
4. [Analytical Data Storage](#analytical-data-storage)
5. [Observability (Logging, Metrics, Tracing)](#observability)
6. [Advanced API Security (JWKS)](#jwks)

---

<a name="cqrs"></a>
## 1. CQRS (Command Query Responsibility Segregation)

**Problem it solves:** Your write operations (create/update/delete) need different optimization than your read operations (queries).

**When you need it:**
- ❌ **Don't use if:** Your app has <10k users, simple CRUD operations, or reads/writes have similar load
- ✅ **Use when:** 
  - Read operations vastly outnumber writes (90%+ reads)
  - Complex reporting queries slow down your transactional database
  - You need different data models for writes vs reads

### CQRS Architecture

```
External Client
     │
     ▼
┌────────────────────────────────────────────────┐
│  Command Side (Writes)     Query Side (Reads)  │
│                                                 │
│  POST /api/orders          GET /api/orders     │
│       │                           ▲            │
│       ▼                           │            │
│  ┌──────────┐              ┌──────────┐       │
│  │ Commands │              │ Queries  │       │
│  │ (Django) │              │ (FastAPI)│       │
│  └──────────┘              └──────────┘       │
│       │                           ▲            │
│       ▼                           │            │
│  PostgreSQL ──────sync/async──────┘            │
│  (normalized)      ▲       PostgreSQL          │
│                    │       (denormalized,      │
│                    │        materialized views)│
│                    │                            │
│                RabbitMQ                         │
│                (events)                         │
└────────────────────────────────────────────────┘
```

### Implementation Pattern

**Command Side (Django):**
```python
# Write-optimized, normalized model
class Order(models.Model):
    user = models.ForeignKey(User)
    status = models.CharField(max_length=20)
    total = models.DecimalField()
    created_at = models.DateTimeField(auto_now_add=True)

@api_view(['POST'])
def create_order(request):
    order = Order.objects.create(**request.data)
    
    # Publish event for read model sync
    publish_event('order.created', {
        'order_id': order.id,
        'user_id': order.user_id,
        'total': str(order.total)
    })
    
    return Response({'id': order.id})
```

**Query Side (FastAPI):**
```python
# Read-optimized, denormalized model
class OrderReadModel(BaseModel):
    order_id: int
    user_name: str  # Denormalized!
    user_email: str # Denormalized!
    status: str
    total: Decimal
    items_count: int

@app.get("/api/orders")
async def get_orders():
    # Queries from denormalized read database
    # Fast because all data is in one table
    return await db.fetch_all(
        "SELECT * FROM order_read_model ORDER BY created_at DESC"
    )
```

**Event Handler (syncs Command → Query):**
```python
# Listens to RabbitMQ events and updates read model
def handle_order_created(event):
    user = fetch_user(event['user_id'])  # May call Django API
    
    # Update denormalized read model
    db.execute("""
        INSERT INTO order_read_model 
        (order_id, user_name, user_email, status, total)
        VALUES (?, ?, ?, ?, ?)
    """, event['order_id'], user.name, user.email, 'pending', event['total'])
```

### Trade-offs

**Pros:**
- Write side optimized for consistency and business logic
- Read side optimized for query performance
- Scale reads independently (add read replicas)

**Cons:**
- **Eventual consistency:** Read model lags behind writes (seconds to minutes)
  - ⚠️ **Critical distinction:** Command side has strong consistency (ACID transactions), Query side has eventual consistency
  - Users may see stale data: "I just created an order, why don't I see it in the list?"
  - Must handle this in UI: "Your order is being processed..."
- **Operational complexity:** Two databases, synchronization mechanism
- **More code:** Separate models, event handlers

**Reality check:** Most teams don't need CQRS. Use Postgres materialized views first:
```sql
CREATE MATERIALIZED VIEW order_summary AS
  SELECT o.id, u.name, u.email, o.status, o.total
  FROM orders o JOIN users u ON o.user_id = u.id;

REFRESH MATERIALIZED VIEW CONCURRENTLY order_summary;
```

---

<a name="event-sourcing"></a>
## 2. Event Sourcing

**Problem it solves:** You need a complete audit trail of all changes, or you need to reconstruct state at any point in time.

**When you need it:**
- ❌ **Don't use if:** Basic CRUD is enough, or you only need "current state"
- ✅ **Use when:**
  - Financial transactions (every change must be audited)
  - Compliance requirements (GDPR, SOX, HIPAA)
  - You need to replay events to rebuild state
  - "How did we get here?" is a frequent question

### Event Sourcing Architecture

```
Traditional (State-Based):
  users table: {id: 1, name: "Alice", email: "alice@example.com"}
  (Previous states are lost)

Event Sourcing (Event-Based):
  events table:
    {id: 1, type: "UserCreated", data: {name: "Alice", email: "alice@example.com"}}
    {id: 2, type: "EmailChanged", data: {new_email: "alice.new@example.com"}}
    {id: 3, type: "NameChanged", data: {new_name: "Alice Smith"}}
  
  Current state = replay all events
```

### Implementation Pattern

**Event Store (PostgreSQL):**
```python
class Event(models.Model):
    aggregate_id = models.CharField(max_length=100)  # e.g., "user-123"
    aggregate_type = models.CharField(max_length=50) # e.g., "User"
    event_type = models.CharField(max_length=100)    # e.g., "UserCreated"
    event_data = models.JSONField()
    version = models.IntegerField()  # Optimistic locking
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['aggregate_id', 'version']),
        ]
```

**Write (Append-only):**
```python
def create_user(user_id, name, email):
    # Never UPDATE, always INSERT
    Event.objects.create(
        aggregate_id=f"user-{user_id}",
        aggregate_type="User",
        event_type="UserCreated",
        event_data={"name": name, "email": email},
        version=1
    )
    
    # Publish to message queue for read models
    publish_event("UserCreated", {"user_id": user_id, "name": name, "email": email})

def change_email(user_id, new_email):
    current_version = Event.objects.filter(
        aggregate_id=f"user-{user_id}"
    ).count()
    
    Event.objects.create(
        aggregate_id=f"user-{user_id}",
        aggregate_type="User",
        event_type="EmailChanged",
        event_data={"new_email": new_email},
        version=current_version + 1
    )
```

**Read (Replay events to build current state):**
```python
def get_user(user_id):
    events = Event.objects.filter(
        aggregate_id=f"user-{user_id}"
    ).order_by('version')
    
    # Replay events
    user = {}
    for event in events:
        if event.event_type == "UserCreated":
            user = event.event_data.copy()
        elif event.event_type == "EmailChanged":
            user['email'] = event.event_data['new_email']
        elif event.event_type == "NameChanged":
            user['name'] = event.event_data['new_name']
    
    return user
```

**Optimization: Snapshots**
```python
# Instead of replaying 10,000 events, store snapshots every 100 events
class Snapshot(models.Model):
    aggregate_id = models.CharField(max_length=100)
    version = models.IntegerField()  # Version at snapshot time
    state = models.JSONField()       # Full state at that version

def get_user_optimized(user_id):
    # Get latest snapshot
    snapshot = Snapshot.objects.filter(
        aggregate_id=f"user-{user_id}"
    ).order_by('-version').first()
    
    if snapshot:
        user = snapshot.state.copy()
        start_version = snapshot.version + 1
    else:
        user = {}
        start_version = 1
    
    # Replay only events after snapshot
    events = Event.objects.filter(
        aggregate_id=f"user-{user_id}",
        version__gte=start_version
    ).order_by('version')
    
    for event in events:
        apply_event(user, event)
    
    return user
```

### Trade-offs

**Pros:**
- Complete audit trail (every change is recorded)
- Time travel (reconstruct state at any point)
- Event replay for debugging/testing
- Natural fit for event-driven architectures

**Cons:**
- **Storage grows forever** (every change = new event)
- **Queries are slow** (must replay events)
- **Schema changes are hard** (old events have old schemas)
- **Complexity** (projection workers, snapshots, versioning)

**Reality check:** Use event sourcing only for aggregates that absolutely need it (e.g., `Order`, `Payment`), not your entire system.

---

<a name="database-sharding"></a>
## 3. Database Sharding (Horizontal Partitioning)

**Problem it solves:** A single PostgreSQL instance can't handle your data volume or write throughput.

**When you need it:**
- ❌ **Don't use if:** <1TB of data, <10k writes/sec, or you haven't tried vertical scaling (bigger instance)
- ✅ **Use when:**
  - Single database is >5TB
  - Writes exceed 50k/sec
  - Read replicas aren't enough

### Sharding Strategies

| Strategy | How It Works | Pros | Cons | Best For |
|----------|-------------|------|------|----------|
| **Range Sharding** | User IDs 1-1M → Shard 1<br>User IDs 1M-2M → Shard 2 | Simple logic | Hotspots (new users on latest shard) | Time-series data |
| **Hash Sharding** | `hash(user_id) % num_shards` | Balanced distribution | Cross-shard queries expensive | User data, high write throughput |
| **Geographic** | US users → US shard<br>EU users → EU shard | Data locality, compliance | Uneven distribution | Multi-region apps |

### Implementation: Hash Sharding

**Shard Router (Go service):**
```go
const NUM_SHARDS = 4

var shards = map[int]*sql.DB{
    0: connectDB("shard-0.postgres.example.com"),
    1: connectDB("shard-1.postgres.example.com"),
    2: connectDB("shard-2.postgres.example.com"),
    3: connectDB("shard-3.postgres.example.com"),
}

func getShardForUser(userID int) *sql.DB {
    shardID := userID % NUM_SHARDS
    return shards[shardID]
}

func GetUser(userID int) (*User, error) {
    db := getShardForUser(userID)
    
    var user User
    err := db.QueryRow(
        "SELECT id, name, email FROM users WHERE id = $1",
        userID,
    ).Scan(&user.ID, &user.Name, &user.Email)
    
    return &user, err
}
```

**Cross-Shard Query (Expensive!):**
```go
// Get all users named "Alice" - must query ALL shards
func GetUsersByName(name string) ([]User, error) {
    var allUsers []User
    
    // Query each shard in parallel
    var wg sync.WaitGroup
    results := make(chan []User, NUM_SHARDS)
    
    for shardID := 0; shardID < NUM_SHARDS; shardID++ {
        wg.Add(1)
        go func(shard *sql.DB) {
            defer wg.Done()
            
            rows, _ := shard.Query(
                "SELECT id, name, email FROM users WHERE name = $1",
                name,
            )
            // ... scan rows and send to results channel
        }(shards[shardID])
    }
    
    wg.Wait()
    close(results)
    
    // Merge results from all shards
    for users := range results {
        allUsers = append(allUsers, users...)
    }
    
    return allUsers, nil
}
```

### Rebalancing (Adding Shards)

**Problem:** You start with 4 shards, but need to add 4 more (8 total). Half your data needs to move.

**Solution: Consistent Hashing** (minimize data movement)
```go
import "github.com/stathat/consistent"

var ring = consistent.New()

func init() {
    ring.Add("shard-0")
    ring.Add("shard-1")
    ring.Add("shard-2")
    ring.Add("shard-3")
}

func getShardForUser(userID string) string {
    shard, _ := ring.Get(userID)
    return shard
}

// When adding a new shard, only 1/5 of data moves (not 1/2)
func addShard() {
    ring.Add("shard-4")
}
```

### Trade-offs

**Pros:**
- Linear scalability (double shards = double capacity)
- Each shard is smaller, faster

**Cons:**
- **Cross-shard queries are expensive** (or impossible)
- **Cross-shard transactions** require 2-phase commit (2PC), which is problematic:
  - **High latency:** 2 network round-trips minimum (prepare + commit)
  - **Blocking:** Locks held during entire 2PC process
  - **Failure complexity:** If coordinator crashes, transactions stuck in limbo
  - **Recommendation:** Design your sharding key to avoid cross-shard transactions entirely
- **Rebalancing is painful** (data movement)
- **Application complexity** (shard routing logic)

**Reality check:** Before sharding, try:
1. **Vertical scaling** (bigger Postgres instance)
2. **Read replicas** (offload reads)
3. **Partitioning** (Postgres native table partitioning)
4. **Archiving old data** (move to cheaper storage)

Most teams never need sharding.

---

<a name="analytical-data-storage"></a>
## 4. Analytical Data Storage

**Problem it solves:** Analytical queries (reports, dashboards, aggregations) slow down your transactional database.

**OLTP vs OLAP:**
- **OLTP (Online Transaction Processing):** Your primary database (Postgres) - optimized for fast writes, transactions, and point queries
- **OLAP (Online Analytical Processing):** Analytical storage (DuckDB, ClickHouse) - optimized for complex queries, aggregations, and scanning large datasets

**When you need it:**
- ❌ **Don't use if:** Simple `GROUP BY` queries work fine on Postgres
- ✅ **Use when:**
  - Queries scan millions of rows
  - Complex aggregations timeout
  - Reports impact production performance

### Storage Options (Postgres First)

**Hierarchy of solutions:**

```
1. Postgres Indexes (try this first)
   └─► CREATE INDEX idx_orders_created_at ON orders(created_at);

2. Postgres Materialized Views (if indexes aren't enough)
   └─► CREATE MATERIALIZED VIEW monthly_revenue AS
       SELECT date_trunc('month', created_at) as month, SUM(total)
       FROM orders GROUP BY month;

3. Postgres Read Replica (separate analytical queries)
   └─► Route all analytics to replica, production to primary

4. Postgres Foreign Data Wrapper (query across databases)
   └─► Connect Postgres to external systems

5. DuckDB (when Postgres is impossible)
   └─► Export data to Parquet files, query with DuckDB
```

### When to Use DuckDB

**Postgres is impossible when:**
- You need to query data in S3/GCS without loading into a database
- You're querying 100GB+ Parquet files
- You need OLAP performance without running a separate database server
- You're doing ad-hoc analysis on laptop/edge device
- You're building a data lake structure (DuckLake pattern) with organized Parquet files

### DuckDB Implementation

**Export from Postgres to Parquet:**
```python
# Nightly job: Export orders to Parquet
import duckdb

con = duckdb.connect('analytics.duckdb')

# Connect to Postgres
con.execute("""
    INSTALL postgres;
    LOAD postgres;
    
    ATTACH 'dbname=mydb user=postgres host=localhost' AS pg (TYPE POSTGRES);
""")

# Export to Parquet (columnar format, compressed)
con.execute("""
    COPY (SELECT * FROM pg.orders WHERE created_at >= '2024-01-01')
    TO 's3://mybucket/orders/2024.parquet' (FORMAT PARQUET);
""")
```

**Query Parquet with DuckDB (from any service):**
```python
import duckdb

# Query files directly (no database server needed)
result = duckdb.sql("""
    SELECT 
        date_trunc('month', created_at) as month,
        COUNT(*) as order_count,
        SUM(total) as revenue
    FROM 's3://mybucket/orders/*.parquet'
    WHERE created_at >= '2024-01-01'
    GROUP BY month
    ORDER BY month
""").fetchall()

print(result)
```

**Integration with services:**
```python
# FastAPI endpoint for analytics
@app.get("/api/analytics/revenue")
async def get_revenue(start_date: str):
    con = duckdb.connect('analytics.duckdb', read_only=True)
    
    result = con.execute("""
        SELECT 
            date_trunc('day', created_at) as date,
            SUM(total) as revenue
        FROM 's3://mybucket/orders/*.parquet'
        WHERE created_at >= ?
        GROUP BY date
        ORDER BY date
    """, [start_date]).fetchdf()  # Returns pandas DataFrame
    
    return result.to_dict('records')
```

### Trade-offs

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Postgres Indexes** | Simple, fast, **real-time (strong consistency)** | Limited for complex queries | First try |
| **Materialized Views** | Fast, stays in Postgres | Manual refresh, **eventual consistency** | Scheduled reports |
| **Read Replica** | Isolates analytical load, **near real-time** | Still limited by Postgres OLAP performance | Medium load |
| **DuckDB** | OLAP-optimized, query files | **Eventual consistency** (export lag), export pipeline | Heavy analytics, S3 data lakes |

**Consistency implications:** Moving down this list means accepting more staleness. DuckDB data is typically hours or days old (updated via batch jobs), not real-time.

**Reality check:** Start with Postgres materialized views. Only move to DuckDB when:
1. Postgres queries timeout (>30 seconds)
2. You're already storing data in S3/GCS
3. You need to query 100GB+ datasets

---

<a name="observability"></a>
## 5. Observability: Logging, Metrics, and Tracing

**Problem it solves:** In distributed systems, understanding "what's happening" and "why is it slow" requires structured data about your services.

### The Three Pillars

| Pillar | What It Tells You | Example | When to Query |
|--------|-------------------|---------|---------------|
| **Logs** | Discrete events | `"User 123 failed login"` | Debugging specific errors |
| **Metrics** | Numerical trends | `http_requests_total{status="200"}` | Dashboard monitoring |
| **Traces** | Request flow | `API → Django → Go took 500ms` | Performance debugging |

### OpenTelemetry (OTel) - The Standard

**One library for all three pillars.**

**Installation (Python - FastAPI):**
```bash
pip install opentelemetry-api opentelemetry-sdk \
    opentelemetry-instrumentation-fastapi \
    opentelemetry-exporter-otlp
```

**Code (FastAPI):**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracer
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

app = FastAPI()

# Auto-instrument FastAPI (captures all HTTP requests)
FastAPIInstrumentor.instrument_app(app)

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    tracer = trace.get_tracer(__name__)
    
    # Manual span for database query
    with tracer.start_as_current_span("db.query"):
        user = await db.fetch_one(
            "SELECT * FROM users WHERE id = ?", user_id
        )
    
    # Manual span for external API call
    with tracer.start_as_current_span("external.auth_service"):
        perms = await http.get(f"http://django:8000/api/permissions/{user_id}")
    
    return {"user": user, "permissions": perms}
```

### Distributed Tracing Deep Dive

**Problem:** A request touches 5 services. How do you track it?

**Solution:** Trace ID propagation.

```
Browser → NestJS → Django → Go → Redis
   │         │        │       │      │
   └─────────┴────────┴───────┴──────┘
         All share same trace_id
```

**Trace Structure:**
```
Trace: abc123 (full request journey)
  │
  ├── Span: NestJS handler (200ms)
  │     └── Span: Call Django API (150ms)
  │           └── Span: Django DB query (100ms)
  │
  └── Span: Call Go gRPC service (50ms)
        └── Span: Redis GET (5ms)
```

**Implementation (context propagation):**
```python
# NestJS calls Django, passes trace_id in headers
import { trace } from '@opentelemetry/api';

async function callDjango(userId: string) {
  const span = trace.getActiveSpan();
  const traceId = span.spanContext().traceId;
  
  // Inject trace context into HTTP headers
  const response = await fetch(`http://django:8000/api/users/${userId}`, {
    headers: {
      'traceparent': `00-${traceId}-${span.spanContext().spanId}-01`
    }
  });
  
  return response.json();
}
```

**Django receives and continues trace:**
```python
# Django automatically extracts trace context from headers (with OTel instrumentation)
from opentelemetry.instrumentation.django import DjangoInstrumentor

DjangoInstrumentor().instrument()

# Now all Django spans will be children of NestJS span
```

### Logging to DuckDB (Optional)

**If you want to query logs with SQL:**

```python
# Export OTel logs to JSON files
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# Logs go to OTel Collector → File exporter → DuckDB queries them

# Query logs with DuckDB
import duckdb

con = duckdb.connect()
logs = con.execute("""
    SELECT 
        timestamp,
        severity,
        body,
        trace_id
    FROM read_json_auto('/var/log/app/*.json')
    WHERE severity = 'ERROR'
    AND timestamp > NOW() - INTERVAL '1 hour'
    ORDER BY timestamp DESC
""").fetchall()
```

### Trade-offs

**Pros:**
- **Distributed tracing solves "where's the slowness?"**
- OpenTelemetry is vendor-neutral (switch backends easily)
- Auto-instrumentation = minimal code changes

**Cons:**
- **Performance overhead** (~1-5% latency increase)
- **Storage costs** (traces are large)
- **Learning curve** (understanding spans, context propagation)

**Reality check:** 
1. Start with logs (structured JSON)
2. Add metrics (Prometheus format)
3. Add tracing only when debugging distributed latency

---

<a name="jwks"></a>
## 6. Advanced API Security: JWKS (JSON Web Key Set)

**Problem it solves:** In a microservices architecture, every service needs to validate JWT tokens without calling the auth server on every request.

**When you need it:**
- ❌ **Don't use if:** Single service, session-based auth works fine
- ✅ **Use when:**
  - Multiple services need to validate JWTs
  - You need to rotate signing keys without downtime
  - Using OAuth2/OIDC (Auth0, Keycloak, AWS Cognito)

### How JWKS Works

```
1. User logs in:
   Client → Auth Server (Django/Auth0)
   ← JWT token (signed with private key)

2. User makes API request:
   Client → API Service (NestJS/Go)
         → Fetch public key from JWKS endpoint
         → Validate JWT signature with public key
         → Allow/deny request

3. Key rotation (seamless):
   Auth Server rotates private key
   → Updates JWKS endpoint with new public key
   → API Services auto-fetch new key on next request
```

### Implementation

**Auth Server (Django) - Exposes JWKS endpoint:**
```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from cryptography.hazmat.primitives import serialization
import jwt

PRIVATE_KEY = load_private_key()  # RSA private key
PUBLIC_KEY = PRIVATE_KEY.public_key()

@api_view(['POST'])
def login(request):
    user = authenticate(request.data['username'], request.data['password'])
    
    payload = {
        'user_id': user.id,
        'exp': datetime.now() + timedelta(hours=1)
    }
    
    # Sign JWT with private key
    token = jwt.encode(payload, PRIVATE_KEY, algorithm='RS256', headers={'kid': 'key-1'})
    
    return Response({'token': token})

@api_view(['GET'])
def jwks(request):
    """Public endpoint: /.well-known/jwks.json"""
    
    # Export public key in JWK format
    public_numbers = PUBLIC_KEY.public_numbers()
    
    return Response({
        'keys': [{
            'kty': 'RSA',
            'kid': 'key-1',  # Key ID (for rotation)
            'use': 'sig',
            'n': base64url_encode(public_numbers.n),
            'e': base64url_encode(public_numbers.e)
        }]
    })
```

**API Service (Go) - Validates JWT using JWKS:**
```go
package main

import (
    "github.com/golang-jwt/jwt/v5"
    "github.com/MicahParks/keyfunc/v2"
)

var jwks *keyfunc.JWKS

func init() {
    // Fetch JWKS from auth server (caches keys, auto-refreshes)
    var err error
    jwks, err = keyfunc.Get("https://auth.example.com/.well-known/jwks.json", keyfunc.Options{
        RefreshInterval: 1 * time.Hour,
    })
    if err != nil {
        panic(err)
    }
}

func validateToken(tokenString string) (*jwt.Token, error) {
    // Parse and validate token using JWKS
    token, err := jwt.Parse(tokenString, jwks.Keyfunc)
    
    if err != nil {
        return nil, err
    }
    
    if !token.Valid {
        return nil, errors.New("invalid token")
    }
    
    return token, nil
}

func authMiddleware(c *gin.Context) {
    authHeader := c.GetHeader("Authorization")
    tokenString := strings.TrimPrefix(authHeader, "Bearer ")
    
    token, err := validateToken(tokenString)
    if err != nil {
        c.JSON(401, gin.H{"error": "Unauthorized"})
        c.Abort()
        return
    }
    
    // Extract claims
    claims := token.Claims.(jwt.MapClaims)
    c.Set("user_id", claims["user_id"])
    
    c.Next()
}
```

### Key Rotation (Zero Downtime)

**Problem:** You need to rotate your signing key (security best practice), but don't want to invalidate all existing tokens.

**Solution:** Overlap period.

```
Day 1: Auth server uses key-1 (signs tokens)
       JWKS exposes: [key-1 public]

Day 2: Auth server adds key-2
       JWKS exposes: [key-1 public, key-2 public]
       Signs new tokens with key-2

Day 3: Old tokens (key-1) still valid
       New tokens (key-2) also valid
       API services can validate both

Day 4: All key-1 tokens expired (1 hour TTL)
       Remove key-1 from JWKS
       JWKS exposes: [key-2 public]
```

**Auth Server (rotation):**
```python
KEYS = {
    'key-1': load_key('key-1.pem'),  # Old key
    'key-2': load_key('key-2.pem'),  # New key
}

ACTIVE_KEY_ID = 'key-2'  # Sign with new key

@api_view(['POST'])
def login(request):
    token = jwt.encode(
        payload, 
        KEYS[ACTIVE_KEY_ID], 
        algorithm='RS256',
        headers={'kid': ACTIVE_KEY_ID}  # Token says "I'm signed with key-2"
    )
    return Response({'token': token})

@api_view(['GET'])
def jwks(request):
    return Response({
        'keys': [
            export_public_key(KEYS['key-1'], 'key-1'),  # Still exposed for old tokens
            export_public_key(KEYS['key-2'], 'key-2'),  # New tokens use this
        ]
    })
```

### Trade-offs

**Pros:**
- **Stateless authentication** (no session store)
- **Key rotation without downtime**
- **Services validate tokens independently** (no auth server call)

**Cons:**
- **Can't revoke tokens** (until expiry)
- **Tokens can't be refreshed** (must re-login)
- **Requires HTTPS** (token in header)

**Reality check:** Use JWKS if:
- You have 3+ services validating tokens
- You're using OAuth2/OIDC providers (Auth0, Keycloak)
- You need to rotate keys regularly (compliance)

Otherwise, shared secret (HMAC) is simpler:
```python
jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

---

## When to Use Each Pattern

| Pattern | Use When | Don't Use Until |
|---------|----------|-----------------|
| **CQRS** | Reads vastly outnumber writes (90%+), complex reporting | You've tried Postgres materialized views |
| **Event Sourcing** | Financial transactions, compliance, audit trails | You need more than `updated_at` timestamp |
| **Sharding** | Single DB >5TB, >50k writes/sec | Vertical scaling, read replicas fail |
| **DuckDB Analytics** | Postgres timeouts, querying S3 data lakes | Postgres indexes/views are slow |
| **OpenTelemetry** | 3+ microservices, debugging distributed latency | Single service works fine |
| **JWKS** | 3+ services validating JWTs, key rotation needs | Shared secret HMAC is enough |

---

## Anti-Patterns (Don't Do This)

❌ **Using CQRS for every entity** - Only use for entities with read/write imbalance  
❌ **Event sourcing your entire database** - Use only for aggregates needing audit trails  
❌ **Sharding before 1TB** - You don't need it yet  
❌ **Picking DuckDB over Postgres** - Postgres first, DuckDB when impossible  
❌ **Over-instrumenting with traces** - Start with logs, add tracing when debugging latency  
❌ **Rotating keys daily** - Rotate quarterly unless compliance requires more  

---

## Recommended Reading

- [Martin Fowler - CQRS](https://martinfowler.com/bliki/CQRS.html)
- [Event Sourcing - Greg Young](https://www.eventstore.com/event-sourcing)
- [Database Sharding at Scale - Pinterest](https://medium.com/pinterest-engineering/sharding-pinterest-how-we-scaled-our-mysql-fleet-3f341e96ca6f)
- [OpenTelemetry Docs](https://opentelemetry.io/docs/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
