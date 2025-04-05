from fastapi import FastAPI, HTTPException
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from pydantic import BaseModel

app = FastAPI()

# Qdrant setup
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

class Query(BaseModel):
    text: str

@app.post("/ask-news")
async def ask_news(query: Query):
    try:
        # Embed the user query
        query_embedding = model.encode(query.text).tolist()

        # Search for the top 3 similar news snippets
        search_result = qdrant_client.search(
            collection_name="news",
            query_vector=query_embedding,
            limit=3
        )

        # Format the results
        snippets = [
            {
                "title": hit.payload["title"],
                "summary": hit.payload["summary"],
                "link": hit.payload["link"],
                "source": hit.payload["source"]
            }
            for hit in search_result
        ]

        return {"snippets": snippets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")