# Infrastructure Scalability Architecture

## Overview

Our two-tier architecture is designed for horizontal scalability while maintaining simplicity for development.

## Centralized Services (Singleton)

These services remain **single instances** shared across all projects:

### 1. Redis (`monorepo-redis`)
**Purpose:** Cache, sessions, message broker  
**Why Centralized:**
- Shared cache reduces memory usage
- Central session store for auth
- Single message broker for all Celery workers
- Simplified connection management

**Resource Limits:**
```yaml
limits:
  cpus: '0.25'
  memory: 512M
```

**Scaling Strategy:**
- ✅ Single instance for dev/staging
- ⚠️ For production: Redis Cluster or managed Redis (AWS ElastiCache, Redis Cloud)
- Can add read replicas if needed
- Use Redis Sentinel for high availability

**When to Scale:**
- Memory usage consistently > 400MB
- CPU > 80%
- High eviction rates
- Network I/O bottlenecks

### 2. MinIO (`monorepo-minio`)
**Purpose:** S3-compatible object storage  
**Why Centralized:**
- Shared file storage for all services
- Consistent bucket management
- Unified access control
- Cost-efficient storage

**Scaling Strategy:**
- ✅ Single instance for dev/staging (sufficient for most use cases)
- ⚠️ For production: 
  - MinIO distributed mode (4+ nodes)
  - AWS S3, Google Cloud Storage, or Azure Blob
  - Can add caching layer (CDN)

**When to Scale:**
- Storage > 80% capacity
- High concurrent upload/download operations
- Geographic distribution needed
- Compliance requirements (regional storage)

### 3. RedisInsight (`monorepo-redisinsight`)
**Purpose:** Redis debugging and monitoring UI  
**Why Centralized:**
- Development tool only
- Not needed in production
- Minimal resource usage

**Scaling Strategy:**
- ✅ Dev only - disable in staging/production
- Replace with proper monitoring (Prometheus, Grafana)

## Distributed Services (Per-Project)

These services are **isolated per project** and can scale independently:

### 1. PostgreSQL (`{project}-postgres`)
**Purpose:** Project-specific database  
**Why Isolated:**
- Data isolation and security
- Independent schema evolution
- Service-specific backup strategies
- Failure isolation

**Scaling Strategy:**
- ✅ One instance per service (dev/staging)
- 🔄 **Horizontal Scaling:**
  - Read replicas for read-heavy workloads
  - Connection pooling (PgBouncer)
  - Partitioning/sharding for large datasets
- ⬆️ **Vertical Scaling:**
  - Increase CPU/memory for single instance
  - Better for write-heavy workloads

**When to Scale:**
- Connection pool exhaustion
- Query latency > acceptable SLA
- CPU > 70% sustained
- Disk I/O bottlenecks

**Current Config:**
```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 1G
    reservations:
      cpus: '0.25'
      memory: 512M
```

### 2. Celery Workers (`{project}-celery-worker`)
**Purpose:** Background task processing  
**Why Distributed:**
- Task isolation between services
- Independent scaling per workload
- Failure doesn't affect other services

**Scaling Strategy:**
- ✅ **Horizontal Scaling (Recommended):**
  ```yaml
  celery-worker:
    deploy:
      replicas: 3  # Scale to 3 workers
  ```
- Multiple workers process tasks in parallel
- Scale based on queue depth
- Auto-scaling with orchestrators (K8s HPA)

**When to Scale:**
- Queue lag > acceptable threshold
- Task processing time increasing
- CPU utilization low but queue backing up (add workers)
- Tasks are I/O bound (more workers help)

**Scaling Example:**
```yaml
# In compose.yml
celery-worker:
  container_name: turfoo-celery-worker-${WORKER_ID:-1}
  deploy:
    mode: replicated
    replicas: 3
  # Or manually with docker compose scale:
  # docker compose up -d --scale celery-worker=5
```

### 3. Celery Beat (`{project}-celery-beat`)
**Purpose:** Periodic task scheduler  
**Why Single Instance:**
- ⚠️ **Must be singleton per project**
- Multiple beat instances cause duplicate scheduled tasks
- Only scheduler, not executor

**Scaling Strategy:**
- ❌ Never scale horizontally
- ✅ Use HA with leader election if needed
- Lightweight - rarely needs scaling

## Scaling Decision Matrix

| Service | Dev | Staging | Production | Horizontal | Vertical | Notes |
|---------|-----|---------|------------|------------|----------|-------|
| **Redis** | 1 instance | 1 instance | Cluster/Managed | ⚠️ Complex | ✅ Yes | Use managed Redis in prod |
| **MinIO** | 1 instance | 1 instance | Distributed/S3 | ⚠️ 4+ nodes | ✅ Yes | Switch to S3 in prod |
| **RedisInsight** | 1 instance | Optional | ❌ Remove | ❌ No | N/A | Dev tool only |
| **PostgreSQL** | 1/project | 1/project | 1+replicas | ✅ Read replicas | ✅ Yes | Replicas for reads |
| **Celery Worker** | 1/project | 2+/project | 3+/project | ✅ Recommended | ⚠️ Rarely | Scale workers first |
| **Celery Beat** | 1/project | 1/project | 1/project | ❌ Never | N/A | Always singleton |

## Resource Allocation Guidelines

### Development (Your Current Setup)
```
Global:
- Redis: 512MB, 0.25 CPU
- MinIO: Unbounded (uses ~200MB)
- RedisInsight: Unbounded (uses ~200MB)

Per Project:
- PostgreSQL: 1GB, 0.5 CPU
- Celery Worker: Unbounded
- Celery Beat: Unbounded
```

**Total for 3 services:** ~5GB RAM, ~2 CPUs

### Staging Environment
```
Global:
- Redis: 2GB, 1 CPU (or managed)
- MinIO: 4GB, 1 CPU (or S3)
- RedisInsight: Remove

Per Project:
- PostgreSQL: 4GB, 2 CPU + 1 read replica
- Celery Workers: 2-3 instances @ 1GB each
- Celery Beat: 1 instance @ 512MB
```

**Total for 3 services:** ~35GB RAM, ~15 CPUs

### Production Environment
```
Global:
- Redis: AWS ElastiCache (managed)
- MinIO: AWS S3 (managed)
- RedisInsight: Remove

Per Project:
- PostgreSQL: AWS RDS (managed) + read replicas
- Celery Workers: 5+ instances (auto-scale)
- Celery Beat: 1 instance (HA with Kubernetes)
```

## Scaling Triggers & Monitoring

### Metrics to Monitor

**Redis:**
```bash
# Memory usage
redis-cli INFO memory | grep used_memory_human

# Commands per second
redis-cli INFO stats | grep instantaneous_ops_per_sec

# Evicted keys (cache full)
redis-cli INFO stats | grep evicted_keys
```

**PostgreSQL:**
```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Long-running queries
SELECT * FROM pg_stat_activity 
WHERE state = 'active' AND now() - query_start > interval '30 seconds';

-- Database size
SELECT pg_size_pretty(pg_database_size('turfoo_db'));
```

**Celery:**
```bash
# Queue length
celery -A turfoo.celery_app inspect active_queues

# Active tasks
celery -A turfoo.celery_app inspect active

# Worker stats
celery -A turfoo.celery_app inspect stats
```

### Auto-Scaling Recommendations

**Celery Workers (Kubernetes HPA):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: turfoo-celery-worker
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: turfoo-celery-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: celery_queue_length
      target:
        type: AverageValue
        averageValue: "100"
```

## Migration Paths

### From Dev to Production

**Phase 1: Staging (Validate Scaling)**
1. Keep Redis centralized, increase resources
2. Add PostgreSQL read replica per service
3. Scale Celery workers to 2-3 instances
4. Add monitoring (Prometheus + Grafana)

**Phase 2: Production (Managed Services)**
1. Migrate Redis → AWS ElastiCache/Redis Cloud
2. Migrate MinIO → AWS S3/GCS
3. Migrate PostgreSQL → AWS RDS/Cloud SQL
4. Deploy to Kubernetes/ECS with auto-scaling

**Phase 3: Optimization**
1. Add CDN for MinIO/S3 static content
2. Implement Redis read replicas
3. Database connection pooling (PgBouncer)
4. Queue-based Celery auto-scaling

## Network Topology

### Current (Single Network)
```
┌─────────────────────────────────────────┐
│         monorepo_net (bridge)           │
├─────────────────────────────────────────┤
│  monorepo-redis    (global)             │
│  monorepo-minio    (global)             │
│  turfoo-postgres   (project)            │
│  turfoo-celery-*   (project)            │
│  order-postgres    (project)            │
│  order-celery-*    (project)            │
└─────────────────────────────────────────┘
```

### Production (Multi-Network)
```
┌──────────────────────────────────────────┐
│       Public Internet                    │
└────────────────┬─────────────────────────┘
                 │
         ┌───────▼────────┐
         │  Load Balancer │
         └───────┬────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────────┐        ┌──────▼──────┐
│  App Net   │        │  Data Net   │
│  (APIs)    │────────│  (Private)  │
└────────────┘        └─────────────┘
│ Services   │        │ PostgreSQL  │
│ Celery     │        │ Redis       │
└────────────┘        │ S3/MinIO    │
                      └─────────────┘
```

## Cost Optimization

### Development
- ✅ Use shared global services
- ✅ Limit resources per container
- ✅ Single instance per service

### Staging
- ⚠️ Scale Celery workers only
- ✅ Use managed Redis (free tier)
- ✅ Add read replicas for testing

### Production
- 💰 Use managed services (reduces ops cost)
- 💰 Auto-scaling based on demand
- 💰 Reserved instances for steady-state
- 💰 Spot instances for Celery workers

## Summary

**Always Centralized (Singleton):**
- Redis (until production scale)
- MinIO (until production, then S3)
- RedisInsight (dev only)

**Always Distributed (Per-Project):**
- PostgreSQL databases
- Celery Beat (1 per project, never scale)

**Scale Horizontally:**
- Celery Workers (add more instances)
- PostgreSQL read replicas
- API servers (when you add them)

**Key Principle:**
> Start simple, scale what bottlenecks first. Monitor before scaling.

## References
- [Redis Scaling Strategies](https://redis.io/docs/management/scaling/)
- [PostgreSQL High Availability](https://www.postgresql.org/docs/current/high-availability.html)
- [Celery Autoscaling](https://docs.celeryq.dev/en/stable/userguide/workers.html#autoscaling)
- [MinIO Distributed Mode](https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-multi-node-multi-drive.html)
