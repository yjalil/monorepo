from dataclasses import asdict
from urllib import error

import feedparser
import httpx
from pydantic import HttpUrl

from turfoo import exceptions, mixins, models


class TurfooRSSFeed(mixins.FetchableMixin):

    def fetch(self, feed_type: models.RSSFeedType) -> mixins.Iterator[models.RSSEntry]:
        try:
            feed: feedparser.FeedParserDict = feedparser.parse(str(feed_type.value))
        except error.URLError as e:
            raise exceptions.TurfooFeedError(...) from e

        if feed.bozo:
            raise exceptions.TurfooFeedError(
                f"Malformed feed: {feed.bozo_exception}",
            ) from feed.bozo_exception

        if not feed.entries:
            raise exceptions.TurfooFeedError("RSS feed contains no entries")

        yield from (models.RSSEntry(**entry) for entry in feed.entries)




class TurfooLinkScraper(mixins.FetchableMixin,mixins.ReadableMixin):
    def fetch(self, urls: list[HttpUrl]) -> mixins.Iterator[str]:
        for url in urls:
            try:
                response = httpx.get(str(url))
                response.raise_for_status()
                yield response.text
            except httpx.HTTPError as e:
                raise exceptions.TurfooLinkScrapeError(f"Failed to fetch {url}: {e}") from e



if __name__ == "__main__":
    turfool_provider = TurfooRSSFeed()
    rss_content = turfool_provider.fetch(models.RSSFeedType.NEWS)
    for entry in rss_content:
        print(asdict(entry))
        break

