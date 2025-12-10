"""Celery tasks for Turfoo data ingestion."""

import feedparser
from loguru import logger

from turfoo.celery_app import app


@app.task(name="turfoo.tasks.fetch_program_feed")
def fetch_program_feed():
    """Fetch and parse the program feed from Turfoo."""
    from turfoo.settings import settings

    logger.info(f"Fetching program feed from {settings.turfoo_program_feed_url}")
    feed = feedparser.parse(settings.turfoo_program_feed_url)
    logger.info(f"Fetched {len(feed.entries)} program entries")
    return {"entries": len(feed.entries), "title": feed.feed.get("title", "Unknown")}


@app.task(name="turfoo.tasks.fetch_news_feed")
def fetch_news_feed():
    """Fetch and parse the news feed from Turfoo."""
    from turfoo.settings import settings

    logger.info(f"Fetching news feed from {settings.turfoo_news_feed_url}")
    feed = feedparser.parse(settings.turfoo_news_feed_url)
    logger.info(f"Fetched {len(feed.entries)} news entries")
    return {"entries": len(feed.entries), "title": feed.feed.get("title", "Unknown")}


@app.task(name="turfoo.tasks.fetch_results_feed")
def fetch_results_feed():
    """Fetch and parse the results feed from Turfoo."""
    from turfoo.settings import settings

    logger.info(f"Fetching results feed from {settings.turfoo_results_feed_url}")
    feed = feedparser.parse(settings.turfoo_results_feed_url)
    logger.info(f"Fetched {len(feed.entries)} results entries")
    return {"entries": len(feed.entries), "title": feed.feed.get("title", "Unknown")}
