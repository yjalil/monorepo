FROM python:3.12-slim

WORKDIR /app

# Copy the turfoo package
COPY backends/svc-turfoo-ingest/ .

# Install dependencies using pip (since uv.lock is in project root)
RUN pip install --no-cache-dir \
    celery[redis] \
    feedparser \
    pydantic-settings \
    boto3 \
    loguru

# Create non-root user for security
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-a-user-for-the-container-has-been-created
RUN useradd -m -u 1000 celery && chown -R celery:celery /app
USER celery

# Add health check for Celery worker
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-healthcheck-instructions-have-been-added-to-container-images
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD celery -A turfoo.celery_app inspect ping -d celery@$HOSTNAME

# Default command
CMD ["celery", "-A", "turfoo.celery_app", "worker", "--loglevel=info"]
