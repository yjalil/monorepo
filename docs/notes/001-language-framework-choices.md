# Language and Framework Choices for Data APIs

## Framework Selection by Use Case

### Column 1: Full-Featured CRUD APIs with Auth/Admin
**When you need:** Complete web framework with ORM, migrations, admin panel, authentication, and batteries included. Think Django or Rails - everything you need to build a traditional web application or comprehensive REST API.

**Example scenarios:** Internal admin tools, traditional web apps, complex business logic with database relationships, when you want conventions over configuration.

### Column 2: Lightweight Microservices
**When you need:** Fast, minimal frameworks for small, focused services. Think FastAPI or Flask - you bring your own ORM and structure. Perfect when you know exactly what you need and want to avoid framework overhead.

**Example scenarios:** Single-purpose APIs, Lambda functions, Docker containers with one responsibility, when you need maximum performance with minimal dependencies.

### Column 3: Service-to-Service Communication
**When you need:** Internal APIs between your own backend services (not for browsers). This includes:
- **Synchronous RPC:** Binary protocols (gRPC) with strict contracts and type safety for request/response patterns
- **Asynchronous Events:** Message queues (Kafka, RabbitMQ) for publish/subscribe patterns

**Example scenarios:** 
- **Synchronous (gRPC):** Payment processing, real-time data pipelines, when services need immediate responses
- **Asynchronous (Message Queues):** Order processing, email notifications, background jobs, event-driven architecture

### Column 4: Real-Time Client Updates
**When you need:** Push notifications, live updates, bidirectional communication. The server needs to send data to clients without them asking. WebSockets or Server-Sent Events.

**Example scenarios:** Chat applications, live dashboards, collaborative editing (Google Docs style), real-time notifications, stock tickers, multiplayer games.

---

| Language          | Full-Featured CRUD APIs | Lightweight Microservices | Service-to-Service Communication | Real-Time Client Updates |
|-------------------|-------------------------|---------------------------|----------------------------------|--------------------------||
| Python            | Django REST Framework   | FastAPI                   | grpcio / Celery + RabbitMQ      | Django Channels / FastAPI WebSockets |
| Node.js/TypeScript| NestJS                  | Express / Fastify         | gRPC-js / Bull + Redis          | Socket.IO                |
| Rust              | Loco                    | Actix Web / Axum          | Tonic / Lapin (RabbitMQ)        | Actix/Axum WebSockets    |
| Go                | N/A (By Design)         | Gin / Echo                | gRPC-Go / NATS                  | Gorilla WebSocket        |
| Ruby              | Rails (API Mode)        | Sinatra / Roda            | GRPC gem / Sidekiq + Redis      | Rails Action Cable       |

## Framework Selection Rationale

### Python: The Comfortable Choice

**For Django/Rails Developers:** Python offers the most familiar transition with two distinct philosophies.

#### Column 1: Django REST Framework (Full-Featured)
**Use when:** You need admin panels, built-in auth, ORM migrations, and want Django's "batteries included" approach.

**Pros:**
- Everything included: admin, auth, ORM, migrations, middleware
- Browsable API for development and testing
- ViewSets eliminate boilerplate for standard CRUD
- Massive ecosystem (django-filter, django-cors-headers, etc.)
- Database relationships handled elegantly by ORM

**Cons:**
- 3-4x slower than FastAPI for simple endpoints
- Heavy memory footprint (~50-100MB per worker)
- Overkill if you don't use Django's features
- Synchronous by default (async support is improving)

**Choose DRF when:** Building internal tools, admin dashboards, or traditional web apps where developer productivity matters more than raw performance.

#### Column 2: FastAPI (Lightweight Microservices)
**Use when:** You want Python's ease but need performance. You'll handle auth/ORM yourself.

**Pros:**
- 2-3x faster than Django (comparable to Go/Node)
- Automatic OpenAPI/Swagger docs generation
- Type hints provide IDE autocomplete and validation
- Async-first design for concurrent requests
- Minimal memory (~20-30MB per worker)

**Cons:**
- No admin panel, no ORM included (bring your own SQLAlchemy)
- More architectural decisions required
- Smaller ecosystem than Django
- Team needs to establish conventions

**Choose FastAPI when:** Building focused microservices, Lambda functions, or when you need Django-like DX but FastAPI-level performance.

#### Column 3 & 4: grpcio / Django Channels / FastAPI WebSockets
**Use when:** Internal service communication (gRPC) or real-time browser updates (WebSockets).

**gRPC Pros:** Official Python implementation, works across languages
**gRPC Cons:** Python's GIL limits performance vs Go/Rust

**Channels Pros:** Extends Django patterns to WebSockets naturally
**Channels Cons:** Complex setup with Redis/workers, Django overhead

**FastAPI WebSockets Pros:** Simple async WebSocket support built-in
**FastAPI WebSockets Cons:** Less mature than Channels for complex scenarios

---

### Node.js/TypeScript: The Full-Stack Choice

**For Django/Rails Developers:** Node.js offers a middle ground between Python/Ruby and Go, with the advantage of using one language (JavaScript/TypeScript) across frontend and backend.

#### Column 1: NestJS (Full-Featured)
**Use when:** You want TypeScript across the stack with Rails-like structure and dependency injection.

**Pros:**
- **TypeScript end-to-end:** Share types between frontend and backend
- **Rails-inspired structure:** Controllers, services, modules with dependency injection
- **Massive ecosystem:** npm has a package for everything
- **Strong typing:** TypeScript catches errors at compile time
- **Performance:** 2-3x faster than Django/Rails for I/O-bound tasks
- **Microservices-friendly:** Built-in support for gRPC, message queues, GraphQL

**Cons:**
- Not as "batteries-included" as Django/Rails (no admin panel out of the box)
- npm ecosystem can be chaotic (package quality varies)
- Callback/async patterns can be complex for beginners
- Less mature than Django/Rails for monolithic apps

**Choose NestJS when:** Your frontend is React/Vue/Angular and you want one language across the stack, or when you need better performance than Django/Rails but want more structure than Go.

#### Column 2: Express / Fastify (Lightweight Microservices)
**Use when:** You want minimal overhead and maximum flexibility in Node.js.

**Express:**
- **Most popular Node.js framework** (millions of downloads/week)
- Minimal, unopinionated
- Huge middleware ecosystem
- Best for: Teams that know exactly what they want

**Fastify:**
- **2-3x faster than Express**
- Schema-based validation (like FastAPI)
- Better TypeScript support
- Best for: High-performance microservices in Node.js

**Choose Express/Fastify when:** Building lightweight APIs, Lambda functions, or when you want Node.js performance without NestJS structure.

#### Column 3 & 4: gRPC-js / Socket.IO
**gRPC-js:** Official Node.js gRPC implementation, good performance for I/O-bound services

**Socket.IO:**
- **Most popular real-time library** (even more than WebSockets alone)
- Automatic fallback to polling if WebSockets unavailable
- Room-based messaging built-in
- Used by Microsoft, Trello, and thousands of apps

**Choose Socket.IO when:** Building real-time features (chat, notifications, live dashboards) in Node.js.

**Talent Pool:** Node.js has the **largest talent pool** of all backend languages due to frontend developers knowing JavaScript.

---

### Ruby: The Familiar Alternative

**For Rails Developers:** Ruby offers the same choice pattern as Python - full-featured vs lightweight.

#### Column 1: Rails API Mode (Full-Featured)
**Use when:** You want Rails conventions, ActiveRecord, and rapid scaffolding.

**Pros:**
- Fastest prototyping of any framework (generators, scaffolds)
- ActiveRecord is incredibly elegant for complex queries
- Gems for everything (Devise, CanCanCan, Sidekiq)
- Convention over configuration = fewer decisions

**Cons:**
- Similar performance to Django (~50-100 req/sec per worker)
- Memory heavy (80-150MB per worker)
- Rails "magic" makes debugging harder for newcomers
- Smaller talent pool than Python/JS

**Choose Rails when:** Your team knows Rails and values its conventions, or when rapid prototyping is critical.

#### Column 2: Sinatra/Roda (Lightweight Microservices)
**Use when:** You want Ruby but not Rails overhead. Like FastAPI is to Django.

**Sinatra Pros:** Minimal, expressive, easy to learn
**Roda Pros:** Even faster than Sinatra, plugin architecture

**Cons:** Much smaller ecosystem than Rails, team needs to build structure

**Choose Sinatra/Roda when:** Building small APIs where Rails is overkill but you want Ruby's expressiveness.

#### Column 3 & 4: GRPC gem / Action Cable
**Action Cable:** Built into Rails 5+, good for real-time features in Rails apps
**GRPC gem:** Functional but Ruby's performance limits its use for high-throughput service communication

---

### Go: The Performance Upgrade

**For Django/Rails Developers:** Go is where you go when performance becomes critical, but you'll miss Django/Rails conveniences.

#### Column 1: No Full-Featured Framework (By Design)

**Go intentionally has no Rails/Django/Loco equivalent.**

Go's philosophy: **"A little copying is better than a little dependency."** The community avoids "magic" frameworks.

**Why Go has no batteries-included framework:**
- Go values **explicitness over convention**
- **The standard library is often enough:** `net/http` and `database/sql` can handle simple CRUD without any framework
- ORMs exist (GORM, sqlc) but aren't "blessed" by the community
- You compose libraries, not adopt frameworks
- **The missing piece:** No admin panel equivalent exists (this is Go's biggest pain point for teams coming from Django/Rails)

**What you do instead:**
- Use **Gin or Echo** (lightweight, not full-featured)
- Add **GORM** separately if you want an ORM (many don't)
- Wire up auth/middleware yourself
- Use **sqlc** for type-safe SQL (popular alternative to ORMs)
- Use **golang-migrate** or **Atlas** for migrations

**Example - The Go Way:**
```go
// No `rails scaffold User` - you write this explicitly:
func CreateUser(c *gin.Context) {
    var user User
    if err := c.ShouldBindJSON(&user); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    if err := db.Create(&user).Error; err != nil {
        c.JSON(500, gin.H{"error": err.Error()})
        return
    }
    c.JSON(201, user)
}
```

**Pros of Go's approach:**
- No "framework magic" to debug
- Explicit code is easier to understand
- Smaller binaries, faster startup
- Clear dependency injection

**Cons for Django/Rails developers:**
- **No scaffolding/generators** - more boilerplate
- **No admin panel** - build your own
- **No built-in migrations** - use separate tools
- Takes 2-3x longer to build initial CRUD

**Reality check:** If you love Rails conventions, Go will feel frustrating. But if you embrace "explicit is better than implicit," Go's simplicity becomes its strength.

#### Column 2: Gin/Echo (Lightweight Microservices)
**Use when:** You need 10-40x better performance and can handle manual setup.

**Pros:**
- 10-40x faster than Django/Rails (5000+ req/sec single core)
- 10-20MB memory per service (vs 80-100MB for Django/Rails)
- Compiles to single binary = trivial Docker deployment
- Goroutines make concurrent operations natural
- No dependency hell (go.mod just works)

**Cons:**
- **No equivalent to Django admin or Rails scaffolding**
- GORM is okay but not as elegant as ActiveRecord/Django ORM
- `if err != nil` after every operation gets tedious
- More boilerplate (no "magic" metaprogramming)
- You write middleware that Rails/Django include

**Choose Go when:** You have 5+ microservices and container costs matter, or when you're hitting Python/Ruby performance limits.

**Reality check:** Building in Go takes 2-3x longer than Django/Rails initially. The payoff is deployment simplicity and operational performance.

#### Column 3: gRPC-Go
**Use when:** Service-to-service communication between microservices.

**Pros:** This is THE reference implementation. Best performance, best tooling.
**Choose when:** You're building microservices architecture and need services to communicate efficiently.

#### Column 4: Gorilla WebSocket
**Use when:** Real-time features, but you'll build more yourself than Django Channels or Action Cable.

**Pros:** Go's concurrency model is perfect for thousands of simultaneous connections
**Cons:** Less built-in than Rails/Django equivalents

---

### Rust: The Maximum Performance Choice

**For Django/Rails Developers:** Rust now has Loco, which brings Rails-like conventions to Rust performance.

#### Column 1: Loco (Full-Featured, Rails-inspired)
**Use when:** You want Rails/Django conventions but with Rust's performance and safety.

**Pros:**
- **Rails-like CLI:** `loco generate scaffold`, migrations, background jobs
- **SeaORM integration:** More ergonomic than raw Diesel
- **Convention over configuration:** Feels like Rails but compiles to Rust
- All the Rust benefits: 2-4x faster than Go, memory safety, no GC pauses
- Built on Axum (modern, ergonomic async framework)

**Cons:**
- **Still new (2023):** Smaller ecosystem than Rails/Django
- Learning curve: Rust ownership + web patterns simultaneously
- Compile times still slow (though better than raw Actix)
- Community/docs are growing but not Rails/Django mature

**Choose Loco when:**
- You love Rails but need Rust's performance/safety
- You're starting a greenfield Rust project and want structure
- You have someone on the team who knows Rust already

**Reality check:** Loco makes Rust web development feel closer to Rails, but you still need to learn Rust's ownership model. It's not a shortcut around Rust fundamentals.

#### Column 2: Actix Web / Axum (Lightweight Microservices)
**Use when:** You need maximum control and performance, can handle manual setup.

**Actix Web:**
- **Fastest web framework in benchmarks**
- Actor-based concurrency model
- More mature, larger ecosystem

**Axum:**
- **More modern and ergonomic** (what Loco is built on)
- Built by the Tokio team (async runtime)
- Better compile error messages
- Increasingly popular for new projects

**Choose Actix when:** You need absolute maximum performance and are comfortable with actors.
**Choose Axum when:** You want modern Rust async patterns and better DX than Actix.

#### Column 3: Tonic (gRPC)
**Use when:** You've already chosen Rust and need service communication.

**Pros:** Extremely fast, type-safe
**Cons:** Complex error handling compared to Go

#### Column 4: Actix/Axum WebSockets
**Use when:** You need to handle 100k+ simultaneous WebSocket connections.

**Choose Rust WebSockets when:** Go can't handle your scale (rare) or you're already using Rust.

---

**Loco vs Raw Actix:** Loco is to Actix as Rails is to Sinatra. Use Loco for full apps, Actix for focused microservices.

---

## Decision Framework for Django/Rails Developers

### Column 1: When to use Full-Featured Frameworks (Django/Rails)
**Choose Django REST Framework if:**
- You need admin panels, built-in auth, and ORM migrations
- Your team already knows Django
- Developer velocity matters more than request throughput
- You're integrating with Python data science libraries

**Choose Rails API Mode if:**
- Your team lives and breathes Rails conventions
- You value ActiveRecord's query interface
- Rapid prototyping is the top priority
- You're okay with Ruby's smaller ecosystem than Python

### Column 2: When to use Lightweight Frameworks
**Choose FastAPI if:**
- You want Python but need 3x better performance than Django
- You're building focused microservices
- Type hints and automatic docs are valuable
- You don't need Django's admin/auth out of the box

**Choose Express/Fastify (Node.js) if:**
- Your frontend team knows JavaScript/TypeScript
- You want to share types between frontend and backend
- You need better performance than Python/Ruby but more familiarity than Go
- You're building I/O-bound services (external APIs, databases)
- **Talent pool matters:** Easiest to hire for (any frontend dev can contribute)

**Choose Gin/Echo (Go) if:**
- You need 10-40x better performance than Python/Ruby
- Container size and memory usage matter (Kubernetes costs)
- You're hitting Python/Ruby/Node.js performance limits
- Team can handle 2-3x slower initial development

**Choose Loco (Rust) if:**
- You want Rails/Django conventions with Rust performance
- Memory safety is critical (financial, medical, infrastructure)
- You have at least one Rust expert to guide the team
- You're starting a greenfield project and can accept the learning curve

**Choose Actix Web (Rust) if:**
- You need absolute maximum performance
- You want lower-level control than Loco provides
- You're building focused microservices, not full apps

### Column 3: Service-to-Service Communication
**Two patterns for different needs:**

#### Synchronous RPC (gRPC)
**Use when:** You need immediate responses (request/response pattern)
- Python services → `grpcio`
- Node.js services → `gRPC-js`
- Go services → `gRPC-Go` (best performance)
- Rust services → `Tonic` (if you're already using Rust)

**Don't overthink this:** gRPC is language-agnostic. Your Python service can call your Go service seamlessly.

#### Asynchronous Events (Message Queues)
**Use when:** Background jobs, event-driven architecture, decoupled services
- **RabbitMQ:** Flexible routing, widely supported
- **Apache Kafka:** High-throughput event streaming
- **Redis (Bull/Celery/Sidekiq):** Simple task queues
- **NATS:** Lightweight, high-performance pub/sub

**Choose based on use case:**
- **RabbitMQ/Redis:** Background jobs, task queues (emails, notifications)
- **Kafka:** Event sourcing, data pipelines, audit logs
- **gRPC:** Direct service-to-service calls needing immediate responses

### Column 4: Real-Time Features
**Choose based on your primary framework:**
- Django Channels if you're already using Django
- FastAPI WebSockets if you're using FastAPI
- Rails Action Cable if you're using Rails
- Gorilla WebSocket if you're using Go (best for high concurrency)

## The Pragmatic Path for Most Teams

**Start here:** Django REST Framework or Rails API Mode
- Familiar patterns, rapid development
- Scales to 10k-50k requests/minute easily
- Use this until you have a specific performance problem

**Graduate to:** FastAPI, Node.js, or Go
- When Python/Ruby performance becomes a bottleneck
- **FastAPI** if you want to stay in Python
- **Node.js (NestJS/Fastify)** if you want one language for frontend + backend
- **Go** if you need 10x improvement and can handle the learning curve

**Consider Rust (Loco) if:**
- Go isn't fast enough (rare)
- Memory safety is a requirement, not a nice-to-have
- You're willing to invest in Rust expertise long-term
- **New option:** Loco makes Rust feel more like Rails, reducing some friction

**Only use raw Actix/Axum if:** You need absolute maximum control and Loco's conventions don't fit.

## Real-World Recommendation

**For most Django developers:**
1. Use **Django REST Framework** for your main app (admin, auth, complex business logic)
2. Use **FastAPI** for high-throughput public APIs or microservices
3. Consider **Node.js (NestJS)** if your frontend team is JavaScript-heavy
4. Use **gRPC** for synchronous service calls, **RabbitMQ/Celery** for background jobs
5. Use **Django Channels** only if you actually need real-time features

**For most Rails developers:**
1. Use **Rails API Mode** for your main app
2. Consider **Go (Gin)** for new microservices if performance matters
3. Use **Action Cable** for real-time features within Rails apps

**The truth:** Most companies never need Go or Rust. Django/Rails performance is fine for 95% of applications. Optimize your database queries first.

---

## For the Polyglot: Best of All Worlds Architecture

**You don't have to choose just one language.** Use each language where it shines in a microservices architecture.

### The Recommended Polyglot Stack

**This is the battle-tested architecture.** Each layer uses the best tool for its specific job.

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend: Next.js + TypeScript                              │
│  (Auto-generated from OpenAPI via Orval)                     │
│  Component library for rapid prototyping                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ HTTPS/JSON
┌─────────────────────────────────────────────────────────────┐
│  API Gateway: Traefik                                        │
│  (Dynamic routing, auto TLS, service discovery)              │
│  Falls back to Nginx for static assets at scale             │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬──────────────┐
        │                   │                   │              │
        ▼ REST              ▼ REST              ▼ gRPC         ▼ gRPC
┌──────────────┐   ┌──────────────┐   ┌──────────────┐  ┌────────────┐
│ Django DRF   │   │ NestJS       │   │  Gin (Go)    │  │Actix (Rust)│
│ :8000        │   │ :3000        │   │ :9000        │  │ :9001      │
│              │   │              │   │              │  │            │
│ • Admin UI   │   │ • BFF Layer  │   │ • Media      │  │ • Payments │
│ • Auth       │◄──┤ • Aggregates │◄──┤ • Analytics  │  │ • Crypto   │
│ • User CRUD  │   │   data       │   │ • Rate limit │  │            │
│ • Reports    │   │ • WebSockets │   │              │  │            │
│              │   │ • Socket.IO  │   │              │  │            │
└──────────────┘   └──────────────┘   └──────────────┘  └────────────┘
        │                   │                   │              │
        │                   │                   │              │
        └───────────────────┴─────RabbitMQ──────┴──────────────┘
                            │    (async jobs)
                            ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    │  (main DB)   │
                    │              │
                    │    Redis     │
                    │  (cache/jobs)│
                    └──────────────┘
```

### What Each Layer Does (Be Specific)

#### Layer 1: Django DRF (Port 8000)
**Purpose:** Admin operations, authentication, complex business logic  
**When to call:** Internal admin operations, user management, reports  
**Technology:** Django REST Framework + PostgreSQL + Celery

**Specific services:**
- `POST /api/auth/login` - User authentication
- `GET /admin/` - Django admin panel for ops team
- `POST /api/users/` - Complex user creation with validation
- `GET /api/reports/revenue` - Complex SQL aggregations

---

#### Layer 2: NestJS (Port 3000)
**Purpose:** Public-facing API, BFF (Backend-for-Frontend), real-time features  
**When to call:** All public mobile/web API requests  
**Technology:** NestJS + TypeScript + Socket.IO + Bull (Redis queue)

**Specific services:**
- `GET /api/v1/feed` - Aggregates data from Django + Go services
- `POST /api/v1/orders` - Places order, sends to RabbitMQ
- `WS /socket.io` - Real-time notifications
- `GET /api/v1/users/:id` - Calls Django auth service via REST
- `GET /openapi.json` - OpenAPI spec for Orval codegen

**Why NestJS here:** 
- Auto-generates OpenAPI/Swagger docs (consumed by Orval)
- TypeScript types shared with Next.js frontend via Orval
- You stay in backend mode while Orval generates frontend client code
- No manual API client writing needed

---

#### Layer 3: Gin (Go) (Port 9000)
**Purpose:** High-throughput, stateless microservices  
**When to call:** Internal gRPC calls for performance-critical operations  
**Technology:** Gin + gRPC-Go + PostgreSQL (own tables)

**Specific services:**
- `ProcessImage(imageData)` gRPC - Resize/compress images (10k req/sec)
- `TrackEvent(event)` gRPC - High-volume analytics ingestion
- `CheckRateLimit(userId)` gRPC - Sub-millisecond rate limit checks

**Why Go here:** 10x throughput, 10MB memory footprint, cheap to scale horizontally

---

#### Layer 4: Actix (Rust) (Port 9001) - Optional
**Purpose:** Safety-critical, ultra-high-performance services  
**When to call:** Payment processing, cryptographic operations  
**Technology:** Actix Web + Tonic (gRPC) + PostgreSQL

**Specific services:**
- `ProcessPayment(paymentData)` gRPC - PCI-compliant payment handling
- `SignTransaction(txData)` gRPC - Cryptographic signing

**Why Rust here:** Memory safety prevents entire classes of bugs in financial code

---

### Communication Patterns (Specific)

```
External Client (Browser/Mobile)
         │
         ▼ REST/JSON over HTTPS
    NestJS (Port 3000)
         │
         ├──► Django (Port 8000) - REST: GET /api/users/123
         │
         ├──► Go (Port 9000) - gRPC: TrackEvent(event)
         │
         └──► RabbitMQ - Async: "order.created" event
                  │
                  └──► Django Celery worker picks up background job
```

**Why Traefik (not Kong):**
- **Dynamic configuration:** Auto-discovers services from Docker/Kubernetes labels
- **Let's Encrypt built-in:** Automatic TLS certificate management
- **Simpler configuration:** YAML/TOML vs Kong's database/admin API
- **Native Docker/K8s integration:** No service registry needed
- **Middleware chains:** Rate limiting, auth, retries without plugins

**When to use Nginx instead:**
- Static file serving at massive scale (CDN-like performance)
- Edge caching with complex invalidation rules
- You need battle-tested production stability over modern features

**Example Traefik config (docker-compose.yml):**
```yaml
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  nestjs:
    image: your-nestjs-app
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.middlewares.ratelimit.ratelimit.average=100"
```

**Synchronous (when you need immediate response):**
- NestJS → Django: REST (same language ecosystem benefits)
- NestJS → Go: gRPC (high performance, type-safe)
- Go → Go: gRPC (service mesh)

**Asynchronous (fire-and-forget background jobs):**
- Any service → RabbitMQ → Celery/Bull workers
- Use for: emails, reports, data processing, webhooks

---

### Frontend Code Generation Workflow (Backend-Focused)

**You're backend-focused and don't want to write frontend code manually:**

```
1. Backend: Write NestJS API with DTOs/decorators
   └─► NestJS auto-generates /openapi.json

2. Orval: Run `orval` to generate TypeScript client
   └─► Creates typed API hooks, models, and fetchers

3. Frontend: Import generated hooks in Next.js
   └─► const { data } = useGetUsers(); // Fully typed!
```

**Example backend (NestJS):**
```typescript
@Get('/users/:id')
@ApiResponse({ type: UserDto })
async getUser(@Param('id') id: string): Promise<UserDto> {
  return this.userService.findOne(id);
}
```

**Orval generates (frontend):**
```typescript
// Auto-generated by Orval
export const useGetUser = (id: string) => {
  return useQuery<UserDto, Error>(['users', id], () => 
    fetcher<UserDto>(`/api/users/${id}`)
  );
};
```

**You write (Next.js component):**
```typescript
export default function UserProfile({ userId }: Props) {
  const { data: user } = useGetUser(userId); // Typed automatically!
  return <div>{user.name}</div>;
}
```

**Benefits for backend-focused developers:**
- ✅ Write OpenAPI decorators once in NestJS
- ✅ Orval generates all TypeScript client code
- ✅ No manual API integration
- ✅ Frontend stays in sync with backend automatically
- ✅ Component library handles UI, you focus on backend logic

**Alternative: FastAPI + Orval**
If you prefer Python over NestJS, FastAPI works the same way:
```python
@app.get("/users/{id}", response_model=UserSchema)
async def get_user(id: str) -> UserSchema:
    return await user_service.find_one(id)
```
FastAPI auto-generates OpenAPI → Orval generates TypeScript client → Same workflow

### Recommended Architecture

#### 1. **Django REST Framework** - The Admin/Business Logic Layer
**Purpose:** Your "source of truth" for data, auth, and admin operations.

**What lives here:**
- User authentication and authorization
- Admin panels for internal operations
- Complex business logic with database relationships
- Scheduled jobs (Celery)
- Data migrations and schema management

**Why Django:**
- Excellent admin interface for ops teams
- Django ORM handles complex relationships elegantly
- Massive ecosystem for common patterns
- Python integrates with ML/data science tools

**Example services:**
- `user-service` (auth, profiles, permissions)
- `admin-service` (internal dashboards, reports)
- `billing-service` (complex accounting logic)

---

#### 2. **Node.js (NestJS/Fastify)** - Full-Stack TypeScript Layer
**Purpose:** Unified language across frontend and backend, I/O-bound services.

**What lives here:**
- BFF (Backend-for-Frontend) APIs tailored to specific frontends
- Services that aggregate data from multiple backends
- Real-time features (Socket.IO)
- Services that share TypeScript types with the frontend

**Why Node.js:**
- **One language:** Frontend devs can contribute to backend
- Share types, validation schemas, and business logic
- Excellent for I/O-bound operations (external APIs, databases)
- Socket.IO for real-time features is industry standard
- **Largest talent pool:** Any JavaScript developer can work on it

**Example services:**
- `bff-web` (Backend-for-Frontend for web app)
- `bff-mobile` (Backend-for-Frontend for mobile app)
- `notification-service` (real-time notifications via Socket.IO)
- `aggregation-service` (combines data from Django + Go services)

---

#### 3. **FastAPI** - High-Throughput Public APIs
**Purpose:** Customer-facing APIs that need performance but stay in Python.

**What lives here:**
- Public REST APIs with high request volume
- Services that need async I/O (external API calls)
- Microservices that don't need Django's full stack
- Lambda/serverless functions

**Why FastAPI:**
- 3x faster than Django for simple endpoints
- Stays in Python (share code/libraries with Django)
- Automatic OpenAPI docs
- Async-first for I/O-bound operations

**Example services:**
- `api-gateway` (public REST API)
- `notification-service` (async external API calls)
- `search-service` (ElasticSearch queries)

---

#### 4. **Go (Gin/Echo)** - Microservice Workhorses
**Purpose:** High-throughput, stateless services where performance matters.

**What lives here:**
- API endpoints handling 10k+ req/sec
- Services doing simple CRUD without complex logic
- Image/video processing pipelines
- Rate limiters, proxies, load balancers
- Services that need to scale to many instances

**Why Go:**
- 10-40x faster than Python
- 5-10MB memory footprint (cheap to run many instances)
- Single binary deployment
- Excellent gRPC performance

**Example services:**
- `media-service` (image resizing, video transcoding)
- `analytics-service` (high-volume event ingestion)
- `rate-limiter` (protecting other services)

---

#### 5. **Rust (Loco/Actix/Axum)** - Performance-Critical & Safety-Critical
**Purpose:** Only when Go isn't fast enough or memory safety is required.

**What lives here:**
- Payment processing (safety-critical)
- Real-time bidding systems
- Cryptography services
- Services handling 100k+ concurrent WebSocket connections
- Embedded systems or edge computing

**Why Rust:**
- 2-4x faster than Go
- Memory safety prevents entire classes of bugs
- No garbage collection (predictable latency)

**Example services:**
- `payment-gateway` (PCI compliance, memory safety)
- `websocket-server` (100k+ concurrent connections)
- `crypto-service` (sensitive cryptographic operations)

---

### Service Communication

```
External Clients (Browser/Mobile)
         │
         ▼ REST/JSON (FastAPI)
    API Gateway
         │
         ├─→ Django (for auth, admin, complex logic)
         │
         ├─→ FastAPI (for high-throughput public APIs)
         │
         └─→ Go/Rust (via gRPC for internal service mesh)
                 │
                 └─→ Fast inter-service communication
```

**Inter-Service Communication:**
- **REST/JSON:** External clients → API Gateway
- **gRPC:** Internal services talking to each other (Go ↔ Rust ↔ Python)
- **Message Queue (RabbitMQ/Kafka):** Async background jobs

---

### Decision Matrix for Polyglots

| Scenario | Choose | Why |
|----------|--------|-----|
| Admin panels, auth, complex ORM queries | **Django** | Built-in admin, mature ORM, Python ecosystem |
| Full-stack TypeScript, BFF pattern | **Node.js (NestJS)** | Share types with frontend, largest talent pool |
| Public API with 1000+ req/sec | **FastAPI or Node.js** | Performance + familiarity (Python or JS) |
| Internal microservice with 10k+ req/sec | **Go** | Maximum throughput, minimal resources |
| Payment processing, real-time trading | **Rust** | Memory safety, no GC, ultra-performance |
| Real-time chat/notifications | **Node.js (Socket.IO)** | Industry standard, easy to implement |
| Background jobs, async processing | **RabbitMQ/Celery/Bull** | Depends on primary language (Python/Node/Ruby) |
| Machine learning inference | **Python (FastAPI)** | Easy integration with TensorFlow/PyTorch |

---

### Polyglot Best Practices

#### DO:
✅ **Start with one language** (Django or Rails) and add others as needed  
✅ **Use gRPC** for internal service communication (language-agnostic)  
✅ **Share code via Protocol Buffers** (contracts between services)  
✅ **Use containerization** (Docker/Kubernetes) - each service is independent  
✅ **Centralize auth** (Django handles auth, other services verify tokens)  

#### DON'T:
❌ **Use 4 languages from day one** - start simple, add complexity as needed  
❌ **Share databases between services** - each service owns its data  
❌ **Mix languages within a service** - one service = one language  
❌ **Use REST for internal service communication** - gRPC is faster and type-safe  
❌ **Rewrite everything in Rust** - most services don't need it  

---

### Real-World Polyglot Example

**Shopify's Stack (simplified):**
- **Ruby on Rails:** Admin, business logic, core platform
- **Go:** High-throughput APIs, rate limiting
- **Rust:** Payment processing, security-critical paths

**Netflix's Stack (simplified):**
- **Java/Spring:** Core business logic (their "Django")
- **Node.js:** Fast I/O-bound APIs
- **Python:** Data science, ML pipelines
- **Go:** Performance-critical microservices

**Your Stack (recommended starting point):**
1. **Start:** Django for everything
2. **Add Node.js (NestJS):** If your frontend is React/Vue and team knows TypeScript
3. **Add FastAPI:** When specific Python endpoints need 3x performance
4. **Add Go:** When you need 10x performance and multiple instances
5. **Consider Rust:** Only when Go isn't fast enough (rare)

**Talent Pool Reality:**
- **Easiest to hire:** JavaScript/TypeScript (Node.js) - frontend devs can contribute
- **Large pool:** Python, Java - widely taught, mature ecosystem
- **Medium pool:** Go - growing fast, especially in cloud-native companies
- **Small pool:** Rust, Ruby - niche expertise, higher salaries
- **Choose wisely:** Hiring/training costs often exceed infrastructure costs

---

### Migration Path

```
Phase 1: Monolith (Django or Rails)
    └─→ Everything in one app
        ✓ Fast development
        ✓ Easy to reason about
        ✗ Performance ceiling

Phase 2: Add Node.js or FastAPI
    └─→ Django (admin, auth) + Node.js (BFF/public API)
        ✓ Full-stack TypeScript if frontend is React/Vue
        ✓ OR FastAPI if staying in Python
        ✓ 2-3x better performance

Phase 3: Extract Go microservices
    └─→ Django + Node.js/FastAPI + Go (high-volume services)
        ✓ 10x performance for specific services
        ✗ More operational complexity

Phase 4: Add Rust (only if needed)
    └─→ Django + Node.js + Go + Rust (critical paths)
        ✓ Maximum performance where needed
        ✗ Requires Rust expertise
```

**The truth:** Most companies stop at Phase 2. Only scale to Phase 3/4 when you have specific performance problems, not because it sounds cool.

---

## Next Steps: Advanced Patterns

Once you've chosen your stack and built your initial services, consider these advanced architectural patterns:

📖 **See [002-advanced-architectural-patterns.md](./002-advanced-architectural-patterns.md)** for:

- **CQRS & Event Sourcing** - When you need audit trails and write/read optimization
- **Database Sharding** - When a single Postgres instance can't handle your scale
- **Observability with OpenTelemetry** - Logging, metrics, and distributed tracing for production systems
- **Advanced API Security (JWKS)** - Token validation and key rotation in distributed systems

⚠️ **Warning:** These are advanced patterns for scale problems. Don't implement them until you have proof you need them.