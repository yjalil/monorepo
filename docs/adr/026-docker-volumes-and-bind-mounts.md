# ADR-026: Docker Volumes and Bind Mounts Strategy

## Status
Proposed

## Context
Docker provides three storage mechanisms for persisting data beyond container lifecycle: volumes, bind mounts, and tmpfs mounts. Each has distinct characteristics affecting performance, portability, security, and developer experience. Without clear guidelines, teams make inconsistent choices leading to:

- Data loss when containers are recreated
- Performance degradation from wrong storage types
- Security issues from excessive host filesystem access
- Portability problems when host paths are hardcoded
- Developer friction when files aren't accessible where needed
- Backup/restore complexity from scattered data locations

The choice between volumes and bind mounts depends on:
- **Data lifecycle** - ephemeral vs persistent
- **Access patterns** - container-only vs host tooling needs
- **Performance requirements** - random I/O vs sequential, SSD vs HDD
- **Security boundaries** - isolation vs accessibility
- **Portability needs** - works on any host vs specific filesystem layout
- **Development vs production** - different priorities in each environment

## Decision

**Use Docker volumes as the default. Use bind mounts only when host filesystem access is required. Choose storage type based on data characteristics, access patterns, and environment.**

## Storage Types Comparison

| Characteristic | Docker Volume | Bind Mount | tmpfs Mount |
|---------------|---------------|------------|-------------|
| **Managed by** | Docker | Host filesystem | Memory (RAM) |
| **Location** | `/var/lib/docker/volumes/` | Anywhere on host | Container memory |
| **Portability** | High (works anywhere) | Low (host-specific paths) | High (no persistence) |
| **Performance** | Good | Excellent (native FS) | Fastest (RAM) |
| **Host access** | Difficult (`docker volume inspect`) | Easy (normal file access) | None (ephemeral) |
| **Permissions** | Docker manages | Host UID/GID issues | No issues |
| **Backup** | `docker run --volumes-from` | Standard file backup | Cannot backup |
| **Persistence** | Survives container removal | Survives everything | Lost on container stop |
| **Security** | Isolated from host | Host filesystem exposure | Isolated |
| **Best for** | Databases, production data | Source code, dev configs | Secrets, temp files |

## Decision Framework

### Use Docker Volumes When:

✅ **Production databases and persistent storage**
```yaml
services:
  postgres:
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
    driver: local
```

✅ **Container-managed data that doesn't need host access**
```yaml
services:
  elasticsearch:
    volumes:
      - es-data:/usr/share/elasticsearch/data
```

✅ **Data that needs to be portable across hosts**
```yaml
# Works identically on any Docker host
volumes:
  app-data:
```

✅ **Multi-container data sharing via volumes-from**
```yaml
services:
  app:
    volumes:
      - shared-data:/data
  backup:
    volumes:
      - shared-data:/data:ro
```

**Syntax:**
```yaml
# Named volume (recommended)
services:
  service:
    volumes:
      - volume-name:/container/path

volumes:
  volume-name:
    name: explicit-name  # Optional: control actual volume name
    driver: local        # Optional: default
    driver_opts:         # Optional: driver-specific options
      type: none
      o: bind
      device: /path/to/data

# Anonymous volume (avoid - hard to manage)
services:
  service:
    volumes:
      - /container/path  # Docker generates random name
```

### Use Bind Mounts When:

✅ **Source code during development**
```yaml
services:
  app:
    volumes:
      - ./src:/app/src  # Hot reload on code changes
```

✅ **Configuration files that need host editing**
```yaml
services:
  nginx:
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
```

✅ **Build artifacts that need host inspection**
```yaml
services:
  builder:
    volumes:
      - ./dist:/app/dist  # Compiled assets available on host
```

✅ **Host tools need to process container output**
```yaml
services:
  app:
    volumes:
      - ./logs:/var/log/app  # Analyze logs with host tools
```

✅ **Shared caches between host and container**
```yaml
services:
  node-app:
    volumes:
      - ~/.npm:/home/node/.npm  # Share npm cache
```

**Syntax:**
```yaml
# Short syntax (relative or absolute)
services:
  service:
    volumes:
      - ./relative/path:/container/path
      - /absolute/host/path:/container/path
      - ~/user/home/path:/container/path

# Long syntax (more control)
services:
  service:
    volumes:
      - type: bind
        source: ./host/path      # Relative to compose file
        target: /container/path
        read_only: true          # Optional: prevent writes
        bind:
          propagation: rprivate  # Optional: mount propagation
          create_host_path: true # Optional: create if missing
```

### Use tmpfs Mounts When:

✅ **Sensitive data that must not persist**
```yaml
services:
  app:
    tmpfs:
      - /run/secrets  # Credentials in memory only
```

✅ **High-performance temporary storage**
```yaml
services:
  build:
    tmpfs:
      - /tmp
      - /var/tmp
```

✅ **Scratch space for computations**
```yaml
services:
  processor:
    tmpfs:
      - /workspace/temp:size=2G  # 2GB RAM disk
```

**Syntax:**
```yaml
# Short syntax
services:
  service:
    tmpfs:
      - /container/path

# Long syntax
services:
  service:
    tmpfs:
      - type: tmpfs
        target: /container/path
        tmpfs:
          size: 1073741824  # 1GB in bytes
          mode: 1777        # Permissions
```

## Patterns by Use Case

### Pattern 1: Production Database (Volume)
```yaml
services:
  postgres:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt

volumes:
  postgres-data:
    name: production-postgres
    driver: local
```

**Rationale:**
- Production data must persist across container updates
- Docker volume provides isolation and portability
- Secret in tmpfs (via secrets:) never hits disk
- Can backup with `docker run --volumes-from`

### Pattern 2: Development with Hot Reload (Bind Mount)
```yaml
services:
  web-app:
    build: .
    volumes:
      - ./src:/app/src:cached      # Source code
      - ./tests:/app/tests:cached  # Tests
      - /app/node_modules          # Anonymous volume for dependencies
    environment:
      NODE_ENV: development
```

**Rationale:**
- Code changes on host immediately visible in container
- `cached` flag improves performance on macOS/Windows
- `node_modules` as anonymous volume avoids host/container conflicts
- Works with file watchers for hot reload

### Pattern 3: CI/CD Build Artifacts (Bind Mount)
```yaml
services:
  builder:
    image: node:20
    volumes:
      - ./src:/app/src:ro          # Source read-only
      - ./dist:/app/dist           # Build output writable
      - build-cache:/root/.cache   # Named volume for caching
    command: npm run build

volumes:
  build-cache:
```

**Rationale:**
- Source code read-only prevents accidental modification
- Build artifacts written to host for deployment
- Cache in volume for faster rebuilds (survives container removal)

### Pattern 4: Shared Configuration (Bind Mount, Read-Only)
```yaml
services:
  app-1:
    volumes:
      - ./config/app.yml:/etc/app/config.yml:ro
  app-2:
    volumes:
      - ./config/app.yml:/etc/app/config.yml:ro
  app-3:
    volumes:
      - ./config/app.yml:/etc/app/config.yml:ro
```

**Rationale:**
- Single source of truth on host
- Read-only prevents container from modifying config
- Easy to edit with host editor, changes apply on restart

### Pattern 5: Log Aggregation (Bind Mount)
```yaml
services:
  app:
    volumes:
      - ./logs/app:/var/log/app
  
  nginx:
    volumes:
      - ./logs/nginx:/var/log/nginx
  
  log-processor:
    volumes:
      - ./logs:/logs:ro  # Read all logs
    command: tail -f /logs/**/*.log
```

**Rationale:**
- All logs in one host directory for analysis
- Log processor reads from host filesystem
- Can use host tools (grep, awk) on logs
- Persistent across container recreation

### Pattern 6: Secrets Management (tmpfs)
```yaml
services:
  app:
    volumes:
      - type: tmpfs
        target: /run/secrets
        tmpfs:
          size: 10485760  # 10MB
          mode: 0700
    environment:
      SECRET_PATH: /run/secrets
    entrypoint: |
      sh -c '
        echo "Loading secrets to tmpfs..."
        echo "$DB_PASSWORD" > /run/secrets/db_password
        chmod 400 /run/secrets/db_password
        exec /app/start.sh
      '
```

**Rationale:**
- Secrets never written to disk
- Memory-only storage auto-cleared on container stop
- Restrictive permissions prevent other processes from reading

### Pattern 7: Multi-Stage Build Cache (Volume)
```dockerfile
# Dockerfile
FROM node:20 AS builder
RUN --mount=type=cache,target=/root/.npm \
    npm install
```

```yaml
# docker-compose.yml
services:
  builder:
    build:
      context: .
      cache_from:
        - myapp:builder
```

**Rationale:**
- BuildKit cache mount (not compose volume)
- Cache persists across builds
- Dramatically faster npm install
- No explicit volume declaration needed

### Pattern 8: Database Backup Container (Volume Sharing)
```yaml
services:
  postgres:
    volumes:
      - postgres-data:/var/lib/postgresql/data
  
  backup:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data:ro
      - ./backups:/backups
    command: pg_dump -U postgres -d mydb -f /backups/backup-$(date +%Y%m%d).sql
    depends_on:
      - postgres

volumes:
  postgres-data:
```

**Rationale:**
- Backup container shares same volume read-only
- Dumps written to host via bind mount
- Volume ensures database data accessible to backup
- Host bind mount makes backups accessible for archival

### Pattern 9: Devcontainer Development (Hybrid)
```jsonc
// .devcontainer/devcontainer.json
{
  "name": "Monorepo Dev",
  "dockerComposeFile": "docker-compose.yml",
  "service": "devcontainer",
  "workspaceFolder": "/workspace",
  
  "mounts": [
    // Source code bind mount
    "source=${localWorkspaceFolder},target=/workspace,type=bind",
    
    // Cache bind mounts (performance)
    "type=bind,source=${localWorkspaceFolder}/../.cache/uv,target=/home/vscode/.cache/uv",
    "type=bind,source=${localWorkspaceFolder}/../.cache/mise,target=/home/vscode/.local/share/mise",
    
    // Service data that needs VSCode access
    "type=bind,source=/mnt/ssd/minio-data,target=/workspace/data/minio",
    
    // SSH keys (read-only)
    "type=bind,source=${localWorkspaceFolder}/../.keys/.ssh,target=/home/vscode/.ssh,readonly"
  ]
}
```

```yaml
# docker-compose.yml (sibling services)
services:
  devcontainer:
    build: .devcontainer
    volumes:
      - ..:/workspace
    networks: [dev-net]
  
  postgres:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data  # Named volume (ephemeral)
    networks: [dev-net]
  
  minio:
    image: minio/minio
    volumes:
      - /mnt/ssd/minio-data:/data  # Bind mount (needs VSCode access)
    networks: [dev-net]

volumes:
  postgres-data:

networks:
  dev-net:
```

**Rationale:**
- Source code bind mounted for hot reload
- Caches on SSD for performance, persist across container rebuilds
- Postgres uses named volume (test data, frequently reset)
- MinIO uses bind mount so files visible in VSCode
- SSH keys read-only for security

### Pattern 10: Testing with Clean State (Anonymous Volume)
```yaml
services:
  test-runner:
    image: node:20
    volumes:
      - ./tests:/app/tests:ro
      - /app/node_modules      # Fresh dependencies each run
      - /tmp                   # Temporary test artifacts
    command: npm test
```

**Rationale:**
- Tests read-only, can't modify source
- Fresh `node_modules` each run ensures no cross-test pollution
- `/tmp` gets fresh tmpfs each run
- Clean state prevents flaky tests

### Pattern 11: Backup to External Storage (Bind Mount)
```yaml
services:
  backup:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data:ro
      - /mnt/nas/backups:/backups  # Network-attached storage
    environment:
      BACKUP_RETENTION_DAYS: 30
    command: |
      sh -c '
        pg_dump -U postgres mydb > /backups/backup-$(date +%Y%m%d).sql
        find /backups -name "*.sql" -mtime +30 -delete
      '

volumes:
  postgres-data:
```

**Rationale:**
- Backup written to NAS via bind mount
- Volume provides database access
- Automated retention cleanup in same script
- NAS mount survives host restart

### Pattern 12: Development with Volume Drivers (Cloud Storage)
```yaml
services:
  app:
    volumes:
      - s3-data:/app/data

volumes:
  s3-data:
    driver: rexray/s3fs
    driver_opts:
      accessKey: ${AWS_ACCESS_KEY}
      secretKey: ${AWS_SECRET_KEY}
      bucket: my-app-data
```

**Rationale:**
- Cloud-native storage integration
- No host filesystem dependency
- Scales beyond single host
- Data persists independently of infrastructure

### Pattern 13: Performance-Critical Workload (tmpfs)
```yaml
services:
  video-processor:
    image: ffmpeg:latest
    volumes:
      - ./input:/input:ro
      - ./output:/output
    tmpfs:
      - /tmp:size=10G,mode=1777
    command: |
      sh -c '
        cp /input/video.mp4 /tmp/
        ffmpeg -i /tmp/video.mp4 -c:v libx264 /tmp/output.mp4
        cp /tmp/output.mp4 /output/
      '
```

**Rationale:**
- Input/output via bind mounts (host access)
- Processing in RAM (tmpfs) for maximum speed
- Avoid disk I/O during intensive operations
- Temporary files automatically cleaned up

## Performance Considerations

### Volume Performance by Type

| Operation | Docker Volume | Bind Mount (Linux) | Bind Mount (Mac/Win) | tmpfs |
|-----------|---------------|-------------------|---------------------|-------|
| **Sequential Read** | Excellent | Excellent | Good | Excellent |
| **Sequential Write** | Excellent | Excellent | Good | Excellent |
| **Random Read** | Excellent | Excellent | Poor | Excellent |
| **Random Write** | Excellent | Excellent | Poor | Excellent |
| **Many Small Files** | Good | Good | Very Poor | Excellent |
| **Latency** | Low | Low | High | Lowest |

### Platform-Specific Performance

**Linux:**
- Bind mounts have native filesystem performance
- Volumes slightly slower due to Docker abstraction layer
- Choose based on access needs, not performance

**macOS/Windows:**
- Bind mounts use virtualization layer (slow)
- Use `cached` or `delegated` flags to improve:
  ```yaml
  volumes:
    - ./src:/app/src:cached    # Host -> Container (dev)
    - ./dist:/app/dist:delegated  # Container -> Host (builds)
  ```
- Named volumes stored in Linux VM (fast)
- **Recommendation:** Use volumes for node_modules, Python .venv

### Optimization Patterns

**Node.js Development (Mac/Windows):**
```yaml
services:
  node-app:
    volumes:
      - ./src:/app/src:cached           # Bind mount for hot reload
      - node_modules:/app/node_modules  # Volume for dependencies
```

**Python Development (Mac/Windows):**
```yaml
services:
  python-app:
    volumes:
      - ./src:/app/src:cached     # Bind mount for code
      - venv:/app/.venv           # Volume for virtualenv
```

**Build Performance:**
```yaml
services:
  builder:
    volumes:
      - ./src:/app/src:ro
      - ./dist:/app/dist:delegated  # Fast Container→Host writes
      - build-cache:/root/.cache    # Cache persists
```

## Security Considerations

### Bind Mount Security Risks

**Risk: Host Filesystem Exposure**
```yaml
# ❌ DANGEROUS: Container can modify entire host
volumes:
  - /:/host

# ✅ SAFE: Limit to specific directories
volumes:
  - ./app-data:/data
```

**Risk: Privilege Escalation**
```yaml
# ❌ DANGEROUS: Container can modify binaries
volumes:
  - /usr/bin:/host-bin

# ✅ SAFE: Use read-only
volumes:
  - /usr/bin:/host-bin:ro
```

**Risk: Sensitive File Exposure**
```yaml
# ❌ DANGEROUS: SSH keys, AWS credentials exposed
volumes:
  - ~/:/home/user

# ✅ SAFE: Mount only what's needed, read-only when possible
volumes:
  - ~/.ssh:/home/user/.ssh:ro
  - ~/.aws:/home/user/.aws:ro
```

### Volume Security Best Practices

```yaml
services:
  app:
    volumes:
      # Application data with restrictive permissions
      - type: volume
        source: app-data
        target: /app/data
        volume:
          nocopy: true  # Don't copy initial data
      
      # Config read-only
      - type: bind
        source: ./config.yml
        target: /app/config.yml
        read_only: true
      
      # Secrets in tmpfs (never persisted)
      - type: tmpfs
        target: /run/secrets
        tmpfs:
          size: 10485760
          mode: 0700

volumes:
  app-data:
    driver: local
    driver_opts:
      type: none
      o: bind,uid=1000,gid=1000  # Specific user ownership
      device: /secure/data
```

### User ID Mapping

**Problem: File Ownership Conflicts**
```bash
# Container writes as root (UID 0)
# Host user can't read/modify files
```

**Solution: Match Container UID to Host UID**
```dockerfile
# Dockerfile
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd -g $USER_GID appuser && \
    useradd -u $USER_UID -g $USER_GID appuser

USER appuser
```

```yaml
# docker-compose.yml
services:
  app:
    build:
      args:
        USER_UID: ${UID:-1000}
        USER_GID: ${GID:-1000}
    volumes:
      - ./data:/app/data
```

## Troubleshooting

### Issue: Files Not Appearing in Container

**Symptom:** Bind mount looks empty in container

**Causes:**
1. **Path mismatch** - Host path doesn't exist
2. **Relative path confusion** - Path relative to wrong location
3. **Mount order** - Volume mounted before directory created

**Solutions:**
```yaml
# Solution 1: Use absolute paths
volumes:
  - /home/user/project:/app  # Explicit

# Solution 2: Create host directory first
volumes:
  - type: bind
    source: ./data
    target: /app/data
    bind:
      create_host_path: true  # Create if missing

# Solution 3: Check mount order in Dockerfile
# WRONG:
RUN mkdir -p /app/data
VOLUME /app/data  # This shadows bind mount!

# RIGHT:
# Don't use VOLUME instruction with bind mounts
```

### Issue: Permission Denied

**Symptom:** Container can't write to bind mount

**Causes:**
1. Container user UID doesn't match host owner
2. Host directory has restrictive permissions
3. SELinux preventing access

**Solutions:**
```bash
# Solution 1: Match UIDs (see User ID Mapping above)

# Solution 2: Fix host permissions
chmod -R 777 ./data  # ❌ Too permissive
chmod -R 755 ./data  # ✅ Better
chown -R 1000:1000 ./data  # ✅ Best (match container UID)

# Solution 3: SELinux context
chcon -Rt svirt_sandbox_file_t ./data  # SELinux

# Solution 4: Docker Compose with SELinux
volumes:
  - ./data:/app/data:z  # Private label
  - ./shared:/app/shared:Z  # Shared label
```

### Issue: Poor Performance on Mac/Windows

**Symptom:** Slow file operations, high CPU usage

**Causes:**
1. File watching overhead (webpack, nodemon, etc.)
2. Many small files (node_modules)
3. Virtualization overhead

**Solutions:**
```yaml
# Solution 1: Use cached/delegated flags
volumes:
  - ./src:/app/src:cached

# Solution 2: Exclude problematic directories
volumes:
  - ./src:/app/src
  - /app/node_modules  # Anonymous volume (not bind mounted)

# Solution 3: Use volumes for dependencies
volumes:
  - ./src:/app/src
  - node_modules:/app/node_modules

# Solution 4: Reduce file watching scope
# package.json
{
  "scripts": {
    "dev": "nodemon --watch src --ignore node_modules"
  }
}
```

### Issue: Volume Data Lost

**Symptom:** Data disappears after `docker compose down`

**Causes:**
1. Using `-v` flag (removes volumes)
2. Anonymous volumes
3. Volume not declared in top-level `volumes:` section

**Solutions:**
```bash
# Wrong: Removes volumes
docker compose down -v

# Right: Keeps volumes
docker compose down

# List volumes
docker volume ls

# Inspect volume
docker volume inspect postgres-data

# Backup volume
docker run --rm \
  --volumes-from postgres \
  -v $(pwd)/backup:/backup \
  ubuntu tar cvf /backup/postgres.tar /var/lib/postgresql/data
```

### Issue: Stale Cache in Volume

**Symptom:** Changes not reflected, old dependencies used

**Solution:**
```bash
# Remove and recreate volume
docker compose down
docker volume rm myapp_build-cache
docker compose up --build

# Or force rebuild without cache
docker compose build --no-cache
docker compose up
```

## Anti-Patterns

### ❌ Anti-Pattern 1: Mount Everything
```yaml
# BAD: Entire filesystem exposed
volumes:
  - /:/host
  - /var/run/docker.sock:/var/run/docker.sock
```

**Why Bad:** Security risk, accidental modifications

**Better:**
```yaml
# GOOD: Only what's needed
volumes:
  - ./app:/app
  - ./config:/config:ro
```

### ❌ Anti-Pattern 2: Anonymous Volumes Everywhere
```yaml
# BAD: Hard to manage, identify
volumes:
  - /app/data
  - /app/logs
  - /app/cache
```

**Why Bad:** Random names, can't reference, accumulate over time

**Better:**
```yaml
# GOOD: Named volumes
volumes:
  - app-data:/app/data
  - app-logs:/app/logs
  - app-cache:/app/cache

volumes:
  app-data:
  app-logs:
  app-cache:
```

### ❌ Anti-Pattern 3: Hardcoded Host Paths
```yaml
# BAD: Won't work on other machines
volumes:
  - /home/john/project:/app
  - /Users/john/data:/data
```

**Why Bad:** Not portable, fails on different hosts

**Better:**
```yaml
# GOOD: Relative paths or environment variables
volumes:
  - ./project:/app
  - ${DATA_PATH:-./data}:/data
```

### ❌ Anti-Pattern 4: Mixing Concerns
```yaml
# BAD: Source and generated files in same mount
volumes:
  - .:/app  # Includes src/, dist/, node_modules/, .git/
```

**Why Bad:** Performance, security, pollution

**Better:**
```yaml
# GOOD: Separate mounts
volumes:
  - ./src:/app/src:cached
  - ./dist:/app/dist:delegated
  - node_modules:/app/node_modules
```

### ❌ Anti-Pattern 5: No Backup Strategy
```yaml
# BAD: Critical data in unnamed volume
services:
  db:
    volumes:
      - /var/lib/postgresql/data
```

**Why Bad:** Data loss on volume removal, no backup mechanism

**Better:**
```yaml
# GOOD: Named volume + backup service
services:
  db:
    volumes:
      - postgres-data:/var/lib/postgresql/data
  
  backup:
    volumes:
      - postgres-data:/data:ro
      - ./backups:/backups

volumes:
  postgres-data:
    name: production-postgres
```

### ❌ Anti-Pattern 6: Root User with Bind Mounts
```dockerfile
# BAD: Runs as root, writes files owned by root
FROM node:20
WORKDIR /app
COPY . .
# Files created by root (UID 0)
```

**Why Bad:** Host user can't modify container-created files

**Better:**
```dockerfile
# GOOD: Non-root user matching host UID
FROM node:20
ARG USER_UID=1000
RUN groupadd -g $USER_UID node && \
    useradd -u $USER_UID -g node node
USER node
WORKDIR /app
```

## Decision Tree

```
Need to store data outside container?
│
├─ Yes → What type of data?
│  │
│  ├─ Source code / configs that need editing?
│  │  └─ Use: Bind Mount
│  │     Example: ./src:/app/src
│  │
│  ├─ Build artifacts / outputs?
│  │  └─ Use: Bind Mount (delegated on Mac/Win)
│  │     Example: ./dist:/app/dist:delegated
│  │
│  ├─ Database / persistent application data?
│  │  ├─ Production environment?
│  │  │  └─ Use: Named Volume
│  │  │     Example: postgres-data:/var/lib/postgresql/data
│  │  │
│  │  └─ Development environment?
│  │     ├─ Need host tool access (backups, inspection)?
│  │     │  └─ Use: Bind Mount
│  │     │     Example: ./data/postgres:/var/lib/postgresql/data
│  │     │
│  │     └─ Container-only access?
│  │        └─ Use: Named Volume
│  │           Example: dev-postgres-data:/var/lib/postgresql/data
│  │
│  ├─ Caches / temporary build artifacts?
│  │  ├─ Need to persist across containers?
│  │  │  └─ Use: Named Volume
│  │  │     Example: build-cache:/root/.cache
│  │  │
│  │  └─ Can be ephemeral?
│  │     └─ Use: tmpfs Mount
│  │        Example: tmpfs: /tmp
│  │
│  ├─ Secrets / sensitive data?
│  │  └─ Use: tmpfs Mount
│  │     Example: tmpfs: /run/secrets
│  │
│  ├─ Shared between multiple containers?
│  │  ├─ Source code / configs?
│  │  │  └─ Use: Bind Mount (shared to all)
│  │  │
│  │  └─ Application data?
│  │     └─ Use: Named Volume (shared via volumes_from)
│  │
│  ├─ Logs that need host analysis?
│  │  └─ Use: Bind Mount
│  │     Example: ./logs:/var/log/app
│  │
│  └─ Dependencies (node_modules, .venv)?
│     ├─ Linux host?
│     │  └─ Either works, prefer bind for simplicity
│     │
│     └─ Mac/Windows host?
│        └─ Use: Named Volume (performance)
│           Example: node_modules:/app/node_modules
│
└─ No → Don't use volumes
   Example: Stateless service
```

## Environment-Specific Guidelines

### Development Environment

**Priorities:** Hot reload, ease of debugging, flexibility

```yaml
services:
  app:
    volumes:
      # Source code - bind mount for hot reload
      - ./src:/app/src:cached
      
      # Test data - named volume (frequently reset)
      - test-data:/app/data
      
      # Build cache - named volume (persist)
      - build-cache:/root/.cache
      
      # Logs - bind mount for host inspection
      - ./logs:/app/logs
      
      # Dependencies - named volume on Mac/Win
      - node_modules:/app/node_modules
```

### CI/CD Environment

**Priorities:** Speed, reproducibility, artifact capture

```yaml
services:
  builder:
    volumes:
      # Source - bind mount read-only
      - ./src:/app/src:ro
      
      # Build output - bind mount for artifact collection
      - ./dist:/app/dist
      
      # Cache - named volume for speed
      - ci-cache:/root/.cache
      
      # Temp - tmpfs for maximum speed
    tmpfs:
      - /tmp
```

### Production Environment

**Priorities:** Security, data persistence, isolation

```yaml
services:
  app:
    volumes:
      # Application data - named volume (isolated)
      - app-data:/app/data
      
      # Config - bind mount read-only
      - ./config.yml:/app/config.yml:ro
      
      # Secrets - tmpfs (never persisted)
    tmpfs:
      - /run/secrets
    
    # No source code mounts in production
```

### Testing Environment

**Priorities:** Clean state, speed, isolation

```yaml
services:
  test-runner:
    volumes:
      # Tests - bind mount read-only
      - ./tests:/app/tests:ro
      
      # Coverage output - bind mount
      - ./coverage:/app/coverage
      
      # Test data - anonymous volume (fresh each run)
      - /app/test-data
      
      # Temp - tmpfs
    tmpfs:
      - /tmp
```

## Consequences

### Positive
- **Clear decision framework** - Systematic approach to volume selection
- **Performance optimization** - Right storage type for each use case
- **Security boundaries** - Minimize host filesystem exposure
- **Data persistence** - Appropriate durability for each data type
- **Portability** - Named volumes work on any Docker host
- **Debugging capability** - Bind mounts enable host tool access when needed
- **Environment-specific patterns** - Different strategies for dev/CI/prod

### Negative
- **Complexity** - More decisions to make than "just use volumes"
- **Platform differences** - Mac/Windows require different patterns than Linux
- **Permission management** - UID/GID mapping needed for bind mounts
- **Path management** - Must track host paths for bind mounts
- **Learning curve** - Team needs to understand volume types and tradeoffs

### Mitigations
- **Decision tree** - Follow systematic selection process
- **Standard patterns** - Use documented patterns for common scenarios
- **UID mapping** - Standardize on matching container/host UIDs (1000:1000)
- **Environment variables** - Use `${DATA_PATH}` instead of hardcoded paths
- **Documentation** - Document volume strategy in project README
- **Validation scripts** - Check paths exist before starting services

## Verification Checklist

Before deploying a new service:

- [ ] Identified all data types (code, configs, databases, caches, logs, secrets)
- [ ] Selected appropriate volume type for each (volume, bind, tmpfs)
- [ ] For bind mounts: Documented host paths and created directories
- [ ] For named volumes: Added to `volumes:` section with explicit names
- [ ] Verified permissions (container user matches host user if needed)
- [ ] Added read-only flag where appropriate (`:ro`)
- [ ] Configured performance flags for Mac/Windows (`:cached`, `:delegated`)
- [ ] Planned backup strategy for persistent data
- [ ] Tested data persists across container recreation
- [ ] Documented volume strategy in service README

## Quick Reference

### When to Use What

| Use Case | Storage Type | Example |
|----------|--------------|---------|
| Production database | Named Volume | `postgres-data:/var/lib/postgresql/data` |
| Dev source code | Bind Mount | `./src:/app/src:cached` |
| Build artifacts | Bind Mount | `./dist:/app/dist:delegated` |
| CI cache | Named Volume | `ci-cache:/root/.cache` |
| Secrets | tmpfs | `tmpfs: /run/secrets` |
| Test data | Anonymous Volume | `- /app/test-data` |
| Logs (need analysis) | Bind Mount | `./logs:/var/log/app` |
| node_modules (Mac/Win) | Named Volume | `node_modules:/app/node_modules` |
| Shared config | Bind Mount (ro) | `./config.yml:/app/config.yml:ro` |
| Hot reload code | Bind Mount | `./src:/app/src:cached` |

### Common Commands

```bash
# List volumes
docker volume ls

# Inspect volume location and details
docker volume inspect volume-name

# Remove unused volumes
docker volume prune

# Remove specific volume
docker volume rm volume-name

# Backup volume to tarball
docker run --rm \
  --volumes-from container-name \
  -v $(pwd):/backup \
  ubuntu tar cvf /backup/backup.tar /data

# Restore volume from tarball
docker run --rm \
  -v volume-name:/data \
  -v $(pwd):/backup \
  ubuntu tar xvf /backup/backup.tar -C /

# Copy files from volume
docker run --rm \
  -v volume-name:/data \
  -v $(pwd):/backup \
  ubuntu cp -r /data/. /backup/

# View volume contents
docker run --rm \
  -v volume-name:/data \
  ubuntu ls -la /data
```

## References
- [Docker Storage Overview](https://docs.docker.com/storage/)
- [Docker Volumes Documentation](https://docs.docker.com/storage/volumes/)
- [Docker Bind Mounts Documentation](https://docs.docker.com/storage/bind-mounts/)
- [Docker tmpfs Mounts](https://docs.docker.com/storage/tmpfs/)
- [Compose Volume Specification](https://docs.docker.com/compose/compose-file/07-volumes/)
- [Performance Tuning (Mac)](https://docs.docker.com/desktop/mac/performance/)
- [VSCode devcontainer.json Reference](https://containers.dev/implementors/json_reference/)

## Related ADRs
- ADR-020: Django vs FastAPI (service isolation impacts volume strategy)
- ADR-021: API First with OpenAPI (devcontainer development workflow)
- Future: Infrastructure as Code (volume provisioning in production)
