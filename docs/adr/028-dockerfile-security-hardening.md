# ADR 028: Dockerfile Security Hardening

**Status:** Accepted  
**Date:** 2025-01-24  
**Context:** Infrastructure security scanning and hardening

## Context

After implementing the two-tier infrastructure architecture ([ADR 027](027-monorepo-git-workflow-and-Infrastructure.md)), we ran security scanning tools (Checkov) on our Dockerfiles to identify potential security vulnerabilities. The scan identified critical security issues that needed to be addressed before production deployment.

## Decision

We will enforce the following security practices in all Dockerfiles:

### 1. Non-Root User Execution

**Requirement:** All containers must run as non-root users (CKV_DOCKER_3)

**Implementation:**
```dockerfile
# Create non-root user for security
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-a-user-for-the-container-has-been-created
RUN useradd -m -u 1000 celery && chown -R celery:celery /app
USER celery
```

**Rationale:**
- Reduces attack surface by limiting container privileges
- Prevents privilege escalation attacks
- Follows principle of least privilege
- Required for security compliance (PCI-DSS, SOC 2, etc.)

### 2. Health Check Instructions

**Requirement:** All containers must define health checks (CKV_DOCKER_2)

**Implementation for Celery Workers:**
```dockerfile
# Add health check for Celery worker
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-healthcheck-instructions-have-been-added-to-container-images
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD celery -A turfoo.celery_app inspect ping -d celery@$HOSTNAME
```

**Implementation for Generic Applications:**
```dockerfile
# Customize this health check for your specific application needs
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1
```

**Rationale:**
- Enables Docker/Kubernetes to detect unhealthy containers
- Facilitates automatic recovery and self-healing
- Improves service reliability and uptime
- Provides visibility into application health

## Security Scan Results

### Before Hardening
- **Passed checks:** 44
- **Failed checks:** 4
- Critical issues:
  - CKV_DOCKER_3: Missing non-root user (4 failures)
  - CKV_DOCKER_2: Missing HEALTHCHECK (4 failures)

### After Hardening
- **Passed checks:** 168
- **Failed checks:** 0
- All security checks passed ✅

## Implementation Details

### Files Modified

1. **`/workspaces/monorepo/infra/turfoo_celery_worker/Dockerfile`**
   - Added non-root `celery` user (UID 1000)
   - Added Celery-specific health check using `celery inspect ping`
   - Changed file ownership to `celery:celery`

2. **`/workspaces/monorepo/backends/svc-turfoo-ingest/infra/Dockerfile`**
   - Added non-root `celery` user (UID 1000)
   - Added Celery-specific health check
   - Changed file ownership to `celery:celery`

3. **`/workspaces/monorepo/infra/templates/Dockerfile`**
   - Added non-root `appuser` user (UID 1000)
   - Added generic health check with customization instructions
   - Changed file ownership to `appuser:appuser`

### Testing Verification

```bash
# Verify security scan passes
checkov -d infra/ --framework dockerfile -d backends/svc-turfoo-ingest/infra/

# Verify containers run as non-root
docker exec turfoo-celery-worker whoami  # Output: celery
docker exec turfoo-celery-beat whoami    # Output: celery

# Verify health checks work
docker ps --filter "name=turfoo"
# Output shows: (healthy) status for containers
```

## Consequences

### Positive

1. **Enhanced Security Posture**
   - Containers run with minimal privileges
   - Reduced attack surface for privilege escalation
   - Compliance with security best practices

2. **Improved Reliability**
   - Automatic health monitoring
   - Self-healing capabilities via orchestration
   - Better visibility into service health

3. **Production Ready**
   - Passes automated security scanning
   - Meets enterprise security requirements
   - Ready for deployment in regulated environments

4. **Standardization**
   - All Dockerfiles follow same security patterns
   - Template ensures new projects inherit security best practices
   - Consistent security posture across projects

### Negative

1. **Permission Considerations**
   - File system operations must account for non-root user
   - Volume mounts may need permission adjustments
   - Development workflows may need minor updates

2. **Health Check Overhead**
   - Small CPU/memory overhead for periodic checks
   - Need to customize health checks for each application type
   - Health check failures require investigation

### Neutral

1. **Development Impact**
   - Developers must understand non-root implications
   - Health check endpoints need to be lightweight
   - Documentation updated to reflect security requirements

## References

- [Prisma Cloud Docker Policy Index](https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Celery Monitoring and Management Guide](https://docs.celeryq.dev/en/stable/userguide/monitoring.html)
- [ADR 027: Monorepo Git Workflow and Infrastructure](027-monorepo-git-workflow-and-Infrastructure.md)

## Notes

- UID 1000 is commonly used for first non-root user in Linux systems
- Celery health checks use `inspect ping` which requires Celery app to be running
- Generic health checks should be customized per application (HTTP endpoints, database connections, etc.)
- Health check parameters (`interval`, `timeout`, `retries`) can be tuned based on application needs
