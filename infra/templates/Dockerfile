FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install uv && uv sync --frozen

# Create non-root user for security
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-a-user-for-the-container-has-been-created
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Add health check appropriate for your application
# Ref: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-healthcheck-instructions-have-been-added-to-container-images
# Customize this health check for your specific application needs
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command (can be overridden in compose.yml)
CMD ["python", "-m", "your_module"]
