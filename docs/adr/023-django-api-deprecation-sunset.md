# Django ADR-023: API Deprecation and Sunset

## Status
Proposed

## Context
**Implements:** API ADR-008 (API Deprecation and Sunset)

API ADR-008 requires:
- Mark deprecated endpoints in OpenAPI spec with `deprecated: true`
- Return `Deprecation` header (RFC 9745) - timestamp when deprecated
- Return `Sunset` header (RFC 8594) - timestamp when removed
- Document deprecation reason and migration path
- Obtain client consent before shutdown

**Django challenge:** DRF has no built-in deprecation support. Need custom decorator + middleware.

## Decision

**Implement deprecation through decorator that adds headers and marks OpenAPI spec automatically.**

### Deprecation Decorator

```python
# apps/shared/deprecation.py
from functools import wraps
from datetime import datetime
from django.utils import timezone
from drf_spectacular.utils import extend_schema

def deprecated(sunset_date: str, reason: str, replacement: str = None):
    """
    Mark an endpoint as deprecated.
    
    Args:
        sunset_date: ISO 8601 date when endpoint will be removed (e.g., "2025-12-31")
        reason: Why this endpoint is being deprecated
        replacement: Which endpoint to use instead (optional)
    
    Usage:
        @deprecated(
            sunset_date="2025-12-31",
            reason="Replaced by v2 API",
            replacement="GET /api/v2/users/"
        )
        @action(detail=False)
        def old_endpoint(self, request):
            ...
    """
    def decorator(func):
        # Parse sunset date to get deprecation timestamp
        sunset_dt = datetime.fromisoformat(sunset_date + "T00:00:00Z")
        
        # Assume deprecated 6 months before sunset
        # Or use current time if sunset is less than 6 months away
        six_months_before = sunset_dt.timestamp() - (6 * 30 * 24 * 60 * 60)
        deprecation_timestamp = int(min(timezone.now().timestamp(), six_months_before))
        
        # Build deprecation message
        message = f"{reason}."
        if replacement:
            message += f" Use {replacement} instead."
        message += f" Will be removed on {sunset_date}."
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute original function
            response = func(*args, **kwargs)
            
            # Add deprecation headers
            response['Deprecation'] = f"@{deprecation_timestamp}"
            response['Sunset'] = sunset_dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            return response
        
        # Mark as deprecated in OpenAPI
        wrapper = extend_schema(
            deprecated=True,
            description=f"**DEPRECATED:** {message}\n\n" + (func.__doc__ or "")
        )(wrapper)
        
        # Store metadata for middleware
        wrapper._deprecation_info = {
            'sunset_date': sunset_date,
            'reason': reason,
            'replacement': replacement,
            'message': message,
        }
        
        return wrapper
    
    return decorator
```

### Usage in ViewSets

```python
# apps/users/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.shared.deprecation import deprecated
from .models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    """User management endpoints."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @deprecated(
        sunset_date="2025-12-31",
        reason="This endpoint uses outdated authentication",
        replacement="GET /api/v2/users/profile/"
    )
    @action(detail=False, methods=['get'])
    def legacy_profile(self, request):
        """Get user profile (legacy endpoint).
        
        Returns basic user profile information.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
```

**Generated OpenAPI:**
```yaml
/api/users/legacy_profile/:
  get:
    deprecated: true
    description: |
      **DEPRECATED:** This endpoint uses outdated authentication. 
      Use GET /api/v2/users/profile/ instead. 
      Will be removed on 2025-12-31.
      
      Returns basic user profile information.
```

**Response headers:**
```http
HTTP/1.1 200 OK
Deprecation: @1735689600
Sunset: Tue, 31 Dec 2025 00:00:00 GMT
X-Flow-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Deprecation Logging Middleware

**Track usage of deprecated endpoints:**

```python
# apps/shared/middleware.py
import logging

logger = logging.getLogger(__name__)

class DeprecationLoggingMiddleware:
    """
    Log all requests to deprecated endpoints.
    
    Helps track which clients are still using deprecated APIs
    so we can coordinate migration before sunset.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if response has Deprecation header
        if 'Deprecation' in response:
            logger.warning(
                f"Deprecated endpoint called: {request.method} {request.path} "
                f"| Flow-ID: {getattr(request, 'flow_id', 'unknown')} "
                f"| User: {getattr(request.user, 'username', 'anonymous')} "
                f"| Sunset: {response.get('Sunset', 'unknown')}"
            )
        
        return response
```

**Configuration:**

```python
# config/settings/middleware.py
MIDDLEWARE = [
    'apps.shared.middleware.FlowIDMiddleware',
    'apps.shared.middleware.DeprecationLoggingMiddleware',  # After FlowID
    # ... other middleware
]
```

**Log output:**
```
[WARNING] 2024-12-06 20:00:00 flow_id=550e8400... apps.shared.middleware 
Deprecated endpoint called: GET /api/users/legacy_profile/ | Flow-ID: 550e8400... | User: john | Sunset: Tue, 31 Dec 2025 00:00:00 GMT
```

### Monitoring Dashboard Query

**Find clients using deprecated endpoints (for coordination):**

```python
# Example: Django admin command to check deprecated endpoint usage
# management/commands/check_deprecated_usage.py
from django.core.management.base import BaseCommand
import re

class Command(BaseCommand):
    help = 'Analyze logs to find clients using deprecated endpoints'
    
    def handle(self, *args, **options):
        # Parse logs (or query logging service)
        # Group by Flow-ID, User, Endpoint
        # Output: Which clients need to migrate
        
        self.stdout.write(self.style.SUCCESS(
            'Deprecated endpoint usage report generated'
        ))
```

### Deprecating Entire ViewSets

**When deprecating all actions in a ViewSet:**

```python
# apps/legacy/views.py
from drf_spectacular.utils import extend_schema_view, extend_schema

@extend_schema_view(
    list=extend_schema(deprecated=True),
    retrieve=extend_schema(deprecated=True),
    create=extend_schema(deprecated=True),
    update=extend_schema(deprecated=True),
    destroy=extend_schema(deprecated=True),
)
class LegacyOrderViewSet(viewsets.ModelViewSet):
    """
    Legacy order management (DEPRECATED).
    
    All endpoints in this ViewSet are deprecated.
    Migrate to /api/v2/orders/ before 2025-12-31.
    """
    queryset = Order.objects.all()
    serializer_class = LegacyOrderSerializer
    
    def finalize_response(self, request, response, *args, **kwargs):
        """Add deprecation headers to all responses."""
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Deprecation'] = '@1735689600'
        response['Sunset'] = 'Tue, 31 Dec 2025 00:00:00 GMT'
        return response
```

### Deprecating Serializer Fields

**When deprecating specific fields:**

```python
# apps/users/serializers.py
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

class UserSerializer(serializers.ModelSerializer):
    legacy_field = serializers.CharField(
        help_text="DEPRECATED: Use new_field instead. Will be removed 2025-12-31.",
        required=False
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'legacy_field', 'new_field']
```

**In OpenAPI schema:**
```yaml
User:
  properties:
    legacy_field:
      type: string
      description: "DEPRECATED: Use new_field instead. Will be removed 2025-12-31."
```

## Shutdown Process

**Step-by-step process before removing deprecated endpoints:**

### 1. Mark as Deprecated

```python
@deprecated(
    sunset_date="2025-12-31",
    reason="Replaced by v2 API",
    replacement="GET /api/v2/users/"
)
```

### 2. Monitor Usage (3-6 months)

```bash
# Query logs for deprecated endpoint usage
grep "Deprecated endpoint called" logs/*.log | \
  grep "users/legacy_profile" | \
  awk '{print $10}' | sort | uniq -c

# Output: Which users are calling deprecated endpoint
#   15 User: client-app-1
#    8 User: mobile-app-2
#    2 User: partner-integration
```

### 3. Contact Clients

**Email template:**

```
Subject: Action Required - API Endpoint Deprecation

Hello,

We've detected that your application is using a deprecated API endpoint:

  Endpoint: GET /api/users/legacy_profile/
  Sunset Date: 2025-12-31
  Replacement: GET /api/v2/users/profile/

Migration Guide: https://docs.example.com/migration/users-v2

Please migrate before the sunset date to avoid service disruption.

Questions? Reply to this email.
```

### 4. Verify Migration

```bash
# After clients confirm migration, verify in logs
grep "Deprecated endpoint called" logs/*.log | \
  grep "users/legacy_profile" | \
  grep "2024-11-01" | wc -l

# Should be 0 or very low
```

### 5. Remove Endpoint

**Only after:**
- ✅ All clients migrated
- ✅ Sunset date passed
- ✅ Final verification shows zero usage

```python
# Delete deprecated endpoint
class UserViewSet(viewsets.ModelViewSet):
    # @deprecated(...)  # Remove decorator
    # @action(detail=False, methods=['get'])
    # def legacy_profile(self, request):
    #     ...
    # DELETE THIS METHOD
```

## Mechanical Enforcement

### Testing

```python
# apps/shared/tests/test_deprecation.py
from django.test import TestCase
from rest_framework.test import APIClient
from apps.users.models import User

class DeprecationHeadersTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='test', password='test')
        self.client.force_authenticate(user=self.user)
    
    def test_deprecated_endpoint_returns_headers(self):
        """Deprecated endpoints return Deprecation and Sunset headers."""
        response = self.client.get('/api/users/legacy_profile/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Deprecation', response)
        self.assertIn('Sunset', response)
        
        # Verify header format
        self.assertTrue(response['Deprecation'].startswith('@'))  # RFC 9745
        self.assertIn('GMT', response['Sunset'])  # RFC 8594
    
    def test_openapi_marks_deprecated(self):
        """OpenAPI schema marks deprecated endpoints."""
        from drf_spectacular.generators import SchemaGenerator
        
        schema = SchemaGenerator().get_schema()
        
        # Check deprecated flag
        operation = schema['paths']['/api/users/legacy_profile/']['get']
        self.assertTrue(operation.get('deprecated'))
        
        # Check description includes migration info
        self.assertIn('DEPRECATED', operation['description'])
        self.assertIn('2025-12-31', operation['description'])
```

### Semgrep Rules

```yaml
# .semgrep/django-deprecation.yml
rules:
  - id: missing-deprecation-replacement
    message: |
      @deprecated decorator should include replacement parameter.
      Example: @deprecated(sunset_date="...", reason="...", replacement="GET /api/v2/...")
      See: docs/adr/django/023-api-deprecation-sunset.md
    pattern: |
      @deprecated(sunset_date=$DATE, reason=$REASON)
    pattern-not: |
      @deprecated(sunset_date=$DATE, reason=$REASON, replacement=$REPLACEMENT)
    languages: [python]
    severity: WARNING
    paths:
      include:
        - "apps/*/views.py"
  
  - id: sunset-date-in-past
    message: |
      Sunset date has passed - remove this deprecated endpoint.
      See: docs/adr/django/023-api-deprecation-sunset.md
    pattern: |
      @deprecated(sunset_date="2024-...", ...)
    languages: [python]
    severity: ERROR
    paths:
      include:
        - "apps/*/views.py"
```

## Consequences

### Positive
- **Clear communication** - Clients see deprecation in OpenAPI docs and headers
- **Tracking** - Logs show which clients need to migrate
- **Coordinated shutdown** - Process ensures no clients broken
- **RFC compliant** - Uses standard Deprecation and Sunset headers

### Negative
- **Manual coordination** - Must contact clients individually
- **Log analysis burden** - Need to parse logs or set up monitoring
- **Decorator overhead** - Extra code on deprecated endpoints

### Mitigations
- **Automated alerts** - Set up monitoring dashboard for deprecated usage
- **Email automation** - Script to email clients based on log analysis
- **Semgrep enforcement** - Catch sunset dates in the past

## Verification Checklist

After implementing this ADR:

- [ ] `apps/shared/deprecation.py` created with `@deprecated` decorator
- [ ] `apps/shared/middleware.py` includes DeprecationLoggingMiddleware
- [ ] MIDDLEWARE setting includes DeprecationLoggingMiddleware
- [ ] Test deprecated endpoint returns `Deprecation` and `Sunset` headers
- [ ] OpenAPI schema marks deprecated endpoints with `deprecated: true`
- [ ] Logs show warning when deprecated endpoint called
- [ ] Semgrep rules catch missing replacement or past sunset dates
- [ ] Process documented for contacting clients before shutdown

## References
- **Implements:** API ADR-008 (API Deprecation and Sunset)
- [RFC 9745: Deprecation HTTP Header](https://www.rfc-editor.org/rfc/rfc9745.html)
- [RFC 8594: Sunset HTTP Header](https://www.rfc-editor.org/rfc/rfc8594.html)
- [drf-spectacular Deprecation](https://drf-spectacular.readthedocs.io/en/latest/customization.html#step-5-deprecation)

## Related Django ADRs
- Django ADR-021: API First Implementation (OpenAPI generation)
- Django ADR-022: HTTP Header Standards (custom headers)
