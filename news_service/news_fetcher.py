import os
import sys
import requests
import feedparser
from bs4 import BeautifulSoup
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dotenv import load_dotenv

print("Script starting...", file=sys.stderr)
print("Running updated script with NY Times and CoinDesk feeds", file=sys.stderr)  # Added for verification
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
print(f"Using MONGO_URI: {MONGO_URI}", file=sys.stderr)

try:
    client = MongoClient(MONGO_URI)
    db = client["finance_chatbot"]
    news_collection = db["news"]
    print("MongoDB client initialized.", file=sys.stderr)
except Exception as e:
    print(f"Failed to initialize MongoDB client: {str(e)}", file=sys.stderr)
    sys.exit(1)

# RSS feeds for financial news
RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",  # NY Times Business
    "https://www.coindesk.com/arc/outboundfeeds/rss/",           # CoinDesk main feed
]

def fetch_feed(url):
    """Fetch the RSS feed using requests with a custom User-Agent."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FinanceChatbot/1.0)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return feedparser.parse(response.content)
    except Exception as e:
        print(f"Error fetching feed {url}: {e}", file=sys.stderr)
        return None

def preprocess_text(html_content):
    """Remove HTML tags and clean text."""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ").strip()
    return " ".join(text.split())

def fetch_and_store_news():
    print(f"Fetching news at {datetime.utcnow().isoformat()}...", file=sys.stderr)
    for feed_url in RSS_FEEDS:
        feed = fetch_feed(feed_url)
        if feed is None or not feed.entries:
            print(f"No entries found for {feed_url}", file=sys.stderr)
            continue
        for entry in feed.entries:
            title = entry.get("title", "No title")
            summary = entry.get("summary", entry.get("description", ""))
            link = entry.get("link", "")
            published = entry.get("published", datetime.utcnow().isoformat())
            clean_summary = preprocess_text(summary)
            news_item = {
                "title": title,
                "summary": clean_summary,
                "link": link,
                "published": published,
                "fetched_at": datetime.utcnow().isoformat(),
                "source": feed_url.split("/")[2]  # e.g., "rss.nytimes.com"
            }
            news_collection.update_one(
                {"link": link},
                {"$set": news_item},
                upsert=True
            )
        print(f"Stored {len(feed.entries)} items from {feed_url}", file=sys.stderr)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_news, "interval", hours=1)
    scheduler.start()
    print("News scheduler started.", file=sys.stderr)

if __name__ == "__main__":
    print("Starting news service...", file=sys.stderr)
    print("Testing MongoDB connection...", file=sys.stderr)
    try:
        news_collection.insert_one({"test": "Hello MongoDB", "timestamp": datetime.utcnow().isoformat()})
        print("Test document inserted successfully.", file=sys.stderr)
    except Exception as e:
        print(f"MongoDB test insert failed: {str(e)}", file=sys.stderr)
        sys.exit(1)

    fetch_and_store_news()
    start_scheduler()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Shutting down news service...", file=sys.stderr)