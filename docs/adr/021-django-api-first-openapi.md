# Django ADR-021: API First Implementation with OpenAPI

## Status
Proposed

## Context
**Implements:** API ADR-009 (Follow API First Principle)

API ADR-009 requires:
- OpenAPI specification before implementation
- Self-contained specs (no remote references)
- OpenAPI 3.1 (JSON Schema compliant)
- Version control for specs
- Automated validation

**Django challenge:** Django is code-first by nature. Writing YAML specs manually creates maintenance burden (spec drift from code).

**Solution:** Generate OpenAPI from code using drf-spectacular, enforce documentation discipline through docstrings and automated validation.

## Decision

**Use drf-spectacular to auto-generate OpenAPI 3.1 from Django REST Framework code with docstring-based documentation.**

### Installation

```bash
pip install drf-spectacular
```

### Configuration

```python
# config/settings/openapi.py
import os

INSTALLED_APPS = [
    'drf_spectacular',
    # ... other apps
]

SPECTACULAR_SETTINGS = {
    # OpenAPI 3.1 (JSON Schema compliant)
    'OAS_VERSION': '3.1.0',
    
    # API Meta Information (implements API ADR-015)
    'TITLE': os.getenv('API_TITLE', 'My Project API'),
    'DESCRIPTION': os.getenv('API_DESCRIPTION', 'API for My Project'),
    'VERSION': os.getenv('API_VERSION', '1.0.0'),
    'CONTACT': {
        'name': os.getenv('API_CONTACT_NAME', 'API Team'),
        'email': os.getenv('API_CONTACT_EMAIL', 'api@example.com'),
        'url': os.getenv('API_CONTACT_URL', 'https://example.com'),
    },
    
    # API Identifier (generate once: python -c "import uuid; print(uuid.uuid4())")
    'EXTENSIONS_INFO': {
        'x-api-id': os.getenv('API_ID'),  # Required: UUID
        'x-audience': os.getenv('API_AUDIENCE', 'company-internal'),
    },
    
    # Schema generation
    'SCHEMA_PATH_PREFIX': '/api/',
    'SERVE_PUBLIC': True,
    
    # Swagger UI Configuration
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    
    # Self-contained spec (no remote references)
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}
```

```python
# config/settings/rest_framework.py
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # ... other DRF settings
}
```

```python
# config/settings/security.py
SPECTACULAR_SETTINGS = {
    # Security schemes (JWT Bearer from base Django setup)
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
    'SECURITY': [{'BearerAuth': []}],
}
```

### URL Configuration

```python
# config/urls.py
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # OpenAPI schema (machine-readable)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI (human-readable documentation)
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API endpoints
    path('api/', include('apps.users.urls')),
]
```

### Environment Variables

```bash
# .env.example
# Generate API_ID once and commit to repository (it's not a secret)
API_ID=550e8400-e29b-41d4-a716-446655440000
API_TITLE=My Project API
API_VERSION=1.0.0
API_DESCRIPTION=RESTful API for My Project
API_AUDIENCE=company-internal
API_CONTACT_NAME=Backend Team
API_CONTACT_EMAIL=backend@example.com
API_CONTACT_URL=https://example.com/team
```

## Documentation Pattern: Docstrings

**drf-spectacular automatically extracts OpenAPI documentation from Python docstrings.**

### ViewSet Documentation

```python
# apps/users/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    User management endpoints.
    
    list: Retrieve paginated list of all users
    retrieve: Get a single user by ID
    create: Create a new user account
    update: Replace user details completely
    partial_update: Update specific user fields
    destroy: Delete user account
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get authenticated user profile.
        
        Returns the profile information for the currently
        authenticated user based on JWT token.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
```

**Docstring format:**
- First line: Brief summary (becomes OpenAPI `summary`)
- After blank line: Detailed description (becomes OpenAPI `description`)
- For ViewSets: Use `action: description` format for standard CRUD operations

### Serializer Documentation

```python
# apps/users/serializers.py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """User data representation."""
    
    full_name = serializers.SerializerMethodField(
        help_text="User's full name (first + last)"
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'email': {'help_text': 'User email address (unique)'},
            'username': {'help_text': 'Unique username for authentication'},
            'first_name': {'help_text': "User's first name"},
            'last_name': {'help_text': "User's last name"},
        }
    
    def get_full_name(self, obj):
        """Combine first and last name."""
        return f"{obj.first_name} {obj.last_name}".strip()
```

**help_text on fields becomes OpenAPI schema field descriptions.**

## Mechanical Enforcement

### Semgrep Rules

```yaml
# .semgrep/django-openapi.yml
rules:
  - id: viewset-missing-class-docstring
    message: |
      ViewSet must have docstring with action descriptions.
      Format:
        """
        <Summary>
        
        list: <description>
        retrieve: <description>
        create: <description>
        """
      See: docs/adr/django/021-api-first-openapi.md
    pattern: |
      class $CLASS(viewsets.$VIEWSET):
          ...
    pattern-not: |
      class $CLASS(viewsets.$VIEWSET):
          """..."""
          ...
    languages: [python]
    severity: ERROR
    paths:
      include:
        - "apps/*/views.py"
    
  - id: action-missing-docstring
    message: |
      Custom @action must have docstring for OpenAPI generation.
      See: docs/adr/django/021-api-first-openapi.md
    pattern: |
      @action(...)
      def $METHOD(self, request):
          ...
    pattern-not: |
      @action(...)
      def $METHOD(self, request):
          """..."""
          ...
    languages: [python]
    severity: ERROR
    paths:
      include:
        - "apps/*/views.py"
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: openapi-validation
        name: Validate OpenAPI schema generation
        entry: python manage.py spectacular --validate --fail-on-warn
        language: system
        pass_filenames: false
      
      - id: semgrep-openapi
        name: Check ViewSet docstrings
        entry: semgrep --config .semgrep/django-openapi.yml
        language: system
        pass_filenames: false
```

### Automated Testing

```python
# apps/shared/tests/test_openapi_compliance.py
from django.test import TestCase
from drf_spectacular.generators import SchemaGenerator

class OpenAPIComplianceTest(TestCase):
    """Verify OpenAPI schema meets ADR requirements."""
    
    def test_schema_generation_succeeds(self):
        """OpenAPI schema can be generated without errors."""
        generator = SchemaGenerator()
        schema = generator.get_schema()
        
        self.assertIsNotNone(schema)
        self.assertEqual(schema['openapi'], '3.1.0')
    
    def test_required_meta_information(self):
        """Schema includes required API meta information (API ADR-015)."""
        generator = SchemaGenerator()
        schema = generator.get_schema()
        info = schema['info']
        
        # Required fields
        self.assertIn('title', info)
        self.assertIn('version', info)
        self.assertIn('contact', info)
        self.assertIn('x-api-id', info)
        self.assertIn('x-audience', info)
        
        # x-api-id must be UUID
        import uuid
        try:
            uuid.UUID(info['x-api-id'])
        except ValueError:
            self.fail('x-api-id must be a valid UUID')
    
    def test_security_scheme_defined(self):
        """Schema includes JWT Bearer authentication."""
        generator = SchemaGenerator()
        schema = generator.get_schema()
        
        self.assertIn('components', schema)
        self.assertIn('securitySchemes', schema['components'])
        self.assertIn('BearerAuth', schema['components']['securitySchemes'])
        
        bearer_auth = schema['components']['securitySchemes']['BearerAuth']
        self.assertEqual(bearer_auth['type'], 'http')
        self.assertEqual(bearer_auth['scheme'], 'bearer')
    
    def test_all_endpoints_have_summary(self):
        """Every endpoint must have summary (from docstring)."""
        generator = SchemaGenerator()
        schema = generator.get_schema()
        
        for path, methods in schema['paths'].items():
            for method, operation in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    self.assertIn('summary', operation,
                        f"{method.upper()} {path} missing summary - add ViewSet docstring"
                    )
```

### CI/CD Schema Publishing

```yaml
# .github/workflows/ci.yml (or similar)
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          python manage.py test
      
      - name: Generate OpenAPI schema
        run: |
          python manage.py spectacular --file openapi-schema.yaml
      
      - name: Validate OpenAPI schema
        run: |
          python manage.py spectacular --validate --fail-on-warn
      
      - name: Upload schema artifact
        uses: actions/upload-artifact@v3
        with:
          name: openapi-schema
          path: openapi-schema.yaml
```

## Integration with Existing Docstring Rules

**This ADR extends existing Python docstring rules (ADR-002):**

| Applies To | Rule | Format |
|------------|------|--------|
| Regular functions | ADR-002 | Google-style (Args/Returns/Raises) |
| ViewSet classes | ADR-021 | Action descriptions |
| ViewSet methods | ADR-021 | Summary + description |

**No conflicts:** Different patterns for different contexts.

## Consequences

### Positive
- **Single source of truth** - Code generates OpenAPI, no YAML maintenance
- **Discipline enforced** - Semgrep + pre-commit catch missing docs
- **Interactive documentation** - Swagger UI for manual testing
- **Client code generation** - OpenAPI spec enables TypeScript/Python client generation
- **No decorator overhead** - Just docstrings, no 50-line @extend_schema decorators
- **Automated validation** - CI/CD catches schema generation errors

### Negative
- **Not pure API-first** - Code exists before spec (inverted from ADR-009 intent)
- **Docstring discipline required** - Team must write comprehensive docstrings
- **Learning curve** - Team needs to understand docstring → OpenAPI mapping

### Mitigations
- **Pre-commit enforcement** - Catches missing docstrings before commit
- **Automated tests** - Verify every endpoint documented
- **CI/CD validation** - Schema generation must succeed in pipeline
- **Documentation** - This ADR explains pattern clearly

## Verification Checklist

After implementing this ADR:

- [ ] `pip install drf-spectacular` completed
- [ ] `config/settings/openapi.py` configured
- [ ] `API_ID` environment variable generated (UUID)
- [ ] `/api/schema/` endpoint returns OpenAPI 3.1 spec
- [ ] `/api/docs/` endpoint shows Swagger UI
- [ ] All ViewSets have class docstrings
- [ ] All custom @actions have method docstrings
- [ ] Semgrep rules added to `.semgrep/django-openapi.yml`
- [ ] Pre-commit hooks configured
- [ ] Tests in `apps/shared/tests/test_openapi_compliance.py` pass
- [ ] CI/CD pipeline generates and validates schema

## References
- **Implements:** API ADR-009 (API First Principle), API ADR-015 (API Meta Information)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [OpenAPI 3.1 Specification](https://spec.openapis.org/oas/v3.1.0)

## Related Django ADRs
- Django ADR-002: Docstring Required Sections (Google-style for functions)
- Django ADR-022: HTTP Header Standards (X-Flow-ID middleware)
- Django ADR-023: API Security (JWT authentication setup)
