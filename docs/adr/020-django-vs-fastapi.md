# ADR-020: When to Use Django vs FastAPI

## Status
Proposed

## Context
We have two Python web frameworks in our stack. Without clear guidance, teams choose based on familiarity rather than use case fit. This leads to:
- Django projects that only need simple CRUD endpoints but carry full ORM/admin overhead
- FastAPI services trying to replicate Django's auth/admin features poorly
- Inconsistent architecture across services

Both frameworks are Python, but optimize for different problems:
- **Django**: Batteries-included, convention over configuration, rapid development
- **FastAPI**: Minimal, performance-focused, explicit dependencies

## Decision

**Use Django REST Framework when:**
- Service needs authentication and authorization
- Service needs admin interface for operations team
- Service has complex database relationships (3+ related models)
- Service requires migrations and schema management
- Team needs rapid prototyping with scaffolding

**Use FastAPI when:**
- Service does ONE thing (single responsibility)
- Service is stateless (no auth, no sessions)
- Service needs high throughput (>1000 req/sec per instance)
- Service has simple or no database interaction
- Service is internal-only (other services consume it)

**Never use FastAPI for:**
- User authentication/authorization
- Admin panels
- Complex business logic with many database relationships

**Never use Django for:**
- Simple proxy/transformation services
- High-throughput data pipelines
- Services that don't need a database

## Examples

### Use Django DRF:
```python
# user-service - manages users, auth, permissions
# Complex relationships, needs admin, auth required
class User(models.Model):
    email = models.EmailField(unique=True)
    groups = models.ManyToManyField(Group)
    permissions = models.ManyToManyField(Permission)
```

### Use FastAPI:
```python
# image-resize-service - resizes images, no auth, high volume
@app.post("/resize")
async def resize_image(image: UploadFile, width: int, height: int):
    resized = await resize(image, width, height)
    return {"url": upload_to_s3(resized)}
```

### Wrong Choice - Django:
```python
# Simple image resize doesn't need Django's overhead
# No database, no auth, just transformation
# FastAPI would be 3x faster here
```

### Wrong Choice - FastAPI:
```python
# User management needs Django's auth/admin
# Trying to build this in FastAPI means rebuilding Django
# Just use Django
```

## Consequences

### Positive
- Clear decision criteria prevents bikeshedding
- Django services get admin/auth for free
- FastAPI services stay lightweight and fast
- Each tool used for its strengths

### Negative
- Two frameworks means two sets of patterns to learn
- Inter-service communication requires planning (covered in future ADR)
- Cannot "just pick Python" - must choose which framework

## Questions to Ask

**Before choosing Django:**
1. Does this service need authentication? (Yes → Django likely)
2. Does this service need an admin interface? (Yes → Django)
3. Does this service have >3 related database models? (Yes → Django)

**Before choosing FastAPI:**
1. Is this service doing one focused thing? (Yes → FastAPI likely)
2. Is throughput a primary concern? (Yes → FastAPI)
3. Is this internal-only with no auth? (Yes → FastAPI)

**If answers are mixed:** Default to Django for simplicity, extract FastAPI microservice later if performance becomes an issue.

## Mechanical Enforcement

None - this is architectural guidance for project inception.

Code review checklist:
- [ ] New Django project: Does it need auth/admin/complex DB?
- [ ] New FastAPI project: Is it truly stateless and single-purpose?

## References
- [Language and Framework Choices](../notes/001-language-framework-choices.md)
- Django REST Framework documentation
- FastAPI documentation
