# Horse Betting Analytics Platform - Complete Guide
## From Zero Knowledge to Full Platform

This spec assumes you know NOTHING about horse racing and have NO data.

---

## Part 1: What You're Building

A platform that helps people make data-driven horse betting decisions by:
1. Analyzing historical race performance
2. Tracking live odds movements
3. Identifying value betting opportunities
4. Managing betting strategies and ROI

**Think:** Analytics dashboard for horse racing (like Bloomberg Terminal for stocks)

---

## Part 2: Jargon Dictionary

See `/tmp/horse-betting-platform-spec.md` Part 1 for complete jargon explanations.

**Key terms quick reference:**
- **Race** = Competition where horses run
- **Track** = Location where races happen (Belmont Park, Churchill Downs, etc.)
- **Jockey** = Person riding horse (skill matters enormously)
- **Trainer** = Coach who prepares horse
- **Post Position** = Starting gate position (inside vs outside)
- **Odds** = Payout ratio (5:1 = bet $1, win $5)
- **Win/Place/Show** = Simple bets (1st / top-2 / top-3)
- **Exacta/Trifecta/Quinté** = Exotic bets (pick multiple horses in order)
- **Pari-mutuel** = Pool betting system (winners split pot)

---

## Part 3: Progressive Milestones

We build features gradually, learning domain knowledge as we go.

---

# Milestone 0: Data Foundation
**Duration:** Week 1-2
**Complexity:** Low
**Goal:** Load historical data into database

## What You'll Learn
- How race data is structured
- Entity relationships (races → entries → horses → jockeys → trainers)
- Data quality challenges (nulls, duplicates, inconsistencies)

## Step 1: Get Data

**Recommended: Kaggle "Horse Racing Dataset"**
- 50,000+ historical races (2005-2020)
- Major US tracks (Belmont, Churchill, Santa Anita, etc.)
- Free download
- CSV format (easy to work with)

**Data files you'll get:**
```
races.csv           - Race details (date, track, distance, surface)
entries.csv         - Which horses ran in which races
horses.csv          - Horse profiles (age, sex, sire/dam)
jockeys.csv         - Jockey profiles
trainers.csv        - Trainer profiles
results.csv         - Race outcomes (winner, finish order, payouts)
```

## Step 2: Database Schema

**Django models:**

```python
# apps/races/models.py

class Track(models.Model):
    """Physical racing location."""
    name = models.CharField(max_length=100)  # "Belmont Park"
    location = models.CharField(max_length=100)  # "New York, NY"
    surface_types = models.JSONField()  # ["dirt", "turf"]
    
class Horse(models.Model):
    """Individual racing horse."""
    name = models.CharField(max_length=100)
    birth_year = models.IntegerField()
    sex = models.CharField(max_length=10)  # "colt", "filly", "gelding", "mare"
    sire = models.ForeignKey('self', null=True, related_name='offspring_as_sire')
    dam = models.ForeignKey('self', null=True, related_name='offspring_as_dam')

class Jockey(models.Model):
    """Horse rider."""
    name = models.CharField(max_length=100)
    # Career stats computed from race results

class Trainer(models.Model):
    """Horse coach."""
    name = models.CharField(max_length=100)
    # Career stats computed from race results

class Race(models.Model):
    """Single race event."""
    date = models.DateField()
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    race_number = models.IntegerField()  # 1-12 (which race of the day)
    distance_furlongs = models.DecimalField(max_digits=4, decimal_places=2)
    surface = models.CharField(max_length=20)  # "dirt", "turf", "synthetic"
    track_condition = models.CharField(max_length=20)  # "fast", "muddy", etc.
    purse = models.DecimalField(max_digits=10, decimal_places=2)
    race_type = models.CharField(max_length=50)  # "claiming", "allowance", "stakes"

class RaceEntry(models.Model):
    """Horse entered in a specific race."""
    race = models.ForeignKey(Race, related_name='entries')
    horse = models.ForeignKey(Horse)
    jockey = models.ForeignKey(Jockey)
    trainer = models.ForeignKey(Trainer)
    post_position = models.IntegerField()  # 1-12
    morning_line_odds = models.CharField(max_length=10)  # "5:1", "3:2", etc.
    
    # Results (null until race completes)
    finish_position = models.IntegerField(null=True)  # 1st, 2nd, 3rd, etc.
    win_payout = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    place_payout = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    show_payout = models.DecimalField(null=True, max_digits=10, decimal_places=2)
```

## Step 3: Data Loading Script

```python
# management/commands/load_kaggle_data.py

import csv
from django.core.management.base import BaseCommand
from apps.races.models import Track, Horse, Jockey, Trainer, Race, RaceEntry

class Command(BaseCommand):
    help = 'Load Kaggle horse racing dataset'
    
    def handle(self, *args, **options):
        # Load tracks
        tracks = {}
        with open('data/tracks.csv') as f:
            for row in csv.DictReader(f):
                track = Track.objects.create(
                    name=row['track_name'],
                    location=row['location']
                )
                tracks[row['track_name']] = track
        
        # Load horses
        horses = {}
        with open('data/horses.csv') as f:
            for row in csv.DictReader(f):
                horse = Horse.objects.create(
                    name=row['horse_name'],
                    birth_year=int(row['birth_year']),
                    sex=row['sex']
                )
                horses[row['horse_name']] = horse
        
        # Load jockeys, trainers (similar pattern)
        
        # Load races
        with open('data/races.csv') as f:
            for row in csv.DictReader(f):
                race = Race.objects.create(
                    date=row['date'],
                    track=tracks[row['track_name']],
                    race_number=int(row['race_number']),
                    distance_furlongs=Decimal(row['distance']),
                    surface=row['surface'],
                    track_condition=row['condition'],
                    purse=Decimal(row['purse'])
                )
        
        # Load race entries with results
        with open('data/entries.csv') as f:
            for row in csv.DictReader(f):
                RaceEntry.objects.create(
                    race_id=row['race_id'],
                    horse=horses[row['horse_name']],
                    jockey=jockeys[row['jockey_name']],
                    trainer=trainers[row['trainer_name']],
                    post_position=int(row['post']),
                    morning_line_odds=row['odds'],
                    finish_position=int(row['finish']) if row['finish'] else None,
                    win_payout=Decimal(row['win_payout']) if row['win_payout'] else None
                )
        
        self.stdout.write(self.style.SUCCESS('Data loaded successfully'))
```

## Step 4: Data Quality Checks

```python
# Check for issues
print(f"Races with no entries: {Race.objects.filter(entries__isnull=True).count()}")
print(f"Entries with no results: {RaceEntry.objects.filter(finish_position__isnull=True).count()}")
print(f"Duplicate horse names: {Horse.objects.values('name').annotate(count=Count('id')).filter(count__gt=1).count()}")
```

**Common issues you'll find:**
- Missing results for some races (race was cancelled/postponed)
- Duplicate horse names (different horses, same name)
- Null jockey/trainer (data missing from source)
- Invalid odds formats ("SCRATCHED", "EVEN", etc.)

## Deliverables

✅ PostgreSQL database with schema
✅ 50,000 historical races loaded
✅ Django admin interface to browse data
✅ Data quality report identifying issues

---

# Milestone 1: Historical Analytics (MVP)
**Duration:** Week 3-4
**Complexity:** Medium
**Goal:** Query historical data, calculate basic stats, manual bet tracking

## What You'll Learn
- Calculating win rates, ROI
- Django ORM queries for analytics
- Understanding what makes a good bet

## Features

### Feature 1.1: Horse Performance Stats

**Endpoint:** `GET /api/horses/{horse-id}/stats`

**Response:**
```json
{
  "horse_id": 123,
  "name": "Thunder Bolt",
  "overall_record": {
    "starts": 25,
    "wins": 7,
    "places": 12,
    "shows": 18,
    "win_rate": 0.28,
    "place_rate": 0.48,
    "show_rate": 0.72
  },
  "by_surface": {
    "dirt": {"starts": 20, "wins": 6, "win_rate": 0.30},
    "turf": {"starts": 5, "wins": 1, "win_rate": 0.20}
  },
  "by_distance": {
    "sprint_5_7f": {"starts": 15, "wins": 5, "win_rate": 0.33},
    "route_8_10f": {"starts": 10, "wins": 2, "win_rate": 0.20}
  },
  "by_track": {
    "Belmont Park": {"starts": 10, "wins": 4, "win_rate": 0.40},
    "Churchill Downs": {"starts": 8, "wins": 2, "win_rate": 0.25}
  },
  "recent_form": [
    {"date": "2024-11-15", "track": "Belmont", "finish": 1},
    {"date": "2024-10-20", "track": "Aqueduct", "finish": 3},
    {"date": "2024-09-18", "track": "Belmont", "finish": 1}
  ]
}
```

**Implementation:**
```python
# apps/races/selectors.py

def get_horse_stats(horse_id: int) -> dict:
    """Calculate performance statistics for a horse."""
    entries = RaceEntry.objects.filter(
        horse_id=horse_id,
        finish_position__isnull=False  # Only completed races
    ).select_related('race', 'race__track')
    
    total_starts = entries.count()
    wins = entries.filter(finish_position=1).count()
    places = entries.filter(finish_position__lte=2).count()
    shows = entries.filter(finish_position__lte=3).count()
    
    # By surface
    dirt_entries = entries.filter(race__surface='dirt')
    dirt_wins = dirt_entries.filter(finish_position=1).count()
    
    # By distance
    sprint_entries = entries.filter(race__distance_furlongs__lt=8)
    sprint_wins = sprint_entries.filter(finish_position=1).count()
    
    # By track
    track_stats = entries.values('race__track__name').annotate(
        starts=Count('id'),
        wins=Count('id', filter=Q(finish_position=1))
    )
    
    return {
        "overall_record": {
            "starts": total_starts,
            "wins": wins,
            "win_rate": wins / total_starts if total_starts > 0 else 0,
            # ... more stats
        },
        # ... by_surface, by_distance, by_track
    }
```

### Feature 1.2: Jockey Performance Stats

**Endpoint:** `GET /api/jockeys/{jockey-id}/stats`

Similar structure to horse stats, but includes:
- Performance by track
- Performance when riding favorites vs longshots
- Success rate with specific trainers (partnerships)

### Feature 1.3: Manual Bet Tracking

**Models:**
```python
# apps/bets/models.py

class Bet(models.Model):
    """User's bet record."""
    BET_TYPES = [
        ('win', 'Win'),
        ('place', 'Place'),
        ('show', 'Show'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    race_entry = models.ForeignKey(RaceEntry, on_delete=models.CASCADE)
    bet_type = models.CharField(max_length=10, choices=BET_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    odds_at_bet = models.CharField(max_length=10)  # "5:1"
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payout = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

**Endpoints:**
```
POST /api/bets              # Record new bet
GET /api/bets               # List user's bets (paginated)
GET /api/bets/{id}          # Bet details
PATCH /api/bets/{id}        # Update status after race
GET /api/portfolio/summary  # Overall stats
```

**Portfolio calculation:**
```python
# apps/bets/selectors.py

def get_portfolio_summary(user_id: int) -> dict:
    """Calculate user's betting performance."""
    bets = Bet.objects.filter(user_id=user_id)
    
    total_wagered = bets.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    total_returned = bets.filter(status='won').aggregate(Sum('payout'))['payout__sum'] or Decimal('0')
    
    wins = bets.filter(status='won').count()
    losses = bets.filter(status='lost').count()
    total = wins + losses
    
    roi = ((total_returned - total_wagered) / total_wagered * 100) if total_wagered > 0 else 0
    
    return {
        "total_bets": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total if total > 0 else 0,
        "total_wagered": float(total_wagered),
        "total_returned": float(total_returned),
        "profit_loss": float(total_returned - total_wagered),
        "roi_percentage": float(roi)
    }
```

## ADRs Tested

✅ **ADR-016: Pagination** - Cursor pagination for 50k races
✅ **ADR-019: URL Design** - `/api/horses/{id}/stats`, `/api/bets`
✅ **ADR-014: JSON Standards** - snake_case, Money as decimal
✅ **ADR-007: Standard Formats** - Dates, decimals
✅ **ADR-012: HTTP Status Codes** - 200, 201, 404
✅ **ADR-021: OpenAPI** - drf-spectacular docs
✅ **ADR-022: Headers** - X-Flow-ID middleware

## Deliverables

✅ Horse/jockey/trainer stats endpoints
✅ Manual bet tracking CRUD
✅ Portfolio summary calculations
✅ Django admin for data management
✅ OpenAPI spec generated
✅ Cursor pagination working on large datasets

---

# Milestone 2: Live Race Cards
**Duration:** Week 5-6
**Complexity:** Medium
**Goal:** Scrape today's upcoming races from track websites

## What You'll Learn
- Web scraping basics
- HTML parsing with BeautifulSoup
- Handling anti-bot measures
- Data normalization (different sites format differently)

## Feature 2.1: Race Card Scraper

**Target sites:**
- Equibase.com (official source, has free race cards)
- Track websites (Belmont, Churchill, etc. publish daily cards)

**What to scrape:**
```
Today's races at Belmont Park:

Race 1 - 12:00 PM - 6 furlongs - Dirt - $50k purse
  Post 1: Thunder Bolt (J. Smith / M. Johnson) - ML 3:1
  Post 2: Quick Step (A. Garcia / P. Williams) - ML 5:1
  ...

Race 2 - 12:30 PM - 1 mile - Turf - $75k purse
  ...
```

**Scraper implementation:**
```python
# apps/scraping/scrapers/equibase.py

import requests
from bs4 import BeautifulSoup
from datetime import date

def scrape_race_cards(track_code: str, race_date: date) -> list[dict]:
    """
    Scrape race cards from Equibase.
    
    Args:
        track_code: 3-letter track code (e.g., 'BEL' for Belmont)
        race_date: Date to scrape
    
    Returns:
        List of race dictionaries with entries
    """
    url = f"https://www.equibase.com/static/entry/{track_code}/EQB{race_date:%Y%m%d}{track_code}.html"
    
    response = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; RacingAnalytics/1.0)'
    })
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch race card: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    races = []
    for race_div in soup.find_all('div', class_='race'):
        race_num = int(race_div.find('span', class_='race-number').text)
        distance = race_div.find('span', class_='distance').text
        surface = race_div.find('span', class_='surface').text
        
        entries = []
        for entry_row in race_div.find_all('tr', class_='entry'):
            post = int(entry_row.find('td', class_='post').text)
            horse_name = entry_row.find('td', class_='horse').text.strip()
            jockey_name = entry_row.find('td', class_='jockey').text.strip()
            trainer_name = entry_row.find('td', class_='trainer').text.strip()
            ml_odds = entry_row.find('td', class_='ml-odds').text.strip()
            
            entries.append({
                'post_position': post,
                'horse_name': horse_name,
                'jockey_name': jockey_name,
                'trainer_name': trainer_name,
                'morning_line_odds': ml_odds
            })
        
        races.append({
            'race_number': race_num,
            'distance': distance,
            'surface': surface,
            'entries': entries
        })
    
    return races
```

**Celery task (runs daily):**
```python
# apps/scraping/tasks.py

from celery import shared_task
from datetime import date
from apps.races.models import Race, RaceEntry
from apps.scraping.scrapers.equibase import scrape_race_cards

@shared_task
def fetch_daily_race_cards():
    """
    Fetch today's race cards for all major tracks.
    Runs daily at 6 AM.
    """
    tracks = ['BEL', 'CD', 'SA', 'DMR', 'AQU']  # Track codes
    today = date.today()
    
    for track_code in tracks:
        try:
            races = scrape_race_cards(track_code, today)
            
            for race_data in races:
                # Create or update race
                race, _ = Race.objects.update_or_create(
                    track_code=track_code,
                    date=today,
                    race_number=race_data['race_number'],
                    defaults={
                        'distance_furlongs': parse_distance(race_data['distance']),
                        'surface': race_data['surface']
                    }
                )
                
                # Create entries
                for entry_data in race_data['entries']:
                    # Get or create horse/jockey/trainer
                    horse, _ = Horse.objects.get_or_create(name=entry_data['horse_name'])
                    jockey, _ = Jockey.objects.get_or_create(name=entry_data['jockey_name'])
                    trainer, _ = Trainer.objects.get_or_create(name=entry_data['trainer_name'])
                    
                    RaceEntry.objects.create(
                        race=race,
                        horse=horse,
                        jockey=jockey,
                        trainer=trainer,
                        post_position=entry_data['post_position'],
                        morning_line_odds=entry_data['morning_line_odds']
                    )
            
            print(f"✅ Fetched {len(races)} races for {track_code}")
        
        except Exception as e:
            print(f"âŒ Failed to fetch {track_code}: {e}")
```

## Feature 2.2: Today's Races API

**Endpoints:**
```
GET /api/tracks                    # List all tracks
GET /api/tracks/{code}/today       # Today's races at track
GET /api/races/{race-id}/entries   # Entries for specific race
```

**Response:**
```json
{
  "track": "Belmont Park",
  "date": "2024-12-07",
  "races": [
    {
      "race_number": 1,
      "post_time": "12:00:00",
      "distance_furlongs": 6.0,
      "surface": "dirt",
      "purse": "50000.00",
      "entries_count": 8,
      "url": "/api/races/12345/entries"
    },
    {
      "race_number": 2,
      "post_time": "12:30:00",
      "distance_furlongs": 8.0,
      "surface": "turf",
      "purse": "75000.00",
      "entries_count": 10,
      "url": "/api/races/12346/entries"
    }
  ]
}
```

## Scraping Challenges

**Challenge 1: Anti-bot measures**
```python
# Solution: Rotate user agents, add delays
import time
import random

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...',
]

def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers={
                'User-Agent': random.choice(USER_AGENTS)
            }, timeout=10)
            
            if response.status_code == 200:
                return response
            
            # Rate limit hit, back off
            time.sleep(2 ** attempt)  # Exponential backoff
        
        except requests.Timeout:
            continue
    
    raise Exception("Max retries exceeded")
```

**Challenge 2: HTML structure changes**
```python
# Solution: Multiple selectors, fallbacks
def safe_find(soup, selectors):
    """Try multiple CSS selectors until one works."""
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return element
    return None

# Usage
horse_name = safe_find(soup, [
    'td.horse-name',
    'td.horse',
    'span[class*="horse"]'
])
```

**Challenge 3: Data normalization**
```python
# Different sites format odds differently
def parse_odds(odds_str: str) -> str:
    """
    Normalize odds from various formats.
    
    Input examples:
      "5-1", "5:1", "5/1" → "5:1"
      "3-2", "3:2" → "3:2"
      "EVEN" → "1:1"
      "SCRATCHED" → None
    """
    odds_str = odds_str.strip().upper()
    
    if odds_str in ['SCRATCHED', 'SCR', '-']:
        return None
    if odds_str in ['EVEN', 'EVN']:
        return '1:1'
    
    # Normalize separators
    odds_str = odds_str.replace('-', ':').replace('/', ':')
    
    return odds_str
```

## ADRs Tested

✅ **ADR-011: HTTP Methods** - GET for race cards
✅ **Background jobs** - Celery scheduled scraping
✅ **Error handling** - Retry logic, graceful failures

## Deliverables

✅ Race card scraper for 5 major tracks
✅ Celery task scheduled daily at 6 AM
✅ API endpoints for today's races
✅ Data normalization handling edge cases
✅ Scraper health monitoring (success/failure tracking)

---

# Milestone 3: Live Odds Tracking
**Duration:** Week 7-9
**Complexity:** High
**Goal:** Track real-time odds changes, detect value bets, send alerts

## What You'll Learn
- High-throughput data ingestion
- Redis caching patterns
- FastAPI for performance-critical services
- WebSocket streaming (premium feature)
- Rate limiting by user tier

## Architecture

**Django (existing):** User management, race data, bet tracking
**FastAPI (new):** High-throughput odds ingestion, real-time streaming
**Redis (new):** Fast cache for latest odds, rate limiting

**Data flow:**
```
Scraper (every 30 sec) → FastAPI ingestion endpoint → Redis (latest odds)
                                                    → PostgreSQL (historical odds)

User request → Django API → Redis (fast lookup) → Return odds

Premium users → FastAPI WebSocket → Stream real-time updates
```

## Feature 3.1: Odds Scraper

**Scrape from betting sites (TVG, TwinSpires, etc.):**

```python
# apps/scraping/scrapers/odds.py

def scrape_live_odds(race_id: int) -> list[dict]:
    """
    Scrape current odds for all horses in race.
    
    Returns:
        [
            {"post_position": 1, "odds": "5:1"},
            {"post_position": 2, "odds": "3:1"},
            ...
        ]
    """
    # Implementation similar to race card scraper
    # But runs every 30-60 seconds instead of daily
```

**Celery task (runs continuously):**
```python
# apps/scraping/tasks.py

@shared_task
def fetch_live_odds():
    """
    Fetch current odds for all races happening soon.
    Runs every 30 seconds.
    """
    upcoming_races = Race.objects.filter(
        date=date.today(),
        post_time__gt=timezone.now(),
        post_time__lt=timezone.now() + timedelta(hours=2)
    )
    
    odds_batch = []
    for race in upcoming_races:
        try:
            odds = scrape_live_odds(race.id)
            odds_batch.append({
                'race_id': race.id,
                'timestamp': timezone.now().isoformat(),
                'odds': odds
            })
        except Exception as e:
            print(f"Failed to scrape race {race.id}: {e}")
    
    # Send batch to FastAPI ingestion service
    requests.post('http://fastapi-service:8000/ingest/odds', json=odds_batch)
```

## Feature 3.2: FastAPI Odds Ingestion Service

```python
# fastapi_services/ingestion/main.py

from fastapi import FastAPI
from redis import Redis
from sqlalchemy.orm import Session

app = FastAPI()
redis_client = Redis(host='redis', port=6379, db=0)

@app.post("/ingest/odds")
async def ingest_odds(odds_batch: list[OddsUpdate]):
    """
    High-throughput endpoint to receive odds updates.
    
    Handles 1000s of updates per minute.
    Stores in Redis for fast API access.
    Bulk inserts to PostgreSQL for history.
    """
    # Store latest odds in Redis (fast!)
    for update in odds_batch:
        race_key = f"race:{update.race_id}:odds"
        redis_client.set(race_key, update.json(), ex=3600)  # Expire after 1 hour
    
    # Bulk insert to PostgreSQL (historical record)
    await bulk_insert_odds_history(odds_batch)
    
    # Check for significant changes (alert triggers)
    await check_odds_movements(odds_batch)
    
    return {"status": "ingested", "count": len(odds_batch)}


async def check_odds_movements(odds_batch: list[OddsUpdate]):
    """
    Detect significant odds changes and trigger alerts.
    
    Example: Horse drops from 10:1 to 4:1 in 5 minutes
    """
    for update in odds_batch:
        for horse_odds in update.odds:
            # Get previous odds from Redis
            prev_key = f"race:{update.race_id}:post:{horse_odds.post}:prev_odds"
            prev_odds = redis_client.get(prev_key)
            
            if prev_odds:
                prev_decimal = odds_to_decimal(prev_odds.decode())
                curr_decimal = odds_to_decimal(horse_odds.odds)
                
                # Check for 30%+ change
                if abs(curr_decimal - prev_decimal) / prev_decimal > 0.30:
                    # Trigger alert
                    await send_odds_movement_alert(
                        race_id=update.race_id,
                        post=horse_odds.post,
                        old_odds=prev_odds.decode(),
                        new_odds=horse_odds.odds
                    )
            
            # Store current as previous for next check
            redis_client.set(prev_key, horse_odds.odds, ex=3600)
```

## Feature 3.3: Django API for Odds

```python
# apps/races/views.py

class RaceOddsView(APIView):
    """
    Get current odds for a race.
    
    Free tier: Delayed 5 minutes
    Premium tier: Real-time
    """
    
    def get(self, request, race_id):
        # Check user tier
        is_premium = request.user.is_authenticated and request.user.tier == 'premium'
        
        # Get odds from Redis
        race_key = f"race:{race_id}:odds"
        odds_json = redis_client.get(race_key)
        
        if not odds_json:
            return Response({"error": "Odds not available"}, status=404)
        
        odds_data = json.loads(odds_json)
        
        # Apply delay for free users
        if not is_premium:
            odds_timestamp = datetime.fromisoformat(odds_data['timestamp'])
            if timezone.now() - odds_timestamp < timedelta(minutes=5):
                # Odds too fresh, return cached older odds or error
                return Response({
                    "message": "Real-time odds available for premium users only",
                    "upgrade_url": "/subscription/upgrade"
                }, status=403)
        
        return Response(odds_data)
```

## Feature 3.4: Odds History

```python
# apps/races/models.py

class OddsSnapshot(models.Model):
    """Historical odds at a specific time."""
    race = models.ForeignKey(Race, related_name='odds_snapshots')
    post_position = models.IntegerField()
    odds = models.CharField(max_length=10)  # "5:1"
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['race', 'timestamp']),
            models.Index(fields=['race', 'post_position', 'timestamp']),
        ]

# Endpoint
GET /api/races/{race-id}/odds/history?post=5
```

**Response:**
```json
{
  "race_id": 123,
  "post_position": 5,
  "horse_name": "Thunder Bolt",
  "odds_timeline": [
    {"time": "11:00:00", "odds": "8:1"},
    {"time": "11:30:00", "odds": "7:1"},
    {"time": "12:00:00", "odds": "6:1"},
    {"time": "12:30:00", "odds": "5:1"},
    {"time": "12:50:00", "odds": "4:1"}
  ],
  "morning_line": "8:1",
  "current": "4:1",
  "change_percentage": -50
}
```

## Feature 3.5: WebSocket Streaming (Premium)

```python
# fastapi_services/streaming/main.py

from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI()

@app.websocket("/ws/odds/{race_id}")
async def odds_stream(websocket: WebSocket, race_id: int):
    """
    Stream live odds updates to premium users.
    
    Client connects, receives updates every time odds change.
    """
    await websocket.accept()
    
    # Subscribe to Redis pub/sub for this race
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"race:{race_id}:odds:updates")
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                odds_update = json.loads(message['data'])
                await websocket.send_json(odds_update)
    
    except WebSocketDisconnect:
        pubsub.unsubscribe()
```

**Client usage:**
```javascript
// Premium user's browser
const ws = new WebSocket('ws://api.example.com/ws/odds/123');

ws.onmessage = (event) => {
  const odds = JSON.parse(event.data);
  console.log('Odds updated:', odds);
  // Update UI with new odds
};
```

## Feature 3.6: Rate Limiting

```python
# apps/shared/middleware.py

from django.core.cache import cache

class RateLimitMiddleware:
    """
    Enforce API rate limits based on user tier.
    
    Free: 100 requests/hour
    Premium: 1000 requests/hour
    """
    
    LIMITS = {
        'free': 100,
        'premium': 1000,
    }
    
    def __call__(self, request):
        if request.path.startswith('/api/'):
            user_tier = 'premium' if request.user.is_authenticated and request.user.tier == 'premium' else 'free'
            limit = self.LIMITS[user_tier]
            
            # Check Redis counter
            key = f"ratelimit:{request.user.id if request.user.is_authenticated else request.META['REMOTE_ADDR']}"
            current = cache.get(key, 0)
            
            if current >= limit:
                return JsonResponse({
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "reset_in_seconds": cache.ttl(key)
                }, status=429)
            
            # Increment counter
            cache.set(key, current + 1, timeout=3600)  # 1 hour window
        
        return self.get_response(request)
```

## ADRs Tested

✅ **ADR-017: Performance** - Gzip, Redis caching
✅ **ADR-020: Django vs FastAPI** - FastAPI for high-throughput ingestion
✅ **ADR-022: Headers** - X-Flow-ID across Django + FastAPI
✅ **Rate limiting** - 429 Too Many Requests by tier
✅ **WebSocket streaming** - Real-time for premium users

## Deliverables

✅ Odds scraper running every 30 seconds
✅ FastAPI ingestion service (1000s updates/min)
✅ Redis caching for fast API responses
✅ Odds history tracking
✅ WebSocket streaming for premium users
✅ Rate limiting by user tier
✅ Odds movement alerts (>30% change)

---

# Milestone 4: Exotic Bets & Pari-Mutuel
**Duration:** Week 10-12
**Complexity:** High
**Goal:** Support exacta/trifecta/quinté bets, pari-mutuel pool calculations

## What You'll Learn
- Complex betting types
- Pari-mutuel pool mathematics
- Combinatorics (calculating bet coverage)
- Batch operations (207 Multi-Status)

## Feature 4.1: Exotic Bet Types

**Extended Bet model:**
```python
# apps/bets/models.py

class Bet(models.Model):
    BET_TYPES = [
        ('win', 'Win'),
        ('place', 'Place'),
        ('show', 'Show'),
        ('exacta', 'Exacta'),
        ('exacta_box', 'Exacta Box'),
        ('trifecta', 'Trifecta'),
        ('trifecta_box', 'Trifecta Box'),
        ('superfecta', 'Superfecta'),
        ('quinte', 'Quinté'),
        ('quinte_disorder', 'Quinté Désordre'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    bet_type = models.CharField(max_length=20, choices=BET_TYPES)
    
    # For simple bets: single horse
    horse = models.ForeignKey(Horse, null=True, blank=True)
    
    # For exotic bets: multiple horses in order
    selections = models.JSONField(default=list)  # [5, 3, 7] for exacta/trifecta
    
    # Box bets cover multiple combinations
    is_box = models.BooleanField(default=False)
    combinations_count = models.IntegerField(default=1)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)  # amount × combinations
    
    # For fixed odds (win/place/show)
    odds_at_bet = models.CharField(max_length=10, null=True, blank=True)
    
    # For pari-mutuel (exotic bets)
    estimated_payout = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_payout = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=10, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
```

**Bet placement logic:**
```python
# apps/bets/services.py

from itertools import permutations, combinations

def calculate_bet_cost(bet_type: str, selections: list[int], amount: Decimal, is_box: bool) -> dict:
    """
    Calculate total cost and combinations for exotic bets.
    
    Examples:
        Exacta 5-3: 1 combination, cost = amount
        Exacta box 5,3: 2 combinations (5-3, 3-5), cost = amount × 2
        Trifecta 5-3-7: 1 combination, cost = amount
        Trifecta box 5,3,7: 6 combinations (3! = 6), cost = amount × 6
    """
    if bet_type in ['win', 'place', 'show']:
        return {'combinations': 1, 'total_cost': amount}
    
    if bet_type == 'exacta':
        if is_box:
            # All permutations of 2 from selections
            combos = len(list(permutations(selections, 2)))
        else:
            combos = 1  # Exact order specified
    
    elif bet_type == 'trifecta':
        if is_box:
            # All permutations of 3 from selections
            combos = len(list(permutations(selections, 3)))
        else:
            combos = 1
    
    elif bet_type == 'superfecta':
        if is_box:
            combos = len(list(permutations(selections, 4)))
        else:
            combos = 1
    
    elif bet_type == 'quinte':
        if is_box:  # Disorder
            combos = len(list(combinations(selections, 5)))  # Any order
        else:
            combos = 1  # Exact order
    
    total_cost = amount * combos
    
    return {
        'combinations_count': combos,
        'total_cost': total_cost
    }


def place_bet(user_id: int, race_id: int, bet_data: dict) -> Bet:
    """
    Create a bet record with proper cost calculation.
    """
    bet_type = bet_data['bet_type']
    selections = bet_data.get('selections', [])
    amount = Decimal(bet_data['amount'])
    is_box = bet_data.get('is_box', False)
    
    # Calculate cost
    cost_info = calculate_bet_cost(bet_type, selections, amount, is_box)
    
    # Get estimated payout for exotic bets
    estimated_payout = None
    if bet_type in ['exacta', 'trifecta', 'superfecta', 'quinte']:
        estimated_payout = estimate_parimutuel_payout(race_id, bet_type, selections)
    
    # Create bet
    bet = Bet.objects.create(
        user_id=user_id,
        race_id=race_id,
        bet_type=bet_type,
        selections=selections,
        is_box=is_box,
        combinations_count=cost_info['combinations_count'],
        amount=amount,
        total_cost=cost_info['total_cost'],
        estimated_payout=estimated_payout,
        status='pending'
    )
    
    return bet
```

## Feature 4.2: Pari-Mutuel Pool Estimation

```python
# apps/races/services.py

def estimate_parimutuel_payout(race_id: int, bet_type: str, selections: list[int]) -> Decimal:
    """
    Estimate payout for exotic bet based on current betting pool.
    
    Note: This is an ESTIMATE. Actual payout determined after betting closes.
    
    Pari-mutuel formula:
        Payout = (Your share of pool) × (Total pool - track take)
    """
    # Get current pool data from betting site or scraping
    pool_data = get_current_pool(race_id, bet_type)
    
    total_pool = Decimal(pool_data['total_pool'])
    track_take_percentage = Decimal('0.20')  # 20% commission
    
    # Amount going to winning bets
    pool_to_winners = total_pool * (1 - track_take_percentage)
    
    # How much bet on this specific combination
    combination_key = '-'.join(map(str, selections))
    amount_on_combination = Decimal(pool_data['by_combination'].get(combination_key, '0'))
    
    if amount_on_combination == 0:
        # No one else bet this combination - could be huge payout!
        # Use average as estimate
        return pool_to_winners / 100  # Very rough estimate
    
    # Calculate payout per $1 bet
    payout_per_dollar = pool_to_winners / amount_on_combination
    
    return payout_per_dollar
```

**Example calculation:**
```
Race 5 Exacta Pool:
- Total money bet: $10,000
- Track takes 20%: -$2,000
- Pool to winners: $8,000

User bets $10 on exacta 5-3
Total bet on 5-3: $200

If 5-3 wins:
- User's share: $10 / $200 = 5%
- User's payout: 5% × $8,000 = $400
- Effective odds: 40:1
```

## Feature 4.3: Batch Bet Placement

```python
# apps/bets/views.py

class BatchBetView(APIView):
    """
    Place multiple bets in one request.
    Returns 207 Multi-Status with per-bet results.
    """
    
    def post(self, request):
        """
        POST /api/bets/batch
        {
          "bets": [
            {"race_id": 123, "bet_type": "exacta", "selections": [5, 3], "amount": "10.00"},
            {"race_id": 124, "bet_type": "win", "horse_id": 7, "amount": "20.00"},
            {"race_id": 125, "bet_type": "trifecta_box", "selections": [2, 5, 8], "amount": "5.00"}
          ]
        }
        """
        results = []
        
        for bet_data in request.data['bets']:
            try:
                bet = place_bet(request.user.id, bet_data['race_id'], bet_data)
                results.append({
                    'bet_id': bet.id,
                    'race_id': bet_data['race_id'],
                    'status': 'success',
                    'total_cost': str(bet.total_cost),
                    'estimated_payout': str(bet.estimated_payout) if bet.estimated_payout else None
                })
            
            except Exception as e:
                results.append({
                    'race_id': bet_data['race_id'],
                    'status': 'failed',
                    'reason': str(e)
                })
        
        return Response(results, status=207)  # Multi-Status
```

**Response:**
```json
[
  {
    "bet_id": 1001,
    "race_id": 123,
    "status": "success",
    "total_cost": "10.00",
    "estimated_payout": "250.00"
  },
  {
    "bet_id": 1002,
    "race_id": 124,
    "status": "success",
    "total_cost": "20.00"
  },
  {
    "race_id": 125,
    "status": "failed",
    "reason": "Invalid selections: horse 8 not in race"
  }
]
```

## Feature 4.4: Bet Settlement (After Race)

```python
# apps/bets/services.py

def settle_bet(bet: Bet, race_results: dict) -> None:
    """
    Calculate if bet won/lost and actual payout.
    
    race_results: {"finish_order": [5, 3, 7, 2, 9], "payouts": {...}}
    """
    finish_order = race_results['finish_order']
    
    if bet.bet_type == 'win':
        if bet.horse.post_position == finish_order[0]:
            bet.status = 'won'
            bet.actual_payout = Decimal(race_results['payouts']['win'][bet.horse.post_position])
        else:
            bet.status = 'lost'
            bet.actual_payout = Decimal('0')
    
    elif bet.bet_type == 'exacta':
        correct_order = finish_order[:2]
        if bet.is_box:
            # Box wins if both horses in top 2 (any order)
            if set(bet.selections) == set(correct_order):
                bet.status = 'won'
                bet.actual_payout = Decimal(race_results['payouts']['exacta'])
            else:
                bet.status = 'lost'
        else:
            # Straight exacta needs exact order
            if bet.selections == correct_order:
                bet.status = 'won'
                bet.actual_payout = Decimal(race_results['payouts']['exacta'])
            else:
                bet.status = 'lost'
    
    elif bet.bet_type == 'trifecta':
        correct_order = finish_order[:3]
        if bet.is_box:
            if set(bet.selections) == set(correct_order):
                bet.status = 'won'
                bet.actual_payout = Decimal(race_results['payouts']['trifecta'])
            else:
                bet.status = 'lost'
        else:
            if bet.selections == correct_order:
                bet.status = 'won'
                bet.actual_payout = Decimal(race_results['payouts']['trifecta'])
            else:
                bet.status = 'lost'
    
    elif bet.bet_type == 'quinte':
        correct_order = finish_order[:5]
        if bet.is_box:  # Disorder
            if set(bet.selections) == set(correct_order):
                bet.status = 'won'
                bet.actual_payout = Decimal(race_results['payouts']['quinte_disorder'])
            else:
                # Partial payouts for 4/5 or 3/5 correct
                correct_count = len(set(bet.selections) & set(correct_order))
                if correct_count >= 3:
                    bet.status = 'partial_win'
                    bet.actual_payout = Decimal(race_results['payouts'][f'quinte_{correct_count}_of_5'])
                else:
                    bet.status = 'lost'
        else:  # Exact order
            if bet.selections == correct_order:
                bet.status = 'won'
                bet.actual_payout = Decimal(race_results['payouts']['quinte'])
            else:
                bet.status = 'lost'
    
    bet.save()
```

## ADRs Tested

✅ **ADR-012: Status Codes** - 207 Multi-Status for batch bets
✅ **ADR-014: JSON Standards** - Decimal for money, not float
✅ **Idempotency** - Bet placement with Idempotency-Key
✅ **Complex business logic** - Combinatorics, pari-mutuel math

## Deliverables

✅ Exotic bet types (exacta, trifecta, quinté)
✅ Box bet support (multiple combinations)
✅ Pari-mutuel pool estimation
✅ Batch bet placement (207 Multi-Status)
✅ Bet settlement logic (all bet types)
✅ Portfolio analytics (ROI by bet type)

---

# Milestone 5: Strategies & Backtesting
**Duration:** Week 13-15
**Complexity:** High
**Goal:** Build betting strategies, test against historical data

## What You'll Learn
- Strategy pattern (rule-based logic)
- Backtesting methodology
- Async job processing (Celery)
- Complex filtering logic

## Feature 5.1: Strategy Builder

```python
# apps/strategies/models.py

class Strategy(models.Model):
    """User-defined betting strategy."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    
    # Strategy rules (JSON)
    rules = models.JSONField(default=dict)
    # Example rules:
    # {
    #   "track_condition": {"in": ["muddy", "sloppy"]},
    #   "horse_muddy_win_rate": {"gte": 0.30},
    #   "current_odds": {"gte": "4:1"},
    #   "trainer_recent_wins": {"gte": 5}
    # }
    
    # Action when conditions met
    action_type = models.CharField(max_length=20)  # "alert", "auto_bet", "track"
    bet_type = models.CharField(max_length=20, default='win')
    stake_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    stake_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # % of bankroll
    
    created_at = models.DateTimeField(auto_now_add=True)


class StrategyTrigger(models.Model):
    """Record when strategy conditions met."""
    strategy = models.ForeignKey(Strategy, related_name='triggers')
    race = models.ForeignKey(Race)
    race_entry = models.ForeignKey(RaceEntry)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    triggered_at = models.DateTimeField(auto_now_add=True)
    
    # Did user act on this trigger?
    bet_placed = models.ForeignKey(Bet, null=True, blank=True)
```

**Strategy evaluation:**
```python
# apps/strategies/services.py

def evaluate_strategy(strategy: Strategy, race: Race) -> list[dict]:
    """
    Check if any horses in race match strategy criteria.
    
    Returns list of matching entries with confidence scores.
    """
    matching_entries = []
    
    for entry in race.entries.all():
        # Evaluate each rule
        matches_all = True
        
        for field, condition in strategy.rules.items():
            value = get_field_value(entry, field)
            
            if not check_condition(value, condition):
                matches_all = False
                break
        
        if matches_all:
            # Calculate confidence score
            confidence = calculate_confidence(entry, strategy.rules)
            
            matching_entries.append({
                'entry': entry,
                'confidence': confidence
            })
    
    return matching_entries


def get_field_value(entry: RaceEntry, field: str):
    """Get value for strategy rule evaluation."""
    if field == 'track_condition':
        return entry.race.track_condition
    
    elif field == 'horse_muddy_win_rate':
        # Calculate from historical data
        muddy_races = RaceEntry.objects.filter(
            horse=entry.horse,
            race__track_condition__in=['muddy', 'sloppy']
        )
        wins = muddy_races.filter(finish_position=1).count()
        total = muddy_races.count()
        return wins / total if total > 0 else 0
    
    elif field == 'current_odds':
        # Get from Redis
        odds_key = f"race:{entry.race_id}:post:{entry.post_position}:odds"
        return redis_client.get(odds_key)
    
    # ... more field calculations


def check_condition(value, condition: dict) -> bool:
    """
    Check if value meets condition.
    
    condition examples:
        {"eq": "muddy"}
        {"in": ["muddy", "sloppy"]}
        {"gte": 0.30}
        {"between": [0.20, 0.40]}
    """
    if 'eq' in condition:
        return value == condition['eq']
    elif 'in' in condition:
        return value in condition['in']
    elif 'gte' in condition:
        return value >= condition['gte']
    elif 'lte' in condition:
        return value <= condition['lte']
    elif 'between' in condition:
        return condition['between'][0] <= value <= condition['between'][1]
    
    return False
```

## Feature 5.2: Strategy Monitoring (Celery)

```python
# apps/strategies/tasks.py

@shared_task
def monitor_strategies():
    """
    Check all active strategies against upcoming races.
    Runs every 5 minutes.
    """
    strategies = Strategy.objects.filter(active=True)
    
    # Races happening in next 2 hours
    upcoming_races = Race.objects.filter(
        date=date.today(),
        post_time__gt=timezone.now(),
        post_time__lt=timezone.now() + timedelta(hours=2)
    )
    
    for strategy in strategies:
        for race in upcoming_races:
            matches = evaluate_strategy(strategy, race)
            
            for match in matches:
                # Record trigger
                trigger = StrategyTrigger.objects.create(
                    strategy=strategy,
                    race=race,
                    race_entry=match['entry'],
                    confidence_score=match['confidence']
                )
                
                # Send alert
                if strategy.action_type == 'alert':
                    send_strategy_alert(strategy.user, trigger)
                
                # Auto-bet if configured
                elif strategy.action_type == 'auto_bet':
                    place_strategy_bet(strategy, trigger)
```

## Feature 5.3: Backtesting

```python
# apps/strategies/models.py

class Backtest(models.Model):
    """Backtest job."""
    strategy = models.ForeignKey(Strategy)
    start_date = models.DateField()
    end_date = models.DateField()
    
    status = models.CharField(max_length=20, default='processing')  # processing, completed, failed
    progress_percentage = models.IntegerField(default=0)
    
    # Results (null until completed)
    total_races_evaluated = models.IntegerField(null=True)
    total_matches = models.IntegerField(null=True)
    total_bets = models.IntegerField(null=True)
    total_wagered = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    total_returned = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    roi_percentage = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)


# apps/strategies/tasks.py

@shared_task
def run_backtest(backtest_id: int):
    """
    Run backtest in background (compute-heavy operation).
    
    For each historical race in date range:
      1. Evaluate strategy
      2. Simulate bet placement
      3. Calculate outcome based on actual results
      4. Accumulate P&L
    """
    backtest = Backtest.objects.get(id=backtest_id)
    strategy = backtest.strategy
    
    backtest.status = 'processing'
    backtest.save()
    
    # Get all races in date range
    races = Race.objects.filter(
        date__gte=backtest.start_date,
        date__lte=backtest.end_date,
        entries__finish_position__isnull=False  # Only completed races
    ).distinct()
    
    total_races = races.count()
    total_wagered = Decimal('0')
    total_returned = Decimal('0')
    wins = 0
    total_bets = 0
    
    for i, race in enumerate(races):
        # Update progress
        if i % 100 == 0:
            backtest.progress_percentage = int((i / total_races) * 100)
            backtest.save()
        
        # Evaluate strategy for this race
        matches = evaluate_strategy(strategy, race)
        
        for match in matches:
            entry = match['entry']
            
            # Simulate bet
            bet_amount = calculate_stake(strategy, Decimal('1000'))  # Assume $1000 bankroll
            total_bets += 1
            total_wagered += bet_amount
            
            # Check if bet won
            if entry.finish_position == 1:  # Assuming win bet
                payout = bet_amount * odds_to_decimal(entry.morning_line_odds)
                total_returned += payout
                wins += 1
            # else: bet lost, no return
    
    # Calculate final stats
    profit_loss = total_returned - total_wagered
    roi = (profit_loss / total_wagered * 100) if total_wagered > 0 else 0
    win_rate = (wins / total_bets) if total_bets > 0 else 0
    
    # Save results
    backtest.status = 'completed'
    backtest.total_races_evaluated = total_races
    backtest.total_matches = total_bets
    backtest.total_bets = total_bets
    backtest.total_wagered = total_wagered
    backtest.total_returned = total_returned
    backtest.profit_loss = profit_loss
    backtest.roi_percentage = roi
    backtest.win_rate = win_rate
    backtest.completed_at = timezone.now()
    backtest.save()
```

**API endpoints:**
```python
# Start backtest (returns 202 Accepted immediately)
POST /api/strategies/{id}/backtest
{
  "start_date": "2020-01-01",
  "end_date": "2023-12-31"
}

Response: 202 Accepted
{
  "job_id": 123,
  "status": "processing",
  "poll_url": "/api/backtests/jobs/123"
}

# Poll for status
GET /api/backtests/jobs/123

Response (processing):
{
  "job_id": 123,
  "status": "processing",
  "progress_percentage": 45
}

Response (completed):
{
  "job_id": 123,
  "status": "completed",
  "results": {
    "total_bets": 1247,
    "win_rate": 0.28,
    "total_wagered": "12470.00",
    "total_returned": "15890.00",
    "profit_loss": "3420.00",
    "roi_percentage": 27.4
  },
  "result_url": "/api/backtests/results/123"
}
```

## Feature 5.4: Strategy Comparison

```python
# Compare multiple strategies
GET /api/strategies/compare?strategy_ids=1,2,3&date_range=2020-01-01/2023-12-31
```

**Response:**
```json
{
  "strategies": [
    {
      "id": 1,
      "name": "Mudder Specialist",
      "roi": 27.4,
      "win_rate": 0.28,
      "total_bets": 1247
    },
    {
      "id": 2,
      "name": "Hot Trainer",
      "roi": 15.2,
      "win_rate": 0.22,
      "total_bets": 892
    },
    {
      "id": 3,
      "name": "Track Bias Play",
      "roi": 8.1,
      "win_rate": 0.25,
      "total_bets": 1544
    }
  ],
  "best_by_roi": 1,
  "best_by_win_rate": 1,
  "recommendation": "Strategy 1 (Mudder Specialist) performs best overall"
}
```

## ADRs Tested

✅ **ADR-011: Async Processing** - 202 Accepted for backtesting
✅ **Complex business logic** - Strategy evaluation engine
✅ **Services/Selectors** - Strategy logic separate from views
✅ **Background jobs** - Celery for monitoring and backtesting

## Deliverables

✅ Strategy builder (rule-based conditions)
✅ Strategy monitoring (Celery task every 5 min)
✅ Backtesting engine (async, 202 Accepted pattern)
✅ Strategy comparison endpoint
✅ Alert system (email/push when strategy triggers)

---

# Milestone 6: Premium Features & Polish
**Duration:** Week 16-18
**Complexity:** Medium
**Goal:** Subscription tiers, advanced features, full ADR compliance

## Feature 6.1: Subscription Management

```python
# apps/users/models.py

class User(AbstractUser):
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('professional', 'Professional'),
    ]
    
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free')
    subscription_expires_at = models.DateTimeField(null=True, blank=True)


# Subscription upgrade (idempotent)
POST /api/subscription/upgrade
Idempotency-Key: upgrade-2024-12-06-abc123
{
  "tier": "premium",
  "payment_method": "stripe_pm_abc123"
}

Response: 201 Created (or 200 OK if idempotency key seen before)
{
  "user_id": 123,
  "tier": "premium",
  "expires_at": "2025-12-06T00:00:00Z",
  "amount_charged": "29.00"
}
```

## Feature 6.2: ETag for Strategy Updates

```python
# apps/strategies/views.py

class StrategyDetailView(APIView):
    def get(self, request, strategy_id):
        strategy = Strategy.objects.get(id=strategy_id)
        serializer = StrategySerializer(strategy)
        
        # Generate ETag from strategy version
        etag = f'"{strategy.id}-v{strategy.updated_at.timestamp()}"'
        
        response = Response(serializer.data)
        response['ETag'] = etag
        return response
    
    def put(self, request, strategy_id):
        strategy = Strategy.objects.get(id=strategy_id)
        
        # Check If-Match header
        if_match = request.headers.get('If-Match')
        current_etag = f'"{strategy.id}-v{strategy.updated_at.timestamp()}"'
        
        if if_match and if_match != current_etag:
            return Response(
                {"error": "Strategy was modified by another request"},
                status=412  # Precondition Failed
            )
        
        # Update strategy
        serializer = StrategySerializer(strategy, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return new ETag
        new_etag = f'"{strategy.id}-v{strategy.updated_at.timestamp()}"'
        response = Response(serializer.data)
        response['ETag'] = new_etag
        return response
```

## Feature 6.3: Deprecation Example

```python
# Deprecate old odds endpoint
@deprecated(
    sunset_date="2025-06-30",
    reason="Switching to FastAPI WebSocket for better performance",
    replacement="WebSocket /ws/odds/{race-id}"
)
@action(detail=True, methods=['get'])
def legacy_odds_polling(self, request, race_id):
    """
    Legacy polling endpoint for odds (DEPRECATED).
    
    This endpoint will be removed on 2025-06-30.
    Use WebSocket streaming instead for real-time updates.
    """
    # ... implementation

# Response headers:
# Deprecation: @1748736000
# Sunset: Mon, 30 Jun 2025 00:00:00 GMT
```

## Feature 6.4: Complete Semgrep Rules

```yaml
# .semgrep/horse-betting-rules.yml

rules:
  - id: no-float-for-money
    message: |
      Use Decimal for money amounts, not float.
      Floats lose precision (52.50 becomes 52.499999).
      See: docs/adr/014-json-payload-standards.md
    pattern: |
      models.FloatField()
    severity: ERROR
    languages: [python]
    paths:
      include:
        - "apps/bets/models.py"
        - "apps/races/models.py"
  
  - id: missing-idempotency-key
    message: |
      Payment/subscription endpoints must support Idempotency-Key.
      See: docs/adr/010-http-header-standards.md
    pattern: |
      def post(self, request):
          ...
    pattern-not: |
      def post(self, request):
          ...
          idempotency_key = request.headers.get('Idempotency-Key')
          ...
    severity: WARNING
    languages: [python]
    paths:
      include:
        - "apps/subscription/views.py"
        - "apps/bets/views.py"
```

## All ADRs Tested

✅ **Python ADRs (001-006):**
- Import patterns
- Docstrings
- No mutable defaults
- Frozen dataclasses
- Operator module

✅ **API ADRs (007-019):**
- Standard formats (dates, decimals)
- Deprecation headers
- API First (OpenAPI generated)
- HTTP headers (X-Flow-ID, Idempotency-Key)
- HTTP methods (GET/POST/PUT/PATCH/DELETE)
- Status codes (200/201/202/207/404/412/429)
- Hypermedia (pagination links)
- JSON standards (snake_case, Money as decimal)
- API meta info (x-api-id, x-audience)
- Pagination (cursor-based)
- Performance (gzip, field filtering, Redis caching)
- Security (JWT, role-based permissions)
- URL design (kebab-case, verb-free)

✅ **Django ADRs (020-025):**
- Django vs FastAPI split
- OpenAPI generation (drf-spectacular)
- HTTP header middleware
- Deprecation decorator
- Performance optimization (select_related, Redis)
- Cursor pagination

## Deliverables

✅ Subscription management (free/premium/professional tiers)
✅ ETag optimistic locking
✅ Deprecation headers
✅ Complete Semgrep rule set
✅ Pre-commit hooks
✅ CI/CD pipeline (schema validation, tests)
✅ Admin dashboard fully featured

---

# Complete Feature Matrix

| Feature | Milestone | Complexity | ADRs Tested |
|---------|-----------|------------|-------------|
| Load historical data | 0 | Low | Database, models |
| Horse/jockey/trainer stats | 1 | Medium | Pagination, JSON, URLs |
| Manual bet tracking | 1 | Medium | CRUD, Money decimals |
| Portfolio analytics | 1 | Medium | Selectors pattern |
| Race card scraping | 2 | Medium | Background jobs |
| Today's races API | 2 | Low | HTTP methods |
| Live odds scraping | 3 | High | FastAPI ingestion |
| Odds history tracking | 3 | Medium | TimescaleDB/indexing |
| WebSocket streaming | 3 | High | Real-time, premium |
| Rate limiting | 3 | Medium | 429 status, tiers |
| Exotic bets | 4 | High | Complex business logic |
| Pari-mutuel pools | 4 | High | Math, estimation |
| Batch bet placement | 4 | Medium | 207 Multi-Status |
| Strategy builder | 5 | High | Rule engine |
| Strategy monitoring | 5 | Medium | Celery, alerts |
| Backtesting | 5 | High | Async (202), compute |
| Subscription management | 6 | Medium | Idempotency, payments |
| ETag locking | 6 | Low | 412 Precondition Failed |
| Deprecation | 6 | Low | Headers, migration |
| Full Semgrep rules | 6 | Medium | All ADRs enforced |

---

# Success Criteria

## Functional
✅ Users can query 50,000 historical races
✅ Users can track bets and view ROI
✅ Users receive daily race cards automatically
✅ Premium users get real-time odds (<60 sec latency)
✅ Users can build and backtest strategies
✅ Exotic bets (quinté) work correctly
✅ Batch operations handle 100+ bets

## Technical
✅ Cursor pagination handles 50k races without timeout
✅ FastAPI ingests 1000+ odds updates/minute
✅ Redis caching <10ms latency for live odds
✅ Backtesting processes 10 years in <60 seconds
✅ WebSocket supports 100+ concurrent users
✅ Rate limiting enforces tier restrictions

## Quality
✅ All 25 ADRs mechanically enforced via Semgrep
✅ OpenAPI spec validates in CI
✅ Pre-commit hooks catch violations
✅ Test coverage >80%
✅ No float usage for money (all Decimal)
✅ No missing idempotency keys on payment endpoints

---

# Getting Started

1. **Week 1-2:** Load Kaggle dataset, build basic Django models
2. **Week 3-4:** Implement horse stats API, manual bet tracking
3. **Week 5-6:** Build race card scraper
4. **Week 7-9:** Add FastAPI for live odds, WebSockets
5. **Week 10-12:** Exotic bets, pari-mutuel calculations
6. **Week 13-15:** Strategy builder, backtesting
7. **Week 16-18:** Polish, subscriptions, full ADR compliance

**Total timeline: ~4 months to full platform**

---

# Appendix: Data Sources

**Historical data (Milestone 0-1):**
- Kaggle: "Horse Racing Dataset" (free, 50k races)
- Alternative: Equibase bulk downloads (paid)

**Live race cards (Milestone 2):**
- Equibase.com (free race cards)
- Track websites (free)

**Live odds (Milestone 3):**
- TVG.com (betting site, scrapable)
- TwinSpires.com (betting site, scrapable)
- Xpressbet.com (betting site, scrapable)

**Note:** Scraping betting sites is legally gray area. For production, consider:
- Official data feeds (expensive, $1000+/month)
- Partnership with betting sites
- User-contributed odds (crowdsourced)
