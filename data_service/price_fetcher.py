import os
from fastapi import FastAPI, HTTPException
import requests
import redis
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = FastAPI()

# Redis setup
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["finance_chatbot"]
news_collection = db["news"]

# API keys from .env (or defaults you provided)
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY", "c4cdc6bd-f996-4e58-84aa-633bcac41afc")
FMP_API_KEY = os.getenv("FMP_API_KEY", "QiITZBVs67TOyukaOip4QAnPHJi8wfqT")

# Cache expiration time (5 minutes = 300 seconds)
CACHE_EXPIRY = 300

# Helper function to determine if ticker is crypto or stock
def is_crypto(ticker: str) -> bool:
    crypto_symbols = {"BTC", "ETH", "XRP", "LTC", "DOGE"}
    return ticker.upper() in crypto_symbols

# Fetch price from CoinMarketCap (crypto)
def fetch_crypto_price(ticker: str) -> float:
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}
    params = {"symbol": ticker, "convert": "USD"}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching crypto price")
    
    data = response.json()
    price = data["data"][ticker.upper()]["quote"]["USD"]["price"]
    return price

# Fetch price from FMP (stocks)
def fetch_stock_price(ticker: str) -> float:
    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_API_KEY}"
    
    response = requests.get(url)
    if response.status_code != 200 or not response.json():
        raise HTTPException(status_code=response.status_code, detail="Error fetching stock price")
    
    data = response.json()
    price = data[0]["price"]
    return price

@app.get("/price")
async def get_price(ticker: str):
    # Check cache first
    cache_key = f"price:{ticker.upper()}"
    cached_price = redis_client.get(cache_key)
    if cached_price:
        return {
            "ticker": ticker.upper(),
            "price": float(cached_price),
            "timestamp": redis_client.get(f"{cache_key}:time"),
            "source": "cache"
        }

    # Fetch price based on ticker type
    try:
        if is_crypto(ticker):
            price = fetch_crypto_price(ticker)
            source = "CoinMarketCap"
        else:
            price = fetch_stock_price(ticker)
            source = "FMP"
        
        # Store in cache
        timestamp = datetime.utcnow().isoformat()
        redis_client.setex(cache_key, CACHE_EXPIRY, price)
        redis_client.setex(f"{cache_key}:time", CACHE_EXPIRY, timestamp)
        
        return {
            "ticker": ticker.upper(),
            "price": price,
            "timestamp": timestamp,
            "source": source
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/news")
async def get_news(limit: int = 5):
    try:
        # Fetch the latest 'limit' news items, sorted by fetched_at descending
        news_items = list(news_collection.find().sort("fetched_at", -1).limit(limit))
        # Convert MongoDB ObjectId to string for JSON serialization
        for item in news_items:
            item["_id"] = str(item["_id"])
        return {"news": news_items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)