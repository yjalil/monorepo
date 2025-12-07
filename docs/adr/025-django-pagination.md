# Django ADR-025: Pagination Implementation

## Status
Proposed

## Context
**Implements:** API ADR-016 (Pagination)

API ADR-016 requires:
- Cursor-based pagination (preferred over offset)
- Standard response structure with navigation links
- `cursor` and `limit` query parameters
- Avoid total count (performance reasons)

**Django challenge:** DRF includes offset pagination by default, but cursor pagination is better for large datasets.

## Decision

**Use DRF's CursorPagination as default. Provide standard response structure with navigation links.**

### Cursor Pagination Configuration

```python
# config/settings/rest_framework.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
}
```

### Custom Cursor Pagination Class

**Implements API ADR-016 response format:**

```python
# apps/shared/pagination.py
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from collections import OrderedDict

class StandardCursorPagination(CursorPagination):
    """
    Cursor-based pagination following API ADR-016.
    
    Response format:
    {
      "self": "https://api.example.com/users?cursor=abc123",
      "first": "https://api.example.com/users",
      "prev": "https://api.example.com/users?cursor=xyz789",
      "next": "https://api.example.com/users?cursor=def456",
      "items": [...]
    }
    
    Query parameters:
      ?cursor=abc123  # Opaque cursor token
      ?limit=50       # Page size (max 100)
    """
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100
    ordering = '-created_at'  # Default ordering
    cursor_query_param = 'cursor'
    
    def get_paginated_response(self, data):
        """Return response in API ADR-016 format."""
        return Response(OrderedDict([
            ('self', self.get_self_link()),
            ('first', self.get_first_link()),
            ('prev', self.get_previous_link()),
            ('next', self.get_next_link()),
            ('items', data)
        ]))
    
    def get_self_link(self):
        """Link to current page."""
        if not self.request:
            return None
        return self.request.build_absolute_uri()
    
    def get_first_link(self):
        """Link to first page (no cursor)."""
        if not self.request:
            return None
        url = self.request.build_absolute_uri(self.request.path)
        if self.get_page_size(self.request):
            return f"{url}?limit={self.get_page_size(self.request)}"
        return url
```

**Update settings:**

```python
# config/settings/rest_framework.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'apps.shared.pagination.StandardCursorPagination',
    'PAGE_SIZE': 20,
}
```

### Usage in ViewSets

**Pagination works automatically:**

```python
# apps/users/views.py
from rest_framework import viewsets
from .models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    User management endpoints.
    
    list: Retrieve paginated list of users (20 per page, cursor-based)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Pagination applied automatically via DEFAULT_PAGINATION_CLASS
```

**API requests:**

```http
# First page (default 20 items)
GET /api/users/

Response:
{
  "self": "https://api.example.com/api/users/",
  "first": "https://api.example.com/api/users/",
  "prev": null,
  "next": "https://api.example.com/api/users/?cursor=cD0yMDI0LTEyLTA2KzIwJTNBMDAlM0EwMCUyQjAwJTNBMDA%3D",
  "items": [
    {"id": 1, "username": "user1"},
    {"id": 2, "username": "user2"},
    ...
  ]
}

# Second page (using cursor from 'next' link)
GET /api/users/?cursor=cD0yMDI0LTEyLTA2KzIwJTNBMDAlM0EwMCUyQjAwJTNBMDA%3D

# Custom page size
GET /api/users/?limit=50
```

### Custom Ordering Per ViewSet

**Override ordering for specific resources:**

```python
# apps/orders/views.py
from rest_framework import viewsets
from apps.shared.pagination import StandardCursorPagination

class OrderPagination(StandardCursorPagination):
    """Order-specific pagination (most recent first)."""
    ordering = '-created_at'

class OrderViewSet(viewsets.ModelViewSet):
    """Order management endpoints."""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
```

### Disabling Pagination for Specific Endpoints

**Some endpoints shouldn't paginate:**

```python
# apps/users/views.py
from rest_framework.decorators import action
from rest_framework.response import Response

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=False, pagination_class=None)
    def roles(self, request):
        """
        Get all user roles (unpaginated).
        
        Small, stable datasets don't need pagination.
        """
        roles = UserRole.objects.all()
        serializer = UserRoleSerializer(roles, many=True)
        return Response(serializer.data)
```

### Filtering with Pagination

**Filters work with cursor pagination:**

```python
# apps/orders/views.py
from django_filters import rest_framework as filters

class OrderFilter(filters.FilterSet):
    status = filters.CharFilter(field_name='status')
    user = filters.NumberFilter(field_name='user_id')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    
    class Meta:
        model = Order
        fields = ['status', 'user', 'created_after']

class OrderViewSet(viewsets.ModelViewSet):
    """
    Order endpoints with filtering.
    
    list: List orders with optional filters
      ?status=pending  # Filter by status
      ?user=123        # Filter by user ID
      ?created_after=2024-01-01T00:00:00Z
      ?limit=50        # Page size
      ?cursor=...      # Pagination cursor
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filterset_class = OrderFilter
```

**Example request:**

```http
GET /api/orders/?status=pending&limit=50

Response:
{
  "self": "https://api.example.com/api/orders/?status=pending&limit=50",
  "first": "https://api.example.com/api/orders/?status=pending&limit=50",
  "prev": null,
  "next": "https://api.example.com/api/orders/?status=pending&limit=50&cursor=abc123",
  "items": [...]
}
```

### Offset Pagination (When Needed)

**Use offset pagination only when jumping to specific pages required:**

```python
# apps/shared/pagination.py
from rest_framework.pagination import LimitOffsetPagination

class StandardOffsetPagination(LimitOffsetPagination):
    """
    Offset-based pagination (only use when necessary).
    
    Query parameters:
      ?offset=100  # Skip first 100 items
      ?limit=20    # Page size
    
    WARNING: Poor performance on large datasets.
    """
    default_limit = 20
    max_limit = 100
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('self', self.request.build_absolute_uri()),
            ('first', self.get_first_link()),
            ('prev', self.get_previous_link()),
            ('next', self.get_next_link()),
            ('items', data)
        ]))
```

**Use in specific ViewSet:**

```python
# apps/reports/views.py
class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Reports with offset pagination (allows jumping to page N).
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    pagination_class = StandardOffsetPagination
```

## Why Cursor Over Offset?

**Offset pagination problems:**

```sql
-- Page 1 (fast)
SELECT * FROM orders ORDER BY created_at OFFSET 0 LIMIT 20;

-- Page 1000 (slow - database scans 20,000 rows!)
SELECT * FROM orders ORDER BY created_at OFFSET 20000 LIMIT 20;
```

**New data causes anomalies:**
```
Page 1: items 1-20
[New item inserted]
Page 2: items 21-40 becomes items 22-41 (item 21 skipped!)
```

**Cursor pagination solves this:**
```
Page 1: items where created_at > cursor_value
[New item inserted - doesn't affect cursor]
Page 2: Still correctly returns next 20 items
```

## Total Count Handling

**API ADR-016: Avoid total counts (expensive).**

```python
# ❌ Don't do this
class BadPagination(CursorPagination):
    def get_paginated_response(self, data):
        return Response({
            'total': self.queryset.count(),  # Expensive!
            'items': data
        })

# ✅ Do this (no total count)
class StandardCursorPagination(CursorPagination):
    def get_paginated_response(self, data):
        return Response({
            'items': data,
            'next': self.get_next_link(),
            'prev': self.get_previous_link(),
        })
```

**If total absolutely required:**

```python
# Only compute on explicit request
class OptionalCountPagination(StandardCursorPagination):
    def get_paginated_response(self, data):
        response_data = OrderedDict([
            ('items', data),
            ('next', self.get_next_link()),
        ])
        
        # Only if client explicitly asks
        if self.request.query_params.get('include_count') == 'true':
            response_data['total'] = self.queryset.count()
        
        return Response(response_data)
```

## Mechanical Enforcement

### Testing

```python
# apps/shared/tests/test_pagination.py
from django.test import TestCase
from rest_framework.test import APIClient
from apps.users.models import User

class PaginationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create 50 test users
        self.users = [
            User.objects.create(username=f'user{i}')
            for i in range(50)
        ]
    
    def test_default_page_size(self):
        """Default page size is 20 items."""
        response = self.client.get('/api/users/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['items']), 20)
    
    def test_response_structure(self):
        """Response follows API ADR-016 format."""
        response = self.client.get('/api/users/')
        
        # Required fields
        self.assertIn('self', response.data)
        self.assertIn('first', response.data)
        self.assertIn('next', response.data)
        self.assertIn('items', response.data)
        
        # No total count
        self.assertNotIn('total', response.data)
        self.assertNotIn('count', response.data)
    
    def test_cursor_pagination_links(self):
        """Navigation links use cursor parameter."""
        response = self.client.get('/api/users/')
        
        # Next link should have cursor parameter
        self.assertIsNotNone(response.data['next'])
        self.assertIn('cursor=', response.data['next'])
    
    def test_custom_page_size(self):
        """Client can specify page size via limit parameter."""
        response = self.client.get('/api/users/?limit=50')
        
        self.assertEqual(len(response.data['items']), 50)
    
    def test_max_page_size_enforced(self):
        """Page size cannot exceed maximum."""
        response = self.client.get('/api/users/?limit=1000')
        
        # Should be capped at max_page_size (100)
        self.assertLessEqual(len(response.data['items']), 100)
    
    def test_cursor_pagination_stability(self):
        """Cursor pagination stable when new items added."""
        # Get first page
        response1 = self.client.get('/api/users/')
        first_page_items = response1.data['items']
        next_cursor = response1.data['next']
        
        # Add new user (should not affect cursor)
        User.objects.create(username='new_user')
        
        # Get second page using cursor
        response2 = self.client.get(next_cursor)
        second_page_items = response2.data['items']
        
        # No overlap between pages
        first_page_ids = [item['id'] for item in first_page_items]
        second_page_ids = [item['id'] for item in second_page_items]
        self.assertEqual(set(first_page_ids) & set(second_page_ids), set())
```

### Semgrep Rules

```yaml
# .semgrep/django-pagination.yml
rules:
  - id: pagination-includes-total-count
    message: |
      Avoid including total count in pagination (expensive).
      See: docs/adr/django/025-pagination.md#total-count-handling
    pattern: |
      def get_paginated_response(self, data):
          ...
          'total': ...
          ...
    languages: [python]
    severity: WARNING
    paths:
      include:
        - "apps/*/pagination.py"
        - "apps/shared/pagination.py"
```

## OpenAPI Documentation

**drf-spectacular automatically documents pagination:**

```yaml
# Generated OpenAPI
/api/users/:
  get:
    parameters:
      - name: cursor
        in: query
        schema:
          type: string
        description: Opaque cursor for pagination
      - name: limit
        in: query
        schema:
          type: integer
          maximum: 100
        description: Number of results per page
    responses:
      '200':
        content:
          application/json:
            schema:
              type: object
              properties:
                self:
                  type: string
                  format: uri
                first:
                  type: string
                  format: uri
                prev:
                  type: string
                  format: uri
                next:
                  type: string
                  format: uri
                items:
                  type: array
                  items:
                    $ref: '#/components/schemas/User'
```

## Consequences

### Positive
- **Better performance** - Cursor pagination scales to millions of rows
- **No skipped items** - Stable under concurrent inserts
- **Standard format** - Consistent response structure across endpoints
- **No total count** - Avoids expensive COUNT(*) queries
- **Client-friendly** - Navigation links eliminate manual URL construction

### Negative
- **Cannot jump to page N** - Must follow cursor links sequentially
- **Opaque cursors** - Cannot inspect or construct cursor manually
- **Requires ordering** - Must have consistent sort order

### Mitigations
- **Use offset pagination** for specific use cases requiring page jumps
- **Document cursor behavior** in API docs
- **Provide first/prev/next links** so clients don't need to understand cursors

## Verification Checklist

After implementing this ADR:

- [ ] `apps/shared/pagination.py` created with StandardCursorPagination
- [ ] DEFAULT_PAGINATION_CLASS set to StandardCursorPagination
- [ ] PAGE_SIZE and MAX_PAGE_SIZE configured
- [ ] Response includes self, first, prev, next, items fields
- [ ] Response does NOT include total count by default
- [ ] Tests verify pagination response structure
- [ ] Tests verify cursor stability under inserts
- [ ] Tests verify max page size enforcement
- [ ] OpenAPI schema documents cursor and limit parameters

## References
- **Implements:** API ADR-016 (Pagination)
- [DRF CursorPagination](https://www.django-rest-framework.org/api-guide/pagination/#cursorpagination)
- [Why Cursor Pagination](https://docs.gitlab.com/ee/development/database/keyset_pagination.html)

## Related Django ADRs
- Django ADR-021: API First Implementation (OpenAPI generation)
- Django ADR-024: API Performance Optimization (query optimization)
