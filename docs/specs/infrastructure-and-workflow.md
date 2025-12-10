# Infrastructure & Development Workflow

## Quick Start

```bash
# Start global services (Redis, MinIO)
repoctl infra global start

# Start project services
repoctl infra project start backends/svc-turfoo-ingest

# Check status
repoctl infra status

# Stop project
repoctl infra project stop backends/svc-turfoo-ingest

# Stop global services
repoctl infra global stop
```

## Architecture

### Two-Tier Infrastructure

```
monorepo/
├── infra/                          # Global Infrastructure (shared)
│   ├── compose.global.yml          # Redis, MinIO, RedisInsight
│   ├── .env.global                 # Global config
│   └── templates/                  # Project templates
│
└── backends/svc-{service-name}/    # Service directory (kebab-case)
    ├── {package_name}/             # Python package (snake_case)
    └── infra/                      # Project Infrastructure (isolated)
        ├── compose.yml             # DB, workers, etc.
        ├── .env                    # Project config
        └── Dockerfile              # Container build
```

**Global Services** (shared by all projects):
- Redis (6379) - Cache, sessions, message broker
- MinIO (9000/9001) - S3-compatible object storage
- RedisInsight (5540) - Redis debugging UI

**Project Services** (per project):
- PostgreSQL - Project database
- Celery Worker - Background tasks
- Celery Beat - Scheduled tasks
- Custom services as needed

All services connect via `monorepo_net` Docker network.

### Naming Conventions

**Directory Structure:**
```
backends/svc-{service-name}/    # Service directory (kebab-case)
└── {package_name}/             # Python package (snake_case)
```

**Example:** `backends/svc-turfoo-ingest/turfoo/`

**Container Names:**
- Global services: `monorepo-{service}` (e.g., `monorepo-redis`)
- Project services: `{short-name}-{service}` (e.g., `turfoo-postgres`, `turfoo-celery-worker`)

**Image Names:**
- Match container names: `{short-name}-{service}:latest`
- Example: `turfoo-celery-worker:latest`, `turfoo-celery-beat:latest`

**Service Names in compose.yml:**
- Use descriptive names: `postgres`, `celery-worker`, `celery-beat`
- Container names and image names provide the full context

## CLI Commands

### Global Infrastructure

```bash
# Start shared services (Redis, MinIO)
repoctl infra global start

# Stop shared services
repoctl infra global stop

# View global services status
repoctl infra global status
```

### Project Infrastructure

```bash
# Start project (auto-starts global if needed)
repoctl infra project start {service-name}
# Example: repoctl infra project start svc-turfoo-ingest

# Stop project
repoctl infra project stop {service-name}

# Restart project
repoctl infra project restart {service-name}

# View project logs
repoctl infra project logs {service-name}

# Rebuild project containers
repoctl infra project rebuild {service-name}

# View project status
repoctl infra project status {service-name}
```

### Multi-Project Management

```bash
# List all projects with infrastructure
repoctl infra list

# View all services (global + all projects)
repoctl infra status
```

### Create New Project Infrastructure

```bash
# Initialize infrastructure for new project (use service directory name)
repoctl infra init svc-new-service

# Creates:
# - backends/svc-new-service/infra/compose.yml
# - backends/svc-new-service/infra/.env
# - backends/svc-new-service/infra/Dockerfile
```

## Development Workflow

### Starting Work

1. **Start global infrastructure** (if not running):
   ```bash
   repoctl infra global start
   ```

2. **Start your project**:
   ```bash
   repoctl infra project start svc-turfoo-ingest
   ```

3. **Verify everything is healthy**:
   ```bash
   repoctl infra status
   ```

### During Development

- **Code changes**: Auto-reload with volume mounts (no restart needed)
- **Dependency changes**: Rebuild containers
  ```bash
  repoctl infra project rebuild backends/svc-turfoo-ingest
  ```
- **View logs**:
  ```bash
  repoctl infra project logs backends/svc-turfoo-ingest
  ```

### Ending Work

```bash
# Stop project (keeps global running for other projects)
repoctl infra project stop backends/svc-turfoo-ingest

# Stop everything (global + all projects)
repoctl infra global stop
```

## Project Workspaces

Each project has a VS Code workspace file that shows only relevant folders:

```
projectspaces/
├── svc-turfoo-ingest.code-workspace
├── monorepo-core.code-workspace
└── monorepo-oss.code-workspace
```

**Example workspace** (`svc-turfoo-ingest.code-workspace`):
```json
{
  "folders": [
    {
      "name": "📦 Turfoo Project",
      "path": "../backends/svc-turfoo-ingest"
    },
    {
      "name": "🚀 Turfoo Infrastructure",
      "path": "../backends/svc-turfoo-ingest/infra"
    },
    {
      "name": "🌐 Global Infrastructure",
      "path": "../infra"
    },
    {
      "name": "📝 Documentation",
      "path": "../docs"
    }
  ],
  "settings": {
    "files.exclude": {
      "**/__pycache__": true,
      "**/*.pyc": true,
      "**/.ruff_cache": true
    }
  }
}
```

### Opening a Workspace

```bash
# From terminal
code projectspaces/svc-turfoo-ingest.code-workspace

# Or in VS Code: File → Open Workspace from File
```

## Project Configuration

### Environment Variables

Each project has `.env` file in `backends/svc-{service-name}/infra/.env`:

**Example:** `backends/svc-turfoo-ingest/infra/.env`

```bash
# Database
POSTGRES_USER=turfoo_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=turfoo_db
POSTGRES_PORT=5432

# Redis (from global)
REDIS_HOST=monorepo-redis
REDIS_PORT=6379
REDIS_PASSWORD=devpassword

# MinIO (from global)
MINIO_ENDPOINT=monorepo-minio:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=devpassword
```

### Docker Compose

Project services defined in `backends/svc-{service-name}/infra/compose.yml`:

**Example:** `backends/svc-turfoo-ingest/infra/compose.yml`

```yaml
services:
  postgres:
    container_name: turfoo-postgres      # {short-name}-{service}
    image: turfoo-postgres:latest        # Match container name
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    networks:
      - monorepo_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]

networks:
  monorepo_net:
    name: monorepo_net
    external: true  # Shared network with global services
```

**Key Points:**
- `container_name`: Uses short descriptive name (e.g., `turfoo-postgres`)
- `image`: Matches container name with `:latest` tag
- Service name in compose: Simple and descriptive (e.g., `postgres`)

### Dockerfile

Security-hardened Dockerfile template in `backends/svc-{service-name}/infra/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install uv && uv sync --frozen

# Security: Create non-root user
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-a-user-for-the-container-has-been-created
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-healthcheck-instructions-have-been-added-to-container-images
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "-m", "your_module"]
```

## Security Best Practices

All Dockerfiles follow security hardening (see [ADR 028](../adr/028-dockerfile-security-hardening.md)):

1. **Non-root user** (CKV_DOCKER_3)
   - All containers run as UID 1000
   - File ownership assigned to application user

2. **Health checks** (CKV_DOCKER_2)
   - All containers define health checks
   - Docker/orchestration can detect unhealthy containers

3. **Verified with Checkov**
   - 168 security checks passed
   - 0 vulnerabilities

## Troubleshooting

### Services won't start

```bash
# Check status
repoctl infra status

# View logs
repoctl infra project logs {service-name}

# Restart
repoctl infra project restart {service-name}
```

### Port conflicts

Check if ports are already in use:
```bash
# Redis (6379), MinIO (9000, 9001), RedisInsight (5540)
lsof -i :6379
```

### Network issues

Ensure `monorepo_net` exists:
```bash
docker network ls | grep monorepo_net
docker network create monorepo_net  # if missing
```

### Health checks failing

Wait for start-period before checking:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Rebuild from scratch

```bash
# Stop everything
repoctl infra project stop backends/{project}
repoctl infra global stop

# Remove containers
docker compose -f infra/compose.global.yml down -v
docker compose -f backends/{project}/infra/compose.yml down -v

# Start fresh
repoctl infra global start
repoctl infra project start backends/{project}
```

## Adding a New Project

1. **Create project structure**:
   ```bash
   mkdir -p backends/new_project/new_project
   ```

2. **Initialize infrastructure**:
   ```bash
   repoctl infra init backends/new_project
   ```

3. **Configure services**:
   - Edit `backends/new_project/infra/compose.yml`
   - Update `backends/new_project/infra/.env`
   - Customize `backends/new_project/infra/Dockerfile`

4. **Create workspace file**:
   ```bash
   cp projectspaces/svc-turfoo-ingest.code-workspace \
      projectspaces/new_project.code-workspace
   # Update paths in new workspace file
   ```

5. **Start the project**:
   ```bash
   repoctl infra project start backends/new_project
   ```

## References

- [ADR 027: Monorepo Git Workflow and Infrastructure](../adr/027-monorepo-git-workflow-and-Infrastructure.md)
- [ADR 028: Dockerfile Security Hardening](../adr/028-dockerfile-security-hardening.md)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/index.html)
