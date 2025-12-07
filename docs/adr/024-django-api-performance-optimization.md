# Django ADR-024: API Performance Optimization

## Status
Proposed

## Context
**Implements:** API ADR-017 (API Performance Optimization)

API ADR-017 requires:
- Gzip compression for bandwidth reduction
- Field filtering (partial responses via `?fields=` parameter)
- Resource embedding (reduce round trips via `?embed=` parameter)
- HTTP caching (ETag, Cache-Control headers)

**Django challenge:** DRF doesn't include these features by default. Need middleware + third-party packages.

## Decision

**Implement performance optimizations incrementally: compression always enabled, field filtering via package, caching when needed.**

### 1. Gzip Compression (Always Enabled)

**Django has built-in gzip middleware:**

```python
# config/settings/middleware.py
MIDDLEWARE = [
    'django.middleware.gzip.GzipMiddleware',  # FIRST in middleware chain
    'django.middleware.security.SecurityMiddleware',
    # ... rest of middleware
]
```

**Configuration:**

```python
# config/settings/performance.py

# Minimum response size to compress (bytes)
# Don't compress tiny responses (overhead > benefit)
GZIP_MINIMUM_SIZE = 1024  # 1KB

# Content types to compress
# Images/video already compressed, don't re-compress
GZIP_CONTENT_TYPES = [
    'text/html',
    'text/plain',
    'text/css',
    'application/json',
    'application/javascript',
    'text/xml',
    'application/xml',
]
```

**How it works:**
1. Client sends: `Accept-Encoding: gzip`
2. Django compresses response
3. Django adds: `Content-Encoding: gzip`
4. Client decompresses

**Bandwidth savings:** 60-90% for JSON responses.

### 2. Field Filtering (Partial Responses)

**Use drf-flex-fields for `?fields=` parameter:**

```bash
pip install drf-flex-fields
```

```python
# config/settings/rest_framework.py
REST_FRAMEWORK = {
    # ... other settings
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework_flex_fields.FlexFieldsRenderer',
    ],
}
```

**Usage in serializers:**

```python
# apps/users/serializers.py
from rest_framework_flex_fields import FlexFieldsModelSerializer

class UserSerializer(FlexFieldsModelSerializer):
    """
    User serializer with field filtering support.
    
    Supports:
      ?fields=id,username,email  # Only these fields
      ?omit=created_at,updated_at  # Exclude these fields
    """
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'created_at', 'updated_at']
```

**API usage:**

```http
# Full response
GET /api/users/123/
{
  "id": 123,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-12-06T20:00:00Z"
}

# Filtered response (smaller payload)
GET /api/users/123/?fields=id,username,email
{
  "id": 123,
  "username": "john",
  "email": "john@example.com"
}

# Omit fields
GET /api/users/123/?omit=created_at,updated_at
{
  "id": 123,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Nested field filtering:**

```python
# apps/orders/serializers.py
from rest_framework_flex_fields import FlexFieldsModelSerializer

class OrderSerializer(FlexFieldsModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'user', 'items', 'total', 'created_at']
        expandable_fields = {
            'user': ('apps.users.serializers.UserSerializer', {}),
            'items': ('apps.orders.serializers.OrderItemSerializer', {'many': True}),
        }
```

```http
# Minimal order
GET /api/orders/456/?fields=id,total

# Order with embedded user (only id and username)
GET /api/orders/456/?expand=user&fields=id,total,user.id,user.username
```

### 3. Resource Embedding (Reduce Round Trips)

**Using drf-flex-fields expandable fields:**

```python
# apps/orders/serializers.py
class OrderSerializer(FlexFieldsModelSerializer):
    """
    Order serializer with embedding support.
    
    Supports:
      ?expand=user,items  # Embed related resources
    """
    
    class Meta:
        model = Order
        fields = ['id', 'user_id', 'total', 'created_at']
        expandable_fields = {
            'user': ('apps.users.serializers.UserSerializer', {}),
            'items': ('apps.orders.serializers.OrderItemSerializer', {'many': True}),
        }
```

**Without embedding (2 requests):**

```http
GET /api/orders/456/
{
  "id": 456,
  "user_id": 123,
  "total": "99.99",
  "created_at": "2024-12-06T20:00:00Z"
}

GET /api/users/123/
{
  "id": 123,
  "username": "john",
  "email": "john@example.com"
}
```

**With embedding (1 request):**

```http
GET /api/orders/456/?expand=user
{
  "id": 456,
  "user_id": 123,
  "user": {
    "id": 123,
    "username": "john",
    "email": "john@example.com"
  },
  "total": "99.99",
  "created_at": "2024-12-06T20:00:00Z"
}
```

**Multiple expansions:**

```http
GET /api/orders/456/?expand=user,items
{
  "id": 456,
  "user": {...},
  "items": [
    {"id": 1, "product": "Widget", "price": "49.99"},
    {"id": 2, "product": "Gadget", "price": "49.99"}
  ],
  "total": "99.99"
}
```

### 4. HTTP Caching (ETag Support)

**Django's ConditionalGetMiddleware provides ETag:**

```python
# config/settings/middleware.py
MIDDLEWARE = [
    'django.middleware.gzip.GzipMiddleware',
    # ... other middleware
    'django.middleware.http.ConditionalGetMiddleware',  # ETag support
]
```

**How ETags work:**

```http
# First request
GET /api/users/123/
HTTP/1.1 200 OK
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
{
  "id": 123,
  "username": "john"
}

# Second request (with If-None-Match)
GET /api/users/123/
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"

HTTP/1.1 304 Not Modified
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
(no body - client uses cached version)
```

**Cache-Control headers:**

```python
# apps/users/views.py
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

class UserViewSet(viewsets.ModelViewSet):
    """User management endpoints."""
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request):
        """List users with caching."""
        return super().list(request)
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def retrieve(self, request, pk=None):
        """Get user with caching."""
        return super().retrieve(request, pk)
```

**Response includes:**

```http
HTTP/1.1 200 OK
Cache-Control: max-age=300  # 5 minutes
ETag: "abc123"
```

### 5. Redis Cache Backend

**For production caching:**

```python
# config/settings/cache.py
import os

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'myproject',
        'TIMEOUT': 300,  # Default timeout (5 minutes)
    }
}
```

### 6. Database Query Optimization

**Use select_related and prefetch_related to avoid N+1 queries:**

```python
# apps/orders/views.py
class OrderViewSet(viewsets.ModelViewSet):
    """
    Order endpoints with optimized queries.
    """
    serializer_class = OrderSerializer
    
    def get_queryset(self):
        """
        Optimize queries based on requested expansions.
        """
        queryset = Order.objects.all()
        
        # Check if user wants expanded fields
        expand = self.request.query_params.get('expand', '').split(',')
        
        if 'user' in expand:
            queryset = queryset.select_related('user')  # JOIN user table
        
        if 'items' in expand:
            queryset = queryset.prefetch_related('items')  # Separate query for items
        
        return queryset
```

**Without optimization (N+1 problem):**
```python
# 1 query to get orders
orders = Order.objects.all()

# N queries (one per order) to get users
for order in orders:
    print(order.user.username)  # Hits database each time!
```

**With optimization (2 queries total):**
```python
# 1 query to get orders + users (JOIN)
orders = Order.objects.select_related('user').all()

# 0 additional queries
for order in orders:
    print(order.user.username)  # Already loaded!
```

### 7. Conditional Query Optimization

**Only fetch related data when client asks for it:**

```python
# apps/users/views.py
from django.db.models import Prefetch

class UserViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Only optimize if client is expanding orders
        if 'orders' in self.request.query_params.get('expand', ''):
            queryset = queryset.prefetch_related(
                Prefetch(
                    'orders',
                    queryset=Order.objects.select_related('payment')
                )
            )
        
        return queryset
```

## Mechanical Enforcement

### Testing

```python
# apps/shared/tests/test_performance.py
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.users.models import User

class PerformanceTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='test', password='test')
        self.client.force_authenticate(user=self.user)
    
    def test_gzip_compression(self):
        """Responses are compressed when client supports gzip."""
        response = self.client.get(
            '/api/users/',
            HTTP_ACCEPT_ENCODING='gzip'
        )
        
        self.assertEqual(response['Content-Encoding'], 'gzip')
    
    def test_field_filtering(self):
        """Field filtering returns only requested fields."""
        response = self.client.get('/api/users/1/?fields=id,username')
        
        self.assertIn('id', response.data)
        self.assertIn('username', response.data)
        self.assertNotIn('email', response.data)
        self.assertNotIn('created_at', response.data)
    
    def test_etag_generation(self):
        """GET requests generate ETag header."""
        response = self.client.get('/api/users/1/')
        
        self.assertIn('ETag', response)
    
    def test_conditional_get(self):
        """If-None-Match returns 304 when content unchanged."""
        # First request
        response1 = self.client.get('/api/users/1/')
        etag = response1['ETag']
        
        # Second request with If-None-Match
        response2 = self.client.get(
            '/api/users/1/',
            HTTP_IF_NONE_MATCH=etag
        )
        
        self.assertEqual(response2.status_code, 304)
```

### Query Performance Testing

```python
# apps/orders/tests/test_query_performance.py
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

class QueryPerformanceTest(TestCase):
    def setUp(self):
        # Create test data
        users = [User.objects.create(username=f'user{i}') for i in range(10)]
        for user in users:
            Order.objects.create(user=user, total=100)
    
    def test_list_without_expansion_efficient(self):
        """List orders without expansion should not query users."""
        client = APIClient()
        
        with CaptureQueriesContext(connection) as context:
            response = client.get('/api/orders/')
        
        # Should only query orders table
        self.assertEqual(len(context.captured_queries), 1)
    
    def test_list_with_user_expansion_efficient(self):
        """List orders with user expansion should use select_related."""
        client = APIClient()
        
        with CaptureQueriesContext(connection) as context:
            response = client.get('/api/orders/?expand=user')
        
        # Should query orders + users in ONE query (JOIN)
        self.assertEqual(len(context.captured_queries), 1)
        
        # Verify query uses JOIN
        query = context.captured_queries[0]['sql']
        self.assertIn('JOIN', query.upper())
```

### Performance Monitoring

```python
# apps/shared/middleware.py
import time
import logging

logger = logging.getLogger(__name__)

class ResponseTimeLoggingMiddleware:
    """
    Log slow API responses for performance monitoring.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        
        # Log slow responses (>1 second)
        if duration > 1.0:
            logger.warning(
                f"Slow response: {request.method} {request.path} "
                f"took {duration:.2f}s | Flow-ID: {getattr(request, 'flow_id', 'unknown')}"
            )
        
        # Add response time header for debugging
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response
```

## Consequences

### Positive
- **60-90% bandwidth reduction** with gzip
- **Smaller payloads** with field filtering
- **Fewer round trips** with resource embedding
- **Reduced database load** with HTTP caching
- **Better mobile performance** (less data, fewer requests)
- **Cost savings** (bandwidth, database queries)

### Negative
- **Complexity** - More query parameters to support
- **Cache invalidation** - Must invalidate when data changes
- **CPU overhead** - Gzip compression uses CPU
- **Testing complexity** - Must test various expand/fields combinations

### Mitigations
- **Gzip CPU cost is minimal** (modern servers handle easily)
- **Cache with short TTL** (5-15 minutes) reduces stale data risk
- **Django Debug Toolbar** helps catch N+1 queries in development
- **Load testing** verifies performance improvements

## Verification Checklist

After implementing this ADR:

- [ ] GzipMiddleware first in MIDDLEWARE setting
- [ ] `pip install drf-flex-fields` installed
- [ ] Serializers use FlexFieldsModelSerializer
- [ ] ConditionalGetMiddleware enabled for ETag support
- [ ] Redis cache configured (production)
- [ ] ViewSets use select_related/prefetch_related appropriately
- [ ] Tests verify gzip compression works
- [ ] Tests verify field filtering works
- [ ] Tests verify ETag generation and 304 responses
- [ ] Query performance tests catch N+1 issues
- [ ] Response time logging middleware configured

## Performance Benchmarks

**Expected improvements (example):**

| Optimization | Before | After | Improvement |
|--------------|--------|-------|-------------|
| Gzip (JSON response) | 50 KB | 8 KB | 84% smaller |
| Field filtering | 2 KB | 0.5 KB | 75% smaller |
| Resource embedding | 2 requests | 1 request | 50% fewer |
| ETag caching | 200ms | 5ms (304) | 97.5% faster |
| select_related | 11 queries | 1 query | 90% fewer |

## References
- **Implements:** API ADR-017 (API Performance Optimization)
- [Django GzipMiddleware](https://docs.djangoproject.com/en/stable/ref/middleware/#django.middleware.gzip.GzipMiddleware)
- [drf-flex-fields Documentation](https://github.com/rsinger86/drf-flex-fields)
- [Django Caching Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Django Query Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)

## Related Django ADRs
- Django ADR-021: API First Implementation (OpenAPI)
- Django ADR-022: HTTP Header Standards (custom headers)
