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
RAG_SERVICE_URL = "http://rag_service:8002"

# Define a set of known ticker symbols (both crypto and famous stocks)
KNOWN_TICKERS = {
    "BTC", "ETH", "XRP", "LTC", "DOGE",
    "AAPL", "TSLA", "GOOG", "AMZN", "MSFT"
}

@app.post("/ask")
async def ask(query: dict):
    try:
        # Route the query to the RAG service
        response = requests.post(f"{RAG_SERVICE_URL}/ask-news", json={"text": query["text"]})
        response.raise_for_status()
        data = response.json()
        answer = data.get("answer", "No answer generated.")
        snippets = data.get("snippets", [])
        return {"message": f"{answer}\n\nSources:\n" + "\n".join(snippets)}
    except requests.RequestException as e:
        return {"error": f"Failed to fetch news: {str(e)}"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the Finance NLP Chatbot API"}

@app.get("/chat")
async def chat(query: str):
    query_lower = query.lower().replace("today", "").strip()
    if "price" in query_lower or "worth" in query_lower:
        # Price query logic: look for a known ticker in the query.
        words = query_lower.split()
        ticker = None
        for word in words:
            candidate = word.upper()
            if candidate in KNOWN_TICKERS:
                ticker = candidate
                break
        # Fallback to default ticker if none found.
        if not ticker:
            ticker = "BTC"
        try:
            response = requests.get(f"{DATA_SERVICE_URL}/price?ticker={ticker}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to fetch price: {str(e)}"}
    elif "show me news" in query_lower or "latest news" in query_lower:
        # Latest news logic from the data service
        try:
            response = requests.get(f"{DATA_SERVICE_URL}/news?limit=5")
            response.raise_for_status()
            data = response.json()
            news_items = data["news"]
            if news_items:
                news_text = "Latest news:\n" + "\n".join(
                    f"- {item['title']}: {item['summary']}" for item in news_items
                )
                return {"message": news_text}
            else:
                return {"message": "No news available at the moment."}
        except requests.RequestException as e:
            return {"error": f"Failed to fetch news: {str(e)}"}
    else:
        try:
            response = requests.post(f"{RAG_SERVICE_URL}/ask-news", json={"text": query})
            response.raise_for_status()
            data = response.json()

            # Safely extract RAG output
            answer = data.get("answer", "No answer found.")
            snippets = data.get("snippets", [])

            if snippets:
                # Combine the answer and the snippets
                snippet_text = f"{answer}\n\nSources:\n" + "\n".join(snippets)
                return {"message": snippet_text}
            else:
                # If no snippets, at least return the raw answer from RAG
                return {"message": answer}

        except requests.RequestException as e:
            # Return as message instead of `error`, so front-end sees it
            return {"message": f"Failed to fetch news snippets: {str(e)}"}
