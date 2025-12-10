# ADR-026: Monorepo Git Workflow and Infrastructure

## Status
Active

## Context
We maintain a monorepo containing multiple experimental projects (Django services, FastAPI services, frontends, tools). Projects are explored independently, and successful experiments graduate to production. Developers switch between projects based on workload, requiring clear git workflow and conflict-free local infrastructure.

Without standardized workflow, we face:
- Branch naming chaos (can't find relevant branches)
- Unclear graduation criteria (when does experiment become "real"?)
- Tooling drift (experiments use stale linter rules)
- Port conflicts (multiple projects can't run simultaneously)
- Database conflicts (dropping one project's data affects others)

## Decision

### Git Branch Structure

**Branch naming convention:**
````
exp/{type}-{name}              # Long-lived experiment branches
exp/{branch}/feat/{feature}    # Feature branches off experiments
feat/{project}-{feature}       # Feature branches off main (rare)

Types:
- service/   Backend services
- frontend/  Frontend applications  
- tool/      CLI tools, scripts
- shared/    Shared libraries
- infra/     Infrastructure code

Examples:
- exp/service-users
- exp/frontend-admin
- exp/service-users/feat/add-auth
- feat/users-add-pagination
````

**Main branch:**
- Contains graduated projects only
- Contains `/adr/` documentation
- Contains tooling config (`.ruff.toml`, `.semgrep/`)
- Represents production-ready or staging-deployed code

**Experiment branches:**
- Long-lived branches for projects under development
- Independent from main until proven valuable
- Can be deleted if experiment fails

### Graduation Process

**Experiments graduate to main when they meet ALL criteria:**

1. ✅ **Deploys somewhere** (staging, production, doesn't matter)
2. ✅ **Has tests** (minimum: smoke tests that service starts)
3. ✅ **Passes ADR compliance** (Semgrep/Ruff checks pass)
4. ✅ **Has README** documenting:
   - What the project does
   - How to run it locally
   - Which ADRs apply to it
5. ✅ **Has maintainer** (someone commits to maintaining it)

**Graduation commands:**
````bash
# Merge experiment to main (preserve history)
git checkout main
git merge --no-ff exp/service-images

# Clean up experiment branch
git branch -d exp/service-images

# Document graduation
echo "service-images: Graduated $(date +%Y-%m-%d)" >> PROJECTS.md
````

**Use `--no-ff` (no fast-forward) for:**
- Graduating experiments to main (preserves "this came from exp/")
- NOT for feature branches into experiments (clutters history)

### Tooling Synchronization

**Tooling lives in main:**
````
main/
├── .ruff.toml           # Python linting config
├── .semgrep/            # Security/pattern rules
├── pyproject.toml       # Python dependencies
└── .pre-commit-config.yaml
````

**Weekly synchronization cycle:**

1. **Monday:** Tooling updates pushed to main
2. **Slack notification:** "🔧 New linting rules in main - sync before Friday meeting"
3. **Throughout week:** Developers merge main into experiments
````bash
   git checkout exp/service-images
   git merge main
   # Fix any new violations
   ruff check .
   semgrep --config .semgrep/ .
````
4. **Friday meeting:** Review experiments, decide graduations, deploy to staging

**Enforcement:**
- Slack notifications for rule changes (not enforced by CI during development)
- Violations caught at graduation time (merge to main)
- Weekly meeting creates natural sync checkpoint

### Infrastructure: Docker Compose with Profiles

**Single compose file with project profiles:**
````yaml
# docker/compose.yml
services:
  # Shared infrastructure (always running)
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-dbs.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_PASSWORD: dev
  
  redis:
    image: redis:7
    ports: ["6379:6379"]
    volumes:
      - redis-data:/data
  
  # Project: users service
  users-api:
    profiles: ["users"]
    build: ../service-users
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    environment:
      DATABASE_URL: postgresql://postgres:dev@postgres:5432/users
  
  # Project: images service
  images-api:
    profiles: ["images"]
    build: ../service-images
    ports: ["8001:8000"]
    depends_on: [postgres, redis]
    environment:
      DATABASE_URL: postgresql://postgres:dev@postgres:5432/images
  
  # Project: admin frontend
  admin-frontend:
    profiles: ["admin"]
    build: ../frontend-admin
    ports: ["3000:3000"]

volumes:
  postgres-data:
  redis-data:
````

**Database initialization:**
````sql
-- docker/init-dbs.sql
CREATE DATABASE users;
CREATE DATABASE images;
CREATE DATABASE orders;
````

**Port allocation strategy:**
- **8000-8099:** Django services (users: 8000, orders: 8001, etc.)
- **8100-8199:** FastAPI services (images: 8100, etc.)
- **3000-3099:** Frontend applications (admin: 3000, customer: 3001)
- **5432:** PostgreSQL (one instance, multiple databases)
- **6379:** Redis (one instance, key prefixes per project)

**Usage patterns:**
````bash
# Start shared infrastructure once
docker compose up -d postgres redis

# Work on users project
docker compose --profile users up

# Switch to images project
docker compose --profile users down
docker compose --profile images up

# Run multiple projects simultaneously (no port conflicts)
docker compose --profile users --profile images up

# Drop users database without affecting other projects
docker exec postgres psql -U postgres -c "DROP DATABASE users; CREATE DATABASE users;"
docker compose restart users-api

# Complete teardown
docker compose down -v
````

### Shared Code Management

**When shared code emerges:**

Pattern: When 2nd project needs same utility, extract to main.
````
# First occurrence - stays in project
exp/service-users/utils/jwt.py

# Second occurrence - extract to shared
main/
└── shared-python/
    └── auth/
        └── jwt.py

# Projects depend via:
# pyproject.toml: dependencies = ["../shared-python"]
````

**Shared code lives in main even if only experimental projects consume it.**

## Consequences

### Positive
- **Clear branch purpose:** Naming convention makes it obvious what branches are for
- **No premature commits:** Experiments stay isolated until proven
- **Preserved history:** `--no-ff` merges show graduation events clearly
- **Synchronized tooling:** Weekly cycle prevents massive cleanup at graduation
- **No port conflicts:** Profiles + port ranges allow simultaneous project work
- **Isolated databases:** Drop/reset one project's data without affecting others
- **Simple infrastructure:** One compose file, profiles control what runs
- **Fast context switching:** Developers switch projects with single command

### Negative
- **Weekly discipline required:** Must sync experiments before meeting
- **Merge conflicts possible:** Multiple experiments updating same files
- **Manual graduation:** No automated promotion of experiments
- **Port exhaustion risk:** Must coordinate port assignments across projects
- **Multiple postgres databases:** More resource usage than single database

### Mitigations
- **Slack notifications:** Remind developers to sync before conflicts accumulate
- **ADR numbering blocks:** Reserve number ranges to prevent ADR conflicts (001-099 global, 100-199 Python, etc.)
- **Port range documentation:** Document assigned ranges in this ADR
- **Graduation checklist:** Clear criteria prevent bikeshedding about promotion
- **Compose profiles:** Start/stop projects independently prevents resource waste

## Mechanical Enforcement

### Pre-commit Hooks
````yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: branch-naming
        name: Check branch naming convention
        entry: scripts/check-branch-name.sh
        language: system
        pass_filenames: false
        stages: [commit]
````
````bash
# scripts/check-branch-name.sh
#!/bin/bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$BRANCH" == "main" ]]; then
  exit 0
fi

if [[ "$BRANCH" =~ ^exp/(service|frontend|tool|shared|infra)- ]]; then
  exit 0
fi

if [[ "$BRANCH" =~ ^exp/.+/feat/ ]]; then
  exit 0
fi

if [[ "$BRANCH" =~ ^feat/[a-z]+-[a-z-]+ ]]; then
  exit 0
fi

echo "❌ Branch name must match convention:"
echo "  exp/{type}-{name}"
echo "  exp/{branch}/feat/{feature}"
echo "  feat/{project}-{feature}"
echo ""
echo "Current branch: $BRANCH"
exit 1
````

### Graduation Checklist Script
````bash
# scripts/check-graduation.sh
#!/bin/bash
PROJECT=$1

echo "Checking graduation criteria for $PROJECT..."

# Check README exists
if [ ! -f "$PROJECT/README.md" ]; then
  echo "❌ Missing README.md"
  exit 1
fi

# Check tests exist
if ! find "$PROJECT" -name "*test*.py" | grep -q .; then
  echo "❌ No test files found"
  exit 1
fi

# Check Semgrep compliance
if ! semgrep --config .semgrep/ "$PROJECT" --error; then
  echo "❌ Semgrep violations found"
  exit 1
fi

# Check Ruff compliance
if ! ruff check "$PROJECT"; then
  echo "❌ Ruff violations found"
  exit 1
fi

echo "✅ All graduation criteria met"
````

## Implementation Guide

### Starting New Experiment
````bash
# Create experiment branch
git checkout main
git checkout -b exp/service-notifications

# Create project structure
mkdir service-notifications
cd service-notifications

# Create README
cat > README.md << 'EOF'
# Service: Notifications

## What
Sends email/SMS notifications.

## How to Run
```bash
docker compose --profile notifications up
```

## ADRs
- 001-006: Python style
- 020-025: Django patterns
EOF

# Start coding
````

### Weekly Sync Routine
````bash
# Before Friday meeting
git checkout exp/service-notifications
git merge main

# Fix any violations
ruff check .
semgrep --config .semgrep/ .

# Commit fixes
git add .
git commit -m "Sync with main tooling updates"
````

### Graduating Experiment
````bash
# Run graduation checks
./scripts/check-graduation.sh service-notifications

# Merge to main
git checkout main
git merge --no-ff exp/service-notifications

# Update project registry
echo "service-notifications: Graduated $(date +%Y-%m-%d)" >> PROJECTS.md
git add PROJECTS.md
git commit -m "docs: Graduate service-notifications"

# Clean up
git branch -d exp/service-notifications
````

### Infrastructure Setup
````bash
# First time setup
cd docker
docker compose up -d postgres redis

# Work on project
docker compose --profile users up

# Reset project database
docker exec postgres psql -U postgres -c "DROP DATABASE users; CREATE DATABASE users;"
docker compose restart users-api
````

## References
- Docker Compose Profiles: https://docs.docker.com/compose/profiles/
- Git Merge Strategies: https://git-scm.com/docs/git-merge

## Related ADRs
- ADR-001 through ADR-006: Python coding standards
- ADR-020: Django vs FastAPI framework selection
- ADR-021: API First with OpenAPI generation