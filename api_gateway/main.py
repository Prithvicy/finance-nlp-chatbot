from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_SERVICE_URL = "http://data_service:8001"

@app.get("/")
def read_root():
    return {"message": "Welcome to the Finance NLP Chatbot API"}

@app.get("/chat")
async def chat(query: str):
    query_lower = query.lower().replace("today", "").strip()
    if "price" in query_lower or "worth" in query_lower:
        # Existing price logic
        words = query_lower.split()
        ticker = words[-1].upper() if words[-1].isalpha() else "BTC"
        try:
            response = requests.get(f"{DATA_SERVICE_URL}/price?ticker={ticker}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to fetch price: {str(e)}"}
    elif "show me news" in query_lower or "latest news" in query_lower:
        # New news logic
        try:
            response = requests.get(f"{DATA_SERVICE_URL}/news?limit=5")
            response.raise_for_status()
            data = response.json()
            news_items = data["news"]
            if news_items:
                # Format news into a multi-line string
                news_text = "Latest news:\n" + "\n".join(
                    f"- {item['title']}: {item['summary']}" for item in news_items
                )
                return {"message": news_text}
            else:
                return {"message": "No news available at the moment."}
        except requests.RequestException as e:
            return {"error": f"Failed to fetch news: {str(e)}"}
    else:
        return {"message": "I can show you the price of BTC or the latest news. Try 'What is the price of BTC?' or 'Show me news'."}