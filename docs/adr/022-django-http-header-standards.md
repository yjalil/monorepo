# Django ADR-022: HTTP Header Standards Implementation

## Status
Proposed

## Context
**Implements:** API ADR-010 (HTTP Header Standards)

API ADR-010 requires:
- `X-Flow-ID` header for request tracking across services
- `Idempotency-Key` header for safe retries
- `ETag` support for conditional requests
- Standard `Content-*` headers (handled by DRF)

**Django challenge:** DRF handles standard headers automatically, but custom headers (X-Flow-ID, Idempotency-Key) need middleware implementation.

## Decision

**Implement custom middleware for X-Flow-ID tracking. Document patterns for Idempotency-Key and ETag support.**

### X-Flow-ID Middleware

**Purpose:** Every request gets a unique ID that follows it through logs and service calls.

```python
# apps/shared/middleware.py
import uuid
import logging

logger = logging.getLogger(__name__)

class FlowIDMiddleware:
    """
    Implements API ADR-010: X-Flow-ID header for request tracking.
    
    - Extracts X-Flow-ID from request header
    - Generates new UUID if not provided
    - Adds Flow-ID to response header
    - Attaches Flow-ID to request for logging
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extract or generate Flow ID
        flow_id = request.headers.get('X-Flow-ID')
        
        if not flow_id:
            flow_id = str(uuid.uuid4())
            logger.debug(f"Generated new Flow-ID: {flow_id}")
        
        # Attach to request object
        request.flow_id = flow_id
        
        # Process request
        response = self.get_response(request)
        
        # Add to response header
        response['X-Flow-ID'] = flow_id
        
        return response
```

### Configuration

```python
# config/settings/middleware.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'apps.shared.middleware.FlowIDMiddleware',  # Add early in chain
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**Why early in chain:** Flow-ID should be available to all subsequent middleware and views for logging.

### CORS Configuration

```python
# config/settings/cors.py
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-flow-id',  # Custom header (API ADR-010)
    'idempotency-key',  # Custom header (API ADR-010)
]

CORS_EXPOSE_HEADERS = [
    'x-flow-id',  # Expose to browser clients
]
```

### Logging Integration

**Attach Flow-ID to all log messages:**

```python
# apps/shared/logging.py
import logging
from threading import local

# Thread-local storage for Flow-ID
_thread_locals = local()

def get_flow_id():
    """Get Flow-ID from thread-local storage."""
    return getattr(_thread_locals, 'flow_id', None)

def set_flow_id(flow_id):
    """Store Flow-ID in thread-local storage."""
    _thread_locals.flow_id = flow_id

class FlowIDFilter(logging.Filter):
    """Add Flow-ID to every log record."""
    
    def filter(self, record):
        record.flow_id = get_flow_id() or 'no-flow-id'
        return True
```

**Update middleware to use thread-local storage:**

```python
# apps/shared/middleware.py
import uuid
import logging
from .logging import set_flow_id

logger = logging.getLogger(__name__)

class FlowIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        flow_id = request.headers.get('X-Flow-ID', str(uuid.uuid4()))
        request.flow_id = flow_id
        
        # Store in thread-local for logging
        set_flow_id(flow_id)
        
        response = self.get_response(request)
        response['X-Flow-ID'] = flow_id
        
        return response
```

**Logging configuration:**

```python
# config/settings/logging.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} flow_id={flow_id} {name} {message}',
            'style': '{',
        },
    },
    'filters': {
        'add_flow_id': {
            '()': 'apps.shared.logging.FlowIDFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['add_flow_id'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

### Usage in Views

**Access Flow-ID in views:**

```python
# apps/users/views.py
import logging

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    def create(self, request):
        logger.info(f"Creating user (Flow-ID: {request.flow_id})")
        # ... implementation
```

**Logs output:**
```
[INFO] 2024-12-06 20:00:00 flow_id=550e8400-e29b-41d4-a716-446655440000 apps.users.views Creating user
```

### Propagating Flow-ID to External Services

**When calling external APIs, pass Flow-ID:**

```python
# apps/users/services.py
import requests

def call_external_api(request):
    """Call external service with Flow-ID propagation."""
    response = requests.post(
        'https://external-api.example.com/endpoint',
        headers={
            'X-Flow-ID': request.flow_id,  # Propagate Flow-ID
            'Authorization': 'Bearer ...',
        },
        json={'data': 'value'},
    )
    return response.json()
```

## Idempotency-Key Support

**Pattern for implementing idempotency (when needed):**

```python
# apps/shared/middleware.py
from django.core.cache import cache
from django.http import JsonResponse

class IdempotencyMiddleware:
    """
    Implements API ADR-010: Idempotency-Key header support.
    
    Only applies to POST requests with Idempotency-Key header.
    Stores response in cache for 24 hours.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only for POST with Idempotency-Key
        if request.method != 'POST':
            return self.get_response(request)
        
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return self.get_response(request)
        
        # Check cache for previous response
        cache_key = f'idempotency:{idempotency_key}'
        cached_response = cache.get(cache_key)
        
        if cached_response:
            # Return cached response
            return JsonResponse(
                cached_response['body'],
                status=cached_response['status']
            )
        
        # Process new request
        response = self.get_response(request)
        
        # Cache successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            cache.set(
                cache_key,
                {
                    'body': response.data if hasattr(response, 'data') else {},
                    'status': response.status_code,
                },
                timeout=86400  # 24 hours
            )
        
        return response
```

**Note:** Add to MIDDLEWARE only when idempotency is needed. Most apps don't need this initially.

## ETag Support

**Django's ConditionalGetMiddleware provides ETag support:**

```python
# config/settings/middleware.py
MIDDLEWARE = [
    # ... other middleware
    'django.middleware.http.ConditionalGetMiddleware',  # ETag support
]
```

**DRF ViewSets automatically generate ETags based on response content.**

**Testing ETag behavior:**

```python
# apps/users/tests/test_etag.py
from django.test import TestCase
from rest_framework.test import APIClient
from apps.users.models import User

class ETagTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='test', password='test')
        self.client.force_authenticate(user=self.user)
    
    def test_etag_on_get(self):
        """GET requests return ETag header."""
        response = self.client.get('/api/users/me/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
    
    def test_if_none_match(self):
        """If-None-Match returns 304 when ETag matches."""
        # First request
        response1 = self.client.get('/api/users/me/')
        etag = response1['ETag']
        
        # Second request with If-None-Match
        response2 = self.client.get(
            '/api/users/me/',
            HTTP_IF_NONE_MATCH=etag
        )
        
        self.assertEqual(response2.status_code, 304)  # Not Modified
```

## Mechanical Enforcement

### Testing

```python
# apps/shared/tests/test_flow_id_middleware.py
from django.test import TestCase, RequestFactory
from apps.shared.middleware import FlowIDMiddleware

class FlowIDMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = FlowIDMiddleware(get_response=lambda r: None)
    
    def test_extracts_flow_id_from_header(self):
        """Middleware extracts X-Flow-ID from request header."""
        request = self.factory.get('/', HTTP_X_FLOW_ID='test-flow-id')
        
        self.middleware(request)
        
        self.assertEqual(request.flow_id, 'test-flow-id')
    
    def test_generates_flow_id_if_missing(self):
        """Middleware generates UUID if X-Flow-ID not provided."""
        request = self.factory.get('/')
        
        self.middleware(request)
        
        self.assertIsNotNone(request.flow_id)
        # Should be valid UUID format
        import uuid
        uuid.UUID(request.flow_id)  # Raises ValueError if invalid
    
    def test_adds_flow_id_to_response(self):
        """Middleware adds X-Flow-ID to response header."""
        def mock_get_response(request):
            from django.http import HttpResponse
            return HttpResponse()
        
        middleware = FlowIDMiddleware(get_response=mock_get_response)
        request = self.factory.get('/')
        
        response = middleware(request)
        
        self.assertIn('X-Flow-ID', response)
        self.assertEqual(response['X-Flow-ID'], request.flow_id)
```

### Integration Test

```python
# apps/users/tests/test_flow_id_integration.py
from django.test import TestCase
from rest_framework.test import APIClient
from apps.users.models import User

class FlowIDIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='test', password='test')
        self.client.force_authenticate(user=self.user)
    
    def test_flow_id_roundtrip(self):
        """Flow-ID sent in request is returned in response."""
        response = self.client.get(
            '/api/users/me/',
            HTTP_X_FLOW_ID='custom-flow-id'
        )
        
        self.assertEqual(response['X-Flow-ID'], 'custom-flow-id')
    
    def test_flow_id_generated_if_missing(self):
        """Flow-ID generated automatically if not provided."""
        response = self.client.get('/api/users/me/')
        
        self.assertIn('X-Flow-ID', response)
        # Should be valid UUID
        import uuid
        uuid.UUID(response['X-Flow-ID'])
```

### Semgrep Rules

```yaml
# .semgrep/django-headers.yml
rules:
  - id: external-api-call-missing-flow-id
    message: |
      External API calls should propagate X-Flow-ID header.
      Add: headers={'X-Flow-ID': request.flow_id}
      See: docs/adr/django/022-http-header-standards.md
    pattern: |
      requests.$METHOD($URL, ...)
    pattern-not: |
      requests.$METHOD($URL, headers={..., 'X-Flow-ID': ...}, ...)
    languages: [python]
    severity: WARNING
    paths:
      include:
        - "apps/*/services.py"
```

## Consequences

### Positive
- **Request tracing** - X-Flow-ID enables tracking requests across services
- **Debugging** - Search logs by Flow-ID to see entire request journey
- **Idempotency support** - Safe retries with Idempotency-Key (when needed)
- **Caching** - ETag support for conditional requests
- **CORS compliant** - Custom headers allowed for browser clients

### Negative
- **Thread-local complexity** - Flow-ID storage requires thread-local pattern
- **Cache dependency** - Idempotency requires Redis/cache backend
- **Performance overhead** - Minimal (UUID generation + cache lookup)

### Mitigations
- **Thread-local only for logging** - Request object holds Flow-ID for views
- **Idempotency optional** - Only add middleware when needed
- **Efficient UUID generation** - uuid.uuid4() is fast

## Verification Checklist

After implementing this ADR:

- [ ] `apps/shared/middleware.py` created with FlowIDMiddleware
- [ ] FlowIDMiddleware added to MIDDLEWARE setting
- [ ] `apps/shared/logging.py` created with FlowIDFilter
- [ ] Logging configuration includes FlowIDFilter
- [ ] CORS_ALLOW_HEADERS includes `x-flow-id` and `idempotency-key`
- [ ] CORS_EXPOSE_HEADERS includes `x-flow-id`
- [ ] Tests in `apps/shared/tests/test_flow_id_middleware.py` pass
- [ ] Log messages include `flow_id=...`
- [ ] External API calls propagate X-Flow-ID header

## References
- **Implements:** API ADR-010 (HTTP Header Standards)
- [Django Middleware Documentation](https://docs.djangoproject.com/en/stable/topics/http/middleware/)
- [Python logging.Filter Documentation](https://docs.python.org/3/library/logging.html#filter-objects)

## Related Django ADRs
- Django ADR-021: API First Implementation (OpenAPI generation)
- Django ADR-023: API Security (JWT authentication)
