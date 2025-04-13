import os
import time
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from transformers import pipeline

app = FastAPI()

# Set up logging for debugging and performance monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the sentence transformer model for query embedding
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to the Qdrant vector database (ensure Qdrant is running)
qdrant_client = QdrantClient(host='qdrant', port=6333)

# Initialize the text generation pipeline using a free model from Hugging Face.
# Ensure your Hugging Face API token is set in the environment if needed.
generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-small",
    use_auth_token=os.getenv("API_KEY")
)

class Query(BaseModel):
    text: str

@app.post("/ask-news")
async def ask_news(query: Query):
    try:
        # Step 1: Embed the user query and log time taken
        start_time = time.time()
        query_embedding = embedder.encode(query.text).tolist()
        logger.info(f"Embedding time: {time.time() - start_time:.2f}s")

        # Step 2: Search for relevant news in Qdrant and log time taken
        start_time = time.time()
        search_result = qdrant_client.search(
            collection_name="news",
            query_vector=query_embedding,
            limit=3
        )
        logger.info(f"Search time: {time.time() - start_time:.2f}s")

        # Step 3: Process search results
        if not search_result:
            snippet_texts = ["No relevant news found."]
            snippets = ["No relevant news found."]
        else:
            snippets = []
            snippet_texts = []
            for hit in search_result:
                title = hit.payload.get("title", "No Title")
                summary = hit.payload.get("summary", "")
                link = hit.payload.get("link", "No Link")
                source = hit.payload.get("source", "Unknown")
                # Format each snippet with title, summary, and source information
                snippet_info = f"Title: {title}\nSummary: {summary}\nSource: {source} ({link})"
                snippets.append(snippet_info)
                # Use a concise version for the prompt input
                snippet_texts.append(f"{title}: {summary}")

        # Step 4: Build a refined prompt that includes the user query and retrieved news snippets.
        prompt = (
            f"User Query: {query.text}\n\n"
            f"Retrieved News Articles:\n" + "\n".join(snippet_texts) +
            "\n\nUsing the above news articles, generate a concise and coherent summary in 2-3 sentences that answers the user query. "
            "Be sure to integrate information from multiple articles if available and include the source URLs next to each cited piece of information."
        )
        logger.info(f"Prompt: {prompt}")

        # Step 5: Generate an answer using the text generation pipeline with tuned parameters
        start_time = time.time()
        generated = generator(
            prompt,
            max_length=150,     # Increased max length for a more detailed answer
            min_length=30,      # Increased minimum length for more context
            do_sample=True,     # Enable sampling for dynamic output
            temperature=0.7,    # Control randomness
            num_return_sequences=1
        )
        logger.info(f"Generation time: {time.time() - start_time:.2f}s")
        answer = generated[0]['generated_text'].strip()

        if not answer:
            answer = "Sorry, I can’t help with that yet!"

        return {"answer": answer, "snippets": snippets}

    except Exception as e:
        logger.error(f"Error in ask-news: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
