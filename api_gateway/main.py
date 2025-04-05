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

@app.get("/")
def read_root():
    return {"message": "Welcome to the Finance NLP Chatbot API"}

@app.get("/chat")
async def chat(query: str):
    query_lower = query.lower().replace("today", "").strip()
    if "price" in query_lower or "worth" in query_lower:
        # Price query logic
        words = query_lower.split()
        ticker = words[-1].upper() if words[-1].isalpha() else "BTC"
        try:
            response = requests.get(f"{DATA_SERVICE_URL}/price?ticker={ticker}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to fetch price: {str(e)}"}
    elif "show me news" in query_lower or "latest news" in query_lower:
        # Latest news logic
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
        # Informational query routed to RAG service
        try:
            response = requests.post(f"{RAG_SERVICE_URL}/ask-news", json={"text": query})
            response.raise_for_status()
            data = response.json()
            snippets = data["snippets"]
            if snippets:
                snippet_text = "Here are some relevant news snippets:\n" + "\n".join(
                    f"- {snippet['title']}: {snippet['summary']}" for snippet in snippets
                )
                return {"message": snippet_text}
            else:
                return {"message": "No relevant news found for your query."}
        except requests.RequestException as e:
            return {"error": f"Failed to fetch news snippets: {str(e)}"}